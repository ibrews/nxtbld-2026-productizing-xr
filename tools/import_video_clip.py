#!/usr/bin/env python3
"""Import a video clip from a URL or local file: trim, re-encode, optionally cap size.

Three modes:
  1. URL + trim (default for YouTube): yt-dlp downloads only the requested
     window, ffmpeg re-trims and re-encodes. Quality preserved at full CRF
     unless --max-mb caps the size.
  2. Local file + trim: skip the download, run ffmpeg directly on the local
     file. Use this for Drive videos (download manually) or for two-phase
     YouTube workflows where you want to scrub before deciding the cut.
  3. --download-only: yt-dlp grabs the requested window (or the full video
     if --start/--end omitted) without re-encoding. Lets you preview at
     full quality in QuickTime, then re-run in mode 2 against the local file.

By default, --max-mb is 0 (no cap, preserve quality). Pass --max-mb 95 to
re-enable the GitHub-friendly auto-shrink ladder (1280→960→854→640).

Usage:
    # YouTube URL, single shot, full quality (no size cap)
    python3 tools/import_video_clip.py URL --start 1:23 --duration 5 --out clip.mp4

    # Drive workflow: after manually downloading, trim the local file
    python3 tools/import_video_clip.py ~/Downloads/video.mp4 --start 0:30 --end 0:38 \\
        --out media/fmx/intro.mp4

    # Two-phase YouTube: download for scrubbing, then trim
    python3 tools/import_video_clip.py URL --download-only --out work/raw/source.mp4
    python3 tools/import_video_clip.py work/raw/source.mp4 --start 1:23 --end 1:45 \\
        --out media/fmx/clip.mp4

    # Cap output size (re-enables auto-shrink fallback chain)
    python3 tools/import_video_clip.py URL --start 0:00 --end 5:00 --max-mb 95 \\
        --out media/promo/long.mp4

No external pip deps — stdlib only. Requires yt-dlp and ffmpeg on PATH.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com",
            "music.youtube.com", "youtu.be"}
DRIVE_HOSTS = {"drive.google.com", "docs.google.com"}

QUALITY_PRESETS = {
    "high":   {"width": 1280, "crf": 21},
    "medium": {"width": 1280, "crf": 23},
    "low":    {"width": 960,  "crf": 28},
}

# Auto-shrink ladder when a clip exceeds --max-mb.
# Each entry: (width, crf_bump_above_initial)
FALLBACK_LADDER = [
    (960, 3),
    (854, 6),
    (640, 9),
]

DRIVE_RECIPE = """\
Drive video detected. Download the file manually (one-time):
  1. Open the Drive URL in your browser, click ⋮ → "Download"
  2. Move the downloaded file to a working dir (e.g. work/raw/)
  3. Run this tool again with the local path:
       python3 tools/import_video_clip.py work/raw/<filename> --start 1:23 --end 1:45 --out media/...
