#!/usr/bin/env python3
"""
transcribe.py — run OpenAI Whisper on all files in scripts/raw/
and write word-level JSON transcriptions to scripts/transcriptions/

Usage:
    python scripts/transcribe.py [--model medium] [--force]

Requires:
    pip install openai-whisper

Output:
    scripts/transcriptions/<id>.json  — one file per audio source
"""

import argparse
import json
import os
import ssl
import sys
from pathlib import Path

# Fix macOS Python SSL certificate verification issue
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    ssl._create_default_https_context = ssl.create_default_context
except ImportError:
    pass

SCRIPT_DIR = Path(__file__).parent
RAW_DIR = SCRIPT_DIR / "raw"
OUT_DIR = SCRIPT_DIR / "transcriptions"
AUDIO_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg"}


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio with Whisper")
    parser.add_argument("--model", default="medium",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: medium)")
    parser.add_argument("--force", action="store_true",
                        help="Re-transcribe even if output already exists")
    args = parser.parse_args()

    try:
        import whisper
    except ImportError:
        print("ERROR: openai-whisper not installed. Run: pip install openai-whisper")
        sys.exit(1)

    audio_files = [
        f for f in sorted(RAW_DIR.iterdir())
        if f.suffix.lower() in AUDIO_EXTENSIONS and not f.name.endswith(".info.json")
    ]

    if not audio_files:
        print(f"No audio files found in {RAW_DIR}")
        print("Run ./scripts/download.sh first.")
        sys.exit(0)

    OUT_DIR.mkdir(exist_ok=True)

    print(f"Loading Whisper model: {args.model}")
    model = whisper.load_model(args.model)
    print(f"Model loaded. Transcribing {len(audio_files)} file(s)...\n")

    for i, audio_file in enumerate(audio_files, 1):
        out_file = OUT_DIR / (audio_file.stem + ".json")

        if out_file.exists() and not args.force:
            print(f"[{i}/{len(audio_files)}] {audio_file.name} — skipped (already transcribed)")
            continue

        print(f"[{i}/{len(audio_files)}] {audio_file.name} ...")

        result = model.transcribe(
            str(audio_file),
            word_timestamps=True,
            language="en",        # set to None to auto-detect (slower)
            verbose=False,
        )

        # Flatten to a clean structure: full text + word-level timestamps
        words = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                words.append({
                    "word": word_info["word"].strip(),
                    "start": round(word_info["start"], 3),
                    "end": round(word_info["end"], 3),
                })

        output = {
            "source": audio_file.name,
            "text": result["text"].strip(),
            "words": words,
        }

        out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"     ✓ {len(words)} words — saved to {out_file.name}")
        print(f"     Preview: {result['text'][:120].strip()}...")
        print()

    print("Transcription complete.")
    print(f"Next: python scripts/match.py")


if __name__ == "__main__":
    main()
