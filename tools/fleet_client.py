"""Thin client for the local LLM fleet (Ollama endpoints over Tailscale).

Usage:
    from fleet_client import call, call_json, ENDPOINTS

    text = call("llama3.1:8b", "Say hi.", endpoint=ENDPOINTS["sam"])
    data = call_json("llama3.1:8b", prompt, schema={...}, endpoint=ENDPOINTS["sam"])

No auth — Tailscale is the perimeter. No native JSON mode; we prompt for JSON
and validate the parse. Per fleet eval notes: single-pass only, never "revise".
"""
from __future__ import annotations
import json
import re
import urllib.request
import urllib.error
from typing import Any

ENDPOINTS = {
    "sam":    "http://100.127.46.63:11434",   # llama3.1:8b — structured JSON / classification
    "archie": "http://100.103.192.41:11434",  # qwen2.5-coder:14b — code parsing
    "lenny":  "http://100.78.179.55:11434",   # gemma3:27b / qwen3-coder:30b — design, code
    "mbp":    "http://100.95.59.11:11434",    # qwen3-coder:30b — code-gen fallback
}

JSON_SUFFIX = '\n\nReturn ONLY valid JSON. No prose, no markdown fences, no explanation.'

THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def call(model: str, prompt: str, *, endpoint: str, timeout: int = 180,
         temperature: float = 0.2, system: str | None = None) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    req = urllib.request.Request(
        f"{endpoint}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read())
    text = body.get("response", "")
    return THINK_BLOCK.sub("", text).strip()


def _extract_json(text: str) -> Any:
    text = FENCE.sub("", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: grab the largest {...} or [...] block.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Model did not return valid JSON. Got:\n{text[:500]}")


def call_json(model: str, prompt: str, *, endpoint: str, timeout: int = 180,
              temperature: float = 0.1, system: str | None = None,
              required_keys: list[str] | None = None) -> Any:
    """Call a model and parse JSON from its response.

    Single-pass by design. If parsing fails, raises — caller decides whether
    to retry with a *different* prompt (never "please fix your JSON").
    """
    raw = call(model, prompt + JSON_SUFFIX, endpoint=endpoint,
               timeout=timeout, temperature=temperature, system=system)
    data = _extract_json(raw)
    if required_keys and isinstance(data, dict):
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"Missing required keys {missing}. Got: {list(data.keys())}")
    return data


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "llama3.1:8b"
    ep = ENDPOINTS[sys.argv[2]] if len(sys.argv) > 2 else ENDPOINTS["sam"]
    print(call(model, "Reply with exactly the word: pong", endpoint=ep))
