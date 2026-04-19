"""Reviewer provider adapters for peer_review.py.

Spatial Deck's peer-review pattern relies on TWO model families with decorrelated
errors. The original implementation hardcoded ollama@Sam (llama3.1:8b) +
ollama@Archie (qwen2.5-coder:14b), which only works on Alex's fleet.

This module abstracts the reviewer behind a Provider interface so anyone can run
peer review with whatever credentials they have:

  - ollama  (local, free, requires fleet machines)
  - claude  (ANTHROPIC_API_KEY)
  - gemini  (GEMINI_API_KEY or GOOGLE_API_KEY)
  - openai  (OPENAI_API_KEY)

Auto-pair selection rule (preserves the "two different families" invariant):
  1. If ollama Sam + Archie are both reachable → use them (preserves the proven
     Sam/Archie pair behaviour).
  2. Else, collect all providers with valid creds, pick top two from
     [claude, gemini, openai] in that priority order. They're already different
     families.
  3. If only one provider is available, error out — single-reviewer is noisy
     per the KB lessons.

No external SDKs. Pure stdlib (urllib.request) so the importer suite stays
zero-deps.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Callable

# ── shared JSON cleanup ──
_THINK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of model output that may be wrapped in fences,
    prefaced with prose, or padded with <think> blocks."""
    text = _THINK.sub("", text).strip()
    text = _FENCE.sub("", text).strip()
    # find first {...} balanced object
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object in: {text[:200]}")
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError(f"unbalanced JSON in: {text[:200]}")


def _http_post(url: str, payload: dict, headers: dict, timeout: int = 240) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _http_get(url: str, headers: dict | None = None, timeout: int = 5) -> int:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# ── provider implementations ──

class Provider:
    family: str  # "ollama" | "claude" | "gemini" | "openai"
    label: str   # human-readable identity, e.g. "claude-haiku-4-5"

    def review(self, prompt: str, timeout: int = 240) -> dict:
        raise NotImplementedError


class OllamaProvider(Provider):
    family = "ollama"

    def __init__(self, model: str, host_label: str, endpoint: str):
        self.model = model
        self.host = host_label
        self.endpoint = endpoint
        self.label = f"{model}@{host_label}"

    def review(self, prompt: str, timeout: int = 240) -> dict:
        body = _http_post(
            f"{self.endpoint}/api/generate",
            {"model": self.model, "prompt": prompt + "\n\nReturn ONLY valid JSON.",
             "stream": False, "options": {"temperature": 0.2}},
            headers={},
            timeout=timeout,
        )
        return _extract_json(body.get("response", ""))


class ClaudeProvider(Provider):
    family = "claude"

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.model = model
        self.label = model
        self.api_key = os.environ["ANTHROPIC_API_KEY"]

    def review(self, prompt: str, timeout: int = 240) -> dict:
        body = _http_post(
            "https://api.anthropic.com/v1/messages",
            {"model": self.model, "max_tokens": 2048, "temperature": 0.2,
             "messages": [{"role": "user", "content": prompt + "\n\nReturn ONLY a JSON object."}]},
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            timeout=timeout,
        )
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
        return _extract_json(text)


class GeminiProvider(Provider):
    family = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self.label = model
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]

    def review(self, prompt: str, timeout: int = 240) -> dict:
        body = _http_post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}",
            {"contents": [{"parts": [{"text": prompt}]}],
             "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}},
            headers={},
            timeout=timeout,
        )
        text = "".join(p.get("text", "") for p in body["candidates"][0]["content"]["parts"])
        return _extract_json(text)


class OpenAIProvider(Provider):
    family = "openai"

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.label = model
        self.api_key = os.environ["OPENAI_API_KEY"]

    def review(self, prompt: str, timeout: int = 240) -> dict:
        body = _http_post(
            "https://api.openai.com/v1/chat/completions",
            {"model": self.model, "temperature": 0.2,
             "response_format": {"type": "json_object"},
             "messages": [{"role": "user", "content": prompt}]},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=timeout,
        )
        text = body["choices"][0]["message"]["content"]
        return _extract_json(text)


# ── availability probes ──

