#!/usr/bin/env python3
"""
match.py — fuzzy-match known quotes against Whisper transcriptions
to find the timestamp of each soundbite automatically.

Usage:
    python scripts/match.py [--threshold 0.6] [--pad 0.3]

Output:
    scripts/matches.json  — review and adjust before running clip.sh

Workflow:
    1. Run this script
    2. Open scripts/matches.json
    3. Review each match — check 'matched_text' looks right
    4. Adjust 'start' / 'end' timestamps if needed (seconds)
    5. Change 'status' from 'review' to 'approved' for each one
    6. Run ./scripts/clip.sh
"""

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
QUOTES_FILE = SCRIPT_DIR / "quotes.json"
TRANS_DIR = SCRIPT_DIR / "transcriptions"
OUT_FILE = SCRIPT_DIR / "matches.json"

# How much silence/context to add around each clip (seconds)
DEFAULT_PAD = 0.3
# Minimum similarity ratio to consider a match
DEFAULT_THRESHOLD = 0.55


def normalise(text: str) -> str:
    """Lowercase, strip punctuation for fuzzy comparison."""
    import re
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def words_to_text(words: list) -> str:
    return " ".join(w["word"] for w in words)


def find_best_window(quote: str, words: list, threshold: float):
    """
    Slide a window over the word list, comparing each window's text
    to the target quote. Returns the best match with its timestamps.
    """
    norm_quote = normalise(quote)
    quote_word_count = len(norm_quote.split())

    # Try windows from quote_len-3 to quote_len+5 to handle Whisper variance
    best_ratio = 0.0
    best_start_idx = None
    best_end_idx = None

    for window_size in range(max(1, quote_word_count - 3), quote_word_count + 6):
        for i in range(len(words) - window_size + 1):
            window = words[i: i + window_size]
            window_text = normalise(words_to_text(window))
            ratio = SequenceMatcher(None, norm_quote, window_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start_idx = i
                best_end_idx = i + window_size - 1

    if best_ratio < threshold or best_start_idx is None:
        return None

    return {
        "ratio": round(best_ratio, 3),
        "start_idx": best_start_idx,
        "end_idx": best_end_idx,
        "start": words[best_start_idx]["start"],
        "end": words[best_end_idx]["end"],
        "matched_text": words_to_text(words[best_start_idx: best_end_idx + 1]),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Minimum match ratio 0–1 (default: 0.55)")
    parser.add_argument("--pad", type=float, default=DEFAULT_PAD,
                        help="Seconds of padding around each clip (default: 0.3)")
    args = parser.parse_args()

    quotes = json.loads(QUOTES_FILE.read_text())
    trans_files = sorted(TRANS_DIR.glob("*.json"))

    if not trans_files:
        print(f"No transcriptions found in {TRANS_DIR}")
        print("Run: python scripts/transcribe.py")
        sys.exit(1)

    # Load existing matches so we don't overwrite approved ones
    existing = {}
    if OUT_FILE.exists():
        for m in json.loads(OUT_FILE.read_text()):
            existing[m["id"]] = m

    # Aggregate all words from all transcriptions (with source file tag)
    all_sources = []
    for tf in trans_files:
        data = json.loads(tf.read_text())
        all_sources.append({
            "file": tf.stem,
            "text": data["text"],
            "words": data["words"],
        })

    print(f"Loaded {len(quotes)} quotes, {len(all_sources)} transcription(s)\n")

    results = []

    for q in quotes:
        qid = q["id"]
        quote = q["quote"]

        # Don't re-process already approved matches
        if qid in existing and existing[qid].get("status") == "approved":
            print(f"  {qid:40s} — APPROVED (skipping)")
            results.append(existing[qid])
            continue

        best_match = None
        best_source = None

        for source in all_sources:
            match = find_best_window(quote, source["words"], args.threshold)
            if match and (best_match is None or match["ratio"] > best_match["ratio"]):
                best_match = match
                best_source = source["file"]

        if best_match:
            padded_start = max(0.0, round(best_match["start"] - args.pad, 3))
            padded_end = round(best_match["end"] + args.pad, 3)
            confidence = "high" if best_match["ratio"] >= 0.8 else \
                         "medium" if best_match["ratio"] >= 0.65 else "low"

            entry = {
                "id": qid,
                "quote": quote,
                "source_file": f"raw/{best_source}.mp3",
                "start": padded_start,
                "end": padded_end,
                "matched_text": best_match["matched_text"],
                "similarity": best_match["ratio"],
                "confidence": confidence,
                "status": "review",     # change to "approved" after checking
            }
            flag = "✓" if confidence == "high" else "~" if confidence == "medium" else "?"
            print(f"  {flag} {qid:40s} [{confidence:6s} {best_match['ratio']:.2f}]  "
                  f"{padded_start:.1f}s–{padded_end:.1f}s  from {best_source}")
        else:
            entry = {
                "id": qid,
                "quote": quote,
                "source_file": None,
                "start": None,
                "end": None,
                "matched_text": None,
                "similarity": 0.0,
                "confidence": "none",
                "status": "not_found",  # needs manual intervention
            }
            print(f"  ✗ {qid:40s} — NOT FOUND (add more clips or set timestamps manually)")

        results.append(entry)

    OUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    found = sum(1 for r in results if r["status"] != "not_found")
    approved = sum(1 for r in results if r["status"] == "approved")
    not_found = sum(1 for r in results if r["status"] == "not_found")

    print(f"\n{'─'*60}")
    print(f"  {found}/{len(quotes)} quotes matched  |  {approved} approved  |  {not_found} not found")
    print(f"\nNext steps:")
    print(f"  1. Open scripts/matches.json")
    print(f"  2. Review each entry — check 'matched_text' looks right")
    print(f"  3. Adjust 'start'/'end' if needed")
    print(f"  4. Set 'status' to 'approved' for each correct match")
    print(f"  5. Run: ./scripts/clip.sh")


if __name__ == "__main__":
    main()