"""


def parse_time(s: str) -> float:
    """Parse '83', '83.5', '1:23', '1:23.5', '1:02:03', '1:02:03.5' -> seconds."""
    if s is None:
        raise ValueError("empty time")
    s = str(s).strip()
    if not s:
        raise ValueError("empty time")
    # Plain number
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    # m:s or h:m:s, with optional .frac on the seconds field
    if not re.fullmatch(r"\d+:\d{1,2}(:\d{1,2})?(\.\d+)?", s):
        raise ValueError(f"unrecognized time format: {s!r}")
    parts = s.split(":")
    try:
        if len(parts) == 2:
            m, sec = int(parts[0]), float(parts[1])
            return m * 60 + sec
        elif len(parts) == 3:
            h, m, sec = int(parts[0]), int(parts[1]), float(parts[2])
            return h * 3600 + m * 60 + sec
    except ValueError as e:
        raise ValueError(f"bad time field in {s!r}: {e}")
    raise ValueError(f"unrecognized time format: {s!r}")


def detect_url_kind(s: str) -> str:
    """Return 'youtube', 'drive', 'local', 'unknown_url', or 'unknown'."""
    # Local file first — anything that resolves on disk wins.
    try:
        if Path(s).expanduser().is_file():
            return "local"
    except (OSError, ValueError):
        pass
    # Otherwise treat as URL.
    try:
        parsed = urlparse(s)
        host = (parsed.hostname or "").lower()
        scheme = (parsed.scheme or "").lower()
    except Exception:
        return "unknown"
    if scheme not in ("http", "https"):
        return "unknown"
    if host in YT_HOSTS:
        return "youtube"
    if host in DRIVE_HOSTS:
        return "drive"
    return "unknown_url"


def url_start_param(url: str) -> float | None:
    """Extract ?t=NNs or ?t=NN from a YouTube URL, if present."""
    try:
        q = parse_qs(urlparse(url).query)
    except Exception:
        return None
    raw = q.get("t", [None])[0] or q.get("start", [None])[0]
    if raw is None:
        return None
    m = re.fullmatch(r"(\d+)s?", raw)
    if m:
        return float(m.group(1))
    try:
        return parse_time(raw)
    except ValueError:
        return None


def fmt_seconds(sec: float) -> str:
    """Format seconds for ffmpeg/yt-dlp (HH:MM:SS.mmm)."""
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec - (h * 3600) - (m * 60)
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def run(cmd: list[str], dry_run: bool = False) -> subprocess.CompletedProcess:
    if dry_run:
        print("DRY:", " ".join(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def ffprobe_streams(path: Path) -> dict:
    cp = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path)
    ])
    return json.loads(cp.stdout)


def encode(src: Path, dst: Path, *, ss: float, dur: float,
           width: int, crf: int, audio: str, dry_run: bool = False) -> None:
    """Re-encode src -> dst with the given trim and quality settings."""
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", fmt_seconds(ss),
        "-i", str(src),
        "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-vf", f"scale={width}:-2:flags=lanczos",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]
    if audio == "mute":
        cmd += ["-an"]
    else:
        cmd += ["-c:a", "aac", "-b:a", "96k"]
    cmd += [str(dst)]
    run(cmd, dry_run=dry_run)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Import a video clip from a YouTube URL or local file. "
            "Trims and re-encodes by default; --download-only skips the "
            "encode pass. Drive URLs require manual download (see error "
            "message for recipe)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("source",
                    help=("YouTube URL (youtube.com / youtu.be / "
                          "music.youtube.com / m.youtube.com) OR a local "
                          "video file path. Drive URLs are rejected with a "
                          "manual-download recipe."))
    ap.add_argument("--start", help="Start timecode (e.g. 1:23, 83, 1:02:03)")
    ap.add_argument("--end", help="End timecode")
    ap.add_argument("--duration", type=float, help="Clip duration in seconds")
    ap.add_argument("--out", required=True, help="Output mp4 path")
    ap.add_argument("--max-mb", type=float, default=0.0,
                    help=("Max output size in MB. 0 = no size cap (default), "
                          "preserves quality. Set e.g. 95 to re-enable the "
                          "auto-shrink ladder (1280→960→854→640) for the "
                          "GitHub 100MB limit."))
    ap.add_argument("--quality", choices=list(QUALITY_PRESETS.keys()),
                    default="high",
                    help=("Initial encode preset (default 'high' = 1280px / "
                          "CRF 21). Lower presets only matter when --max-mb "
                          "is set or as the starting point for the shrink "
                          "ladder."))
    ap.add_argument("--start-from-url", action="store_true",
                    help="Use ?t=Ns from URL as default --start if not given")
    ap.add_argument("--audio", choices=["keep", "mute"], default="keep",
                    help="Keep or strip audio")
    ap.add_argument("--no-fallback", action="store_true",
                    help=("Disable auto-shrink retry loop even when --max-mb "
                          "is set (single attempt only)."))
    ap.add_argument("--download-only", action="store_true",
                    help=("Download from a URL without re-encoding. "
                          "Requires a URL source (not a local file). "
                          "If --start and --end/--duration are both omitted, "
                          "downloads the full video. If both are provided, "
                          "downloads just that window via "
                          "yt-dlp --download-sections."))
    ap.add_argument("--dry-run", action="store_true",
                    help="Print commands but don't execute")
    args = ap.parse_args()

    # ── Resolve source kind ──
    kind = detect_url_kind(args.source)
    if kind == "drive":
        print("ERROR: " + DRIVE_RECIPE, file=sys.stderr)
        return 2
    if kind == "unknown_url":
        print(f"ERROR: unsupported URL host: {args.source!r}. "
              f"Only YouTube URLs and local file paths are supported.",
              file=sys.stderr)
        return 2
    if kind == "unknown":
        print(f"ERROR: source {args.source!r} is neither a recognized URL "
              f"nor an existing local file.", file=sys.stderr)
        return 2

    is_local = (kind == "local")

    # ── --download-only validation ──
    if args.download_only and is_local:
        print("ERROR: --download-only requires a URL, not a local file.",
              file=sys.stderr)
        return 2

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Branch: --download-only ──
    if args.download_only:
        # Optional trim window. If neither --start nor end/dur, download full.
        seg_args: list[str] = []
        has_start = args.start is not None
        has_end = args.end is not None
        has_dur = args.duration is not None
        if has_start or has_end or has_dur:
            # Resolve start
            if has_start:
                try:
                    start = parse_time(args.start)
                except ValueError as e:
                    print(f"ERROR: bad --start value: {e}", file=sys.stderr)
                    return 2
            else:
                # Allow --end/--duration without --start? require start.
                print("ERROR: with --download-only, --start is required if "
                      "you also pass --end or --duration. Pass none of them "
                      "to download the full video.", file=sys.stderr)
                return 2
            if has_end == has_dur:
                print("ERROR: pass exactly one of --end or --duration "
                      "(or omit both for full-video download).",
                      file=sys.stderr)
                return 2
            if has_end:
                try:
                    end = parse_time(args.end)
                except ValueError as e:
                    print(f"ERROR: bad --end value: {e}", file=sys.stderr)
                    return 2
            else:
                end = start + float(args.duration)
            if end <= start:
                print(f"ERROR: end ({end}) must be greater than "
                      f"start ({start})", file=sys.stderr)
                return 2
            seg_args = [
                "--download-sections",
                f"*{fmt_seconds(start)}-{fmt_seconds(end)}",
                "--force-keyframes-at-cuts",
            ]

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            src_tpl = str(tmp / "source.%(ext)s")
            ytdlp_cmd = [
                "yt-dlp",
                "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
                "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                *seg_args,
                "-o", src_tpl,
                args.source,
            ]
            try:
                run(ytdlp_cmd, dry_run=args.dry_run)
            except subprocess.CalledProcessError as e:
                print("ERROR: yt-dlp failed", file=sys.stderr)
                if e.stderr:
                    print(e.stderr, file=sys.stderr)
                if e.stdout:
                    print(e.stdout, file=sys.stderr)
                return 1

            if args.dry_run:
                print(f"DRY: would move <yt-dlp output> -> {out_path}")
                return 0

            candidates = sorted(tmp.glob("source.*"))
            if not candidates:
                print("ERROR: yt-dlp produced no output file",
                      file=sys.stderr)
                return 1
            src = candidates[0]
            os.replace(src, out_path)

        sz_mb = out_path.stat().st_size / 1024 / 1024
        print(f"OK (download-only): {out_path}")
        print(f"  source: {args.source}")
        print(f"  size:   {sz_mb:.2f}MB")
        return 0

    # ── Trim mode: resolve start ──
    if args.start is None and args.start_from_url:
        if is_local:
            print("ERROR: --start-from-url requires a URL source, not a "
                  "local file.", file=sys.stderr)
            return 2
        url_start = url_start_param(args.source)
        if url_start is None:
            print("ERROR: --start-from-url given but URL has no ?t= parameter",
                  file=sys.stderr)
            return 2
        start = url_start
    elif args.start is None:
        print("ERROR: --start is required (or pass --start-from-url with a "
              "URL that has ?t=Ns)", file=sys.stderr)
        return 2
    else:
        try:
            start = parse_time(args.start)
        except ValueError as e:
            print(f"ERROR: bad --start value: {e}", file=sys.stderr)
            return 2

    # ── Resolve end / duration (exactly one) ──
    if (args.end is None) == (args.duration is None):
        print("ERROR: pass exactly one of --end or --duration", file=sys.stderr)
        return 2
    if args.end is not None:
        try:
            end = parse_time(args.end)
        except ValueError as e:
            print(f"ERROR: bad --end value: {e}", file=sys.stderr)
            return 2
    else:
        end = start + float(args.duration)
    if end <= start:
        print(f"ERROR: end ({end}) must be greater than start ({start})",
              file=sys.stderr)
        return 2
    duration = end - start

    preset = QUALITY_PRESETS[args.quality]
    init_w, init_crf = preset["width"], preset["crf"]
    has_size_cap = args.max_mb > 0
    max_bytes = int(args.max_mb * 1024 * 1024) if has_size_cap else 0

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        if is_local:
            src = Path(args.source).expanduser().resolve()
            start_offset = start
        else:
            # ── yt-dlp segment download ──
            src_tpl = str(tmp / "source.%(ext)s")
            # Pad both sides slightly to ensure we have enough material to trim
            # precisely after keyframe alignment.
            seg_start = max(0.0, start - 1.0)
            seg_end = end + 1.0
            ytdlp_cmd = [
                "yt-dlp",
                "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
                "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                "--download-sections",
                f"*{fmt_seconds(seg_start)}-{fmt_seconds(seg_end)}",
                "--force-keyframes-at-cuts",
                "-o", src_tpl,
                args.source,
            ]
            try:
                run(ytdlp_cmd, dry_run=args.dry_run)
            except subprocess.CalledProcessError as e:
                print("ERROR: yt-dlp failed", file=sys.stderr)
                if e.stderr:
                    print(e.stderr, file=sys.stderr)
                if e.stdout:
                    print(e.stdout, file=sys.stderr)
                return 1

            if args.dry_run:
                fake_src = tmp / "source.mp4"
                tmp_out = tmp / "out.mp4"
                encode(fake_src, tmp_out,
                       ss=0.0, dur=duration, width=init_w, crf=init_crf,
                       audio=args.audio, dry_run=True)
                print(f"DRY: would move {tmp_out} -> {out_path}")
                return 0

            candidates = sorted(tmp.glob("source.*"))
            if not candidates:
                print("ERROR: yt-dlp produced no output file",
                      file=sys.stderr)
                return 1
            src = candidates[0]

            # ── ffprobe to find segment_start ──
            try:
                meta = ffprobe_streams(src)
            except subprocess.CalledProcessError as e:
                print("ERROR: ffprobe failed on downloaded segment",
                      file=sys.stderr)
                if e.stderr:
                    print(e.stderr, file=sys.stderr)
                return 1
            try:
                seg_actual_start = float(meta.get("format", {})
                                             .get("start_time", "0") or 0.0)
            except (TypeError, ValueError):
                seg_actual_start = 0.0
            if seg_actual_start < 0.5:
                start_offset = max(0.0, start - seg_start)
            else:
                start_offset = max(0.0, start - seg_actual_start)

        if args.dry_run and is_local:
            tmp_out = tmp / "out.mp4"
            encode(src, tmp_out,
                   ss=start_offset, dur=duration,
                   width=init_w, crf=init_crf,
                   audio=args.audio, dry_run=True)
            print(f"DRY: would move {tmp_out} -> {out_path}")
            return 0

        # ── Encode (single pass if no cap; retry loop if --max-mb set) ──
        attempts: list[tuple[int, int]] = [(init_w, init_crf)]
        if has_size_cap and not args.no_fallback:
            for w, crf_bump in FALLBACK_LADDER:
                attempts.append((w, init_crf + crf_bump))

        tmp_out = tmp / "out.mp4"
        final_size = -1
        final_w, final_crf = init_w, init_crf
        size_ok = False
        for i, (w, crf) in enumerate(attempts, 1):
            try:
                encode(src, tmp_out,
                       ss=start_offset, dur=duration,
                       width=w, crf=crf, audio=args.audio)
            except subprocess.CalledProcessError as e:
                print(f"ERROR: ffmpeg encode failed (attempt {i}, "
                      f"{w}px crf{crf})", file=sys.stderr)
                if e.stderr:
                    print(e.stderr, file=sys.stderr)
                return 1
            sz = tmp_out.stat().st_size
            final_size, final_w, final_crf = sz, w, crf
            if not has_size_cap or sz <= max_bytes:
                size_ok = True
                break
            print(f"  attempt {i}: {sz/1024/1024:.2f}MB at {w}px crf{crf} "
                  f"-> over {args.max_mb}MB, retrying…", file=sys.stderr)
        if has_size_cap and not size_ok:
            print(f"ERROR: clip is {final_size/1024/1024:.2f}MB at lowest "
                  f"quality ({final_w}px crf{final_crf}); use --duration N "
                  f"to shorten or raise --max-mb", file=sys.stderr)
            return 1

        # ── Atomic move ──
        os.replace(tmp_out, out_path)

    # ── Summary ──
    final_meta = ffprobe_streams(out_path)
    vstream = next((s for s in final_meta.get("streams", [])
                    if s.get("codec_type") == "video"), None)
    astream = next((s for s in final_meta.get("streams", [])
                    if s.get("codec_type") == "audio"), None)
    out_dur = float(final_meta.get("format", {}).get("duration", 0.0))
    sz_mb = out_path.stat().st_size / 1024 / 1024
    vcodec = vstream.get("codec_name") if vstream else "none"
    vw = vstream.get("width") if vstream else "?"
    vh = vstream.get("height") if vstream else "?"
    acodec = astream.get("codec_name") if astream else "none"

    print(f"OK: {out_path}")
    print(f"  source:    {args.source}{' (local)' if is_local else ''}")
    print(f"  requested: {duration:.2f}s ({fmt_seconds(start)} -> "
          f"{fmt_seconds(end)})")
    print(f"  output:    {out_dur:.2f}s, {vw}x{vh}, "
          f"{vcodec}/{acodec}, {sz_mb:.2f}MB")
    print(f"  encode:    {final_w}px crf{final_crf}"
          f"{'' if has_size_cap else ' (no size cap)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
