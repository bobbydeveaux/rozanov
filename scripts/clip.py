#!/usr/bin/env python3
"""
clip.py — cut final mp3s from approved matches

Usage:
    python scripts/clip.py [--dry-run]

Reads:    scripts/matches.json  (entries with status="approved")
Output:   website/public/audio/<id>.mp3
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
MATCHES_FILE = SCRIPT_DIR / "matches.json"
AUDIO_OUT = REPO_ROOT / "website" / "public" / "audio"


def ffmpeg_clip(source: Path, start: float, end: float, out: Path) -> bool:
    duration = round(end - start, 3)
    fade = min(0.1, duration * 0.05)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),      # seek BEFORE -i for fast + accurate extraction
        "-i", str(source),
        "-t", str(duration),    # duration from start, not absolute end time
        "-af", f"afade=t=in:st=0:d={fade},afade=t=out:st={duration - fade}:d={fade}",
        "-ar", "44100",
        "-b:a", "128k",
        "-map_metadata", "-1",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ffmpeg error:\n{result.stderr[-300:]}")
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without writing files")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found.")
        sys.exit(1)

    if not MATCHES_FILE.exists():
        print(f"ERROR: {MATCHES_FILE} not found. Run: python scripts/match.py")
        sys.exit(1)

    matches = json.loads(MATCHES_FILE.read_text())

    approved = [m for m in matches if m.get("status") == "approved"]
    review   = [m for m in matches if m.get("status") == "review"]
    missing  = [m for m in matches if m.get("status") == "not_found"]

    print(f"Approved: {len(approved)}  |  Needs review: {len(review)}  |  Not found: {len(missing)}\n")

    if not approved:
        print("No approved matches. Open scripts/matches.json and set status='approved'")
        print("on entries whose timestamps you've verified, then re-run.")
        sys.exit(0)

    if args.dry_run:
        print("DRY RUN — no files will be written\n")

    AUDIO_OUT.mkdir(parents=True, exist_ok=True)

    done = 0
    failed = 0

    for m in approved:
        qid = m["id"]
        source_rel = m["source_file"]
        start = float(m["start"])
        end = float(m["end"])
        out_file = AUDIO_OUT / f"{qid}.mp3"

        duration = round(end - start, 1)
        print(f"  {qid}")
        print(f"    {source_rel}  [{start}s → {end}s  ({duration}s)]")

        if args.dry_run:
            print(f"    → {out_file}\n")
            continue

        # source_file is stored as "raw/x.mp3" — resolve relative to SCRIPT_DIR or REPO_ROOT
        source_path = SCRIPT_DIR / source_rel if (SCRIPT_DIR / source_rel).exists() else REPO_ROOT / source_rel
        if not source_path.exists():
            print(f"    ✗ source not found: {source_path}\n")
            failed += 1
            continue

        if ffmpeg_clip(source_path, start, end, out_file):
            size_kb = out_file.stat().st_size // 1024
            print(f"    ✓ {out_file.name}  ({size_kb} kB)\n")
            done += 1
        else:
            failed += 1
            print()

    print("─" * 50)
    print(f"Done: {done} clipped, {failed} failed")

    if review:
        print(f"\nStill needs review ({len(review)}):")
        for m in review:
            print(f"  - {m['id']}")

    if missing:
        print(f"\nNot found in any clip ({len(missing)}) — add more source URLs to clips.txt:")
        for m in missing:
            print(f"  - {m['id']}: \"{m['quote'][:60]}\"")


if __name__ == "__main__":
    main()
