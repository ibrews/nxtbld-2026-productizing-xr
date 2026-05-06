#!/usr/bin/env python3
"""Download a YouTube clip, trim it, and re-encode under a size budget.

Pipeline:
  1. yt-dlp downloads only the requested time window (--download-sections).
     This is keyframe-aligned, so the actual segment is usually a second or
     two longer than asked at the head.
  2. ffprobe inspects the segment to find its true start time.
  3. ffmpeg re-trims to exact start/duration and re-encodes h264/aac with
     a CRF tuned to a quality preset.
  4. If the result is over --max-mb (default 95, headroom under GitHub's
     100MB limit), an auto-shrink loop retries with progressively smaller
     resolutions and higher CRFs.
  5. On success, the temp output is moved atomically to --out.

Usage:
    python3 tools/import_video_clip.py URL --start 1:23 --duration 5 --out clip.mp4
    python3 tools/import_video_clip.py URL --start 0:30 --end 0:35 --out clip.mp4 \\
        --quality high --audio mute

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


def detect_url_kind(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return "unknown"
    if host in YT_HOSTS:
        return "youtube"
    if host in DRIVE_HOSTS:
        return "drive"
    return "unknown"


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
        description="Download a YouTube clip, trim it, re-encode under a size budget.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("url", help="YouTube watch URL or short URL")
    ap.add_argument("--start", help="Start timecode (e.g. 1:23, 83, 1:02:03)")
    ap.add_argument("--end", help="End timecode")
    ap.add_argument("--duration", type=float, help="Clip duration in seconds")
    ap.add_argument("--out", required=True, help="Output mp4 path")
    ap.add_argument("--max-mb", type=float, default=95.0,
                    help="Max output size in MB (default 95)")
    ap.add_argument("--quality", choices=list(QUALITY_PRESETS.keys()),
                    default="medium", help="Initial encode preset")
    ap.add_argument("--start-from-url", action="store_true",
                    help="Use ?t=Ns from URL as default --start if not given")
    ap.add_argument("--audio", choices=["keep", "mute"], default="keep",
                    help="Keep or strip audio")
    ap.add_argument("--no-fallback", action="store_true",
                    help="Disable auto-shrink retry loop")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print commands but don't execute")
    args = ap.parse_args()

    # ── Resolve URL kind ──
    kind = detect_url_kind(args.url)
    if kind == "drive":
        ff_hint = (
            "ffmpeg -ss <start> -t <dur> -i <downloaded.mp4> "
            "-c:v libx264 -crf 23 -vf scale=1280:-2 -c:a aac -b:a 96k "
            "-movflags +faststart <out.mp4>"
        )
        print("ERROR: Drive support not yet implemented — download manually "
              "then use ffmpeg directly:\n  " + ff_hint, file=sys.stderr)
        return 2
    if kind != "youtube":
        print(f"ERROR: unsupported URL host: {args.url!r}. "
              f"Only YouTube is supported.", file=sys.stderr)
        return 2

    # ── Resolve start ──
    if args.start is None and args.start_from_url:
        url_start = url_start_param(args.url)
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

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    preset = QUALITY_PRESETS[args.quality]
    init_w, init_crf = preset["width"], preset["crf"]
    max_bytes = int(args.max_mb * 1024 * 1024)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src_tpl = str(tmp / "source.%(ext)s")

        # ── yt-dlp ──
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
            args.url,
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
            # Show what the encode call would look like.
            fake_src = tmp / "source.mp4"
            tmp_out = tmp / "out.mp4"
            encode(fake_src, tmp_out,
                   ss=0.0, dur=duration, width=init_w, crf=init_crf,
                   audio=args.audio, dry_run=True)
            print(f"DRY: would move {tmp_out} -> {out_path}")
            return 0

        # Find the downloaded file.
        candidates = sorted(tmp.glob("source.*"))
        if not candidates:
            print("ERROR: yt-dlp produced no output file", file=sys.stderr)
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
        # Best estimate: format start_time. yt-dlp segment downloads keep the
        # original timeline timestamps.
        try:
            seg_actual_start = float(meta.get("format", {})
                                         .get("start_time", "0") or 0.0)
        except (TypeError, ValueError):
            seg_actual_start = 0.0
        # If the format start_time is approximately the requested seg_start,
        # the file is already trimmed-on-timeline; in that case offset is the
        # difference between desired start and seg_start.
        # In practice yt-dlp re-bases timestamps to 0 in the output, so we
        # assume the file starts at seg_start (the requested pre-pad), and
        # the offset within the file is start - seg_start.
        # We trust seg_start if format start_time is ~0.
        if seg_actual_start < 0.5:
            start_offset = max(0.0, start - seg_start)
        else:
            start_offset = max(0.0, start - seg_actual_start)

        # ── Encode w/ size-fit retry loop ──
        attempts: list[tuple[int, int]] = [(init_w, init_crf)]
        if not args.no_fallback:
            for w, crf_bump in FALLBACK_LADDER:
                attempts.append((w, init_crf + crf_bump))

        tmp_out = tmp / "out.mp4"
        final_size = -1
        final_w, final_crf = init_w, init_crf
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
            if sz <= max_bytes:
                break
            print(f"  attempt {i}: {sz/1024/1024:.2f}MB at {w}px crf{crf} "
                  f"-> over {args.max_mb}MB, retrying…", file=sys.stderr)
        else:
            # All attempts failed the size budget.
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
    print(f"  requested: {duration:.2f}s ({fmt_seconds(start)} -> "
          f"{fmt_seconds(end)})")
    print(f"  output:    {out_dur:.2f}s, {vw}x{vh}, "
          f"{vcodec}/{acodec}, {sz_mb:.2f}MB")
    print(f"  encode:    {final_w}px crf{final_crf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