# Lazy import to avoid hard dep on fleet_client when only API providers are used.
def _ollama_endpoints() -> dict[str, str]:
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from fleet_client import ENDPOINTS  # type: ignore
        return ENDPOINTS
    except Exception:
        return {}


def _ollama_reachable(endpoint: str) -> bool:
    return _http_get(f"{endpoint}/api/tags", timeout=2) == 200


def detect_available() -> list[Callable[[], Provider]]:
    """Return constructor lambdas for every provider whose creds/connectivity
    look good. Order matters: callers walk this list to pick a pair."""
    available: list[Callable[[], Provider]] = []

    eps = _ollama_endpoints()
    sam_ep = eps.get("sam")
    archie_ep = eps.get("archie")
    if sam_ep and _ollama_reachable(sam_ep):
        available.append(lambda: OllamaProvider("llama3.1:8b", "sam", sam_ep))
    if archie_ep and _ollama_reachable(archie_ep):
        available.append(lambda: OllamaProvider("qwen2.5-coder:14b", "archie", archie_ep))

    if os.environ.get("ANTHROPIC_API_KEY"):
        available.append(lambda: ClaudeProvider())
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        available.append(lambda: GeminiProvider())
    if os.environ.get("OPENAI_API_KEY"):
        available.append(lambda: OpenAIProvider())

    return available


def auto_pair(lenses: tuple[str, str]) -> tuple[Provider, Provider]:
    """Pick two reviewers from different families. Prefer the proven Sam/Archie
    ollama pair when both are reachable; otherwise pick top two from
    [claude, gemini, openai] in that priority order."""
    constructors = detect_available()
    instantiated: list[Provider] = []
    for c in constructors:
        try:
            instantiated.append(c())
        except Exception:
            pass

    # Case 1: both ollama hosts up → preserve original Sam/Archie behaviour.
    sam = next((p for p in instantiated if isinstance(p, OllamaProvider) and p.host == "sam"), None)
    archie = next((p for p in instantiated if isinstance(p, OllamaProvider) and p.host == "archie"), None)
    if sam and archie:
        return sam, archie

    # Case 2: pick two distinct families from API providers in priority order.
    priority = ["claude", "gemini", "openai", "ollama"]
    by_family: dict[str, Provider] = {}
    for p in instantiated:
        by_family.setdefault(p.family, p)
    chosen: list[Provider] = []
    for fam in priority:
        if fam in by_family:
            chosen.append(by_family[fam])
            if len(chosen) == 2:
                break

    if len(chosen) < 2:
        raise RuntimeError(
            "Need two reviewers from different model families. Available: "
            f"{[p.label for p in instantiated] or 'none'}. Set at least two of "
            "ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY, or bring up "
            "two ollama hosts (sam + archie)."
        )
    return chosen[0], chosen[1]


def build_pair(spec: str | None, lenses: tuple[str, str]) -> tuple[Provider, Provider]:
    """spec is None → auto. Otherwise comma-separated, e.g. 'claude,gemini'
    or 'ollama:sam,ollama:archie'."""
    if not spec or spec == "auto":
        return auto_pair(lenses)

    parts = [s.strip() for s in spec.split(",")]
    if len(parts) != 2:
        raise ValueError(f"--provider must be 'auto' or two comma-separated providers, got: {spec!r}")

    def make(token: str) -> Provider:
        if token.startswith("ollama:"):
            host = token.split(":", 1)[1]
            eps = _ollama_endpoints()
            if host not in eps:
                raise ValueError(f"unknown ollama host: {host}")
            model = "llama3.1:8b" if host == "sam" else "qwen2.5-coder:14b"
            return OllamaProvider(model, host, eps[host])
        if token == "claude":
            return ClaudeProvider()
        if token == "gemini":
            return GeminiProvider()
        if token == "openai":
            return OpenAIProvider()
        raise ValueError(f"unknown provider: {token}")

    a, b = make(parts[0]), make(parts[1])
    if a.family == b.family:
        sys.stderr.write(
            f"WARN: both reviewers are family={a.family}. Decorrelated errors "
            "require different families — results may be lower-signal.\n"
        )
    return a, b
