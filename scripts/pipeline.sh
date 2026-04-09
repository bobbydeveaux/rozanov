#!/usr/bin/env bash
# pipeline.sh — full pipeline from clips.txt to website/public/audio/
#
# Usage:
#   ./scripts/pipeline.sh              # runs all steps
#   ./scripts/pipeline.sh --skip-download
#   ./scripts/pipeline.sh --skip-transcribe
#   ./scripts/pipeline.sh --model large   # use a bigger Whisper model
#   ./scripts/pipeline.sh --dry-run       # clip step only previews

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WHISPER_MODEL="medium"
SKIP_DOWNLOAD=false
SKIP_TRANSCRIBE=false
DRY_RUN=""

for arg in "$@"; do
  case "$arg" in
    --skip-download)   SKIP_DOWNLOAD=true ;;
    --skip-transcribe) SKIP_TRANSCRIBE=true ;;
    --dry-run)         DRY_RUN="--dry-run" ;;
    --model)           shift; WHISPER_MODEL="$1" ;;
  esac
done

echo "═══════════════════════════════════════════"
echo "  Rozanov Soundboard — Audio Pipeline"
echo "═══════════════════════════════════════════"
echo ""

# ── Step 1: Download ──────────────────────────
if [[ "$SKIP_DOWNLOAD" == "false" ]]; then
  echo "▶ Step 1/3: Downloading clips..."
  echo ""
  bash "$SCRIPT_DIR/download.sh"
  echo ""
else
  echo "▷ Step 1/3: Download skipped"
fi

# ── Step 2: Transcribe ────────────────────────
if [[ "$SKIP_TRANSCRIBE" == "false" ]]; then
  echo "▶ Step 2/3: Transcribing with Whisper ($WHISPER_MODEL)..."
  echo ""
  python3 "$SCRIPT_DIR/transcribe.py" --model "$WHISPER_MODEL"
  echo ""
else
  echo "▷ Step 2/3: Transcription skipped"
fi

# ── Step 3: Match ─────────────────────────────
echo "▶ Step 3/4: Matching quotes to timestamps..."
echo ""
python3 "$SCRIPT_DIR/match.py"
echo ""

# ── Manual review gate ────────────────────────
if [[ -z "$DRY_RUN" ]]; then
  echo "═══════════════════════════════════════════"
  echo "  REVIEW REQUIRED before clipping"
  echo "═══════════════════════════════════════════"
  echo ""
  echo "  1. Open scripts/matches.json"
  echo "  2. Check each 'matched_text' looks right"
  echo "  3. Adjust 'start'/'end' timestamps if needed"
  echo "  4. Set 'status' to 'approved' for verified clips"
  echo "  5. Run: python scripts/clip.py"
  echo ""
  echo "  Or run: ./scripts/pipeline.sh --skip-download --skip-transcribe"
  echo "  to re-match and re-clip after adding more clips."
else
  echo "▶ Step 4/4: Clipping (dry run)..."
  python3 "$SCRIPT_DIR/clip.py" --dry-run
fi
