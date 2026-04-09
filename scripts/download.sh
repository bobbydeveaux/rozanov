#!/usr/bin/env bash
# download.sh — fetch audio from every URL in clips.txt
# Usage: ./scripts/download.sh [clips.txt]
#
# Requires: yt-dlp  (pip install yt-dlp)
# Output:   scripts/raw/<video-id>.mp3

set -euo pipefail

CLIPS_FILE="${1:-clips.txt}"
RAW_DIR="$(dirname "$0")/raw"
LOG_FILE="$(dirname "$0")/download.log"

# Prefer system yt-dlp, fall back to python3 -m yt_dlp
if command -v yt-dlp &>/dev/null; then
  YTDLP="yt-dlp"
elif python3 -m yt_dlp --version &>/dev/null 2>&1; then
  YTDLP="python3 -m yt_dlp"
else
  echo "ERROR: yt-dlp not found. Run: pip install yt-dlp"
  exit 1
fi

if [[ ! -f "$CLIPS_FILE" ]]; then
  echo "ERROR: $CLIPS_FILE not found"
  echo "Create it with one URL per line. Lines starting with # are ignored."
  exit 1
fi

mkdir -p "$RAW_DIR"
echo "" > "$LOG_FILE"

total=0
downloaded=0
skipped=0
failed=0

while IFS= read -r line || [[ -n "$line" ]]; do
  # skip blank lines and comments
  [[ -z "$line" || "$line" == \#* ]] && continue
  total=$((total + 1))

  url="${line%%  *}"   # strip any trailing comment
  url="${url%% *}"     # strip trailing spaces

  echo "──────────────────────────────────────"
  echo "[$total] $url"

  $YTDLP \
    --extract-audio \
    --audio-format mp3 \
    --audio-quality 0 \
    --output "$RAW_DIR/%(id)s.%(ext)s" \
    --no-playlist \
    --write-info-json \
    --quiet \
    --progress \
    "$url" 2>>"$LOG_FILE" && {
      downloaded=$((downloaded + 1))
      echo "     ✓ downloaded"
    } || {
      failed=$((failed + 1))
      echo "     ✗ failed (see download.log)"
    }

done < "$CLIPS_FILE"

echo ""
echo "══════════════════════════════════════"
echo "Done: $downloaded downloaded, $skipped skipped, $failed failed"
echo "Files in: $RAW_DIR"
