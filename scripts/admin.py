#!/usr/bin/env python3
"""
admin.py — local clip editor / preview server

Usage:
    python scripts/admin.py

Opens a browser at http://localhost:7474
Lets you preview any clip with 5s context either side,
then adjust start/end and re-clip precisely.
"""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
MATCHES_FILE = SCRIPT_DIR / "matches.json"
AUDIO_OUT = REPO_ROOT / "website" / "public" / "audio"
PORT = 7474
CONTEXT_SECS = 5  # seconds of context either side


def load_matches():
    return json.loads(MATCHES_FILE.read_text())


def save_matches(matches):
    MATCHES_FILE.write_text(json.dumps(matches, indent=2, ensure_ascii=False))


def get_source_duration(source_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(source_path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def make_preview(source_path: Path, start: float, end: float) -> bytes:
    """Extract audio from (start - CONTEXT) to (end + CONTEXT), return mp3 bytes."""
    duration = get_source_duration(source_path)
    preview_start = max(0.0, start - CONTEXT_SECS)
    preview_end = min(duration, end + CONTEXT_SECS)
    preview_dur = preview_end - preview_start

    # Markers: where the actual clip starts/ends within the preview
    clip_start_in_preview = start - preview_start
    clip_end_in_preview = end - preview_start

    # Use afade to gently dim the context region vs the clip region
    # silencedetect won't work here — instead use volume filter with timeline
    af = (
        f"volume=0.35:enable='lt(t,{clip_start_in_preview:.3f})',"
        f"volume=0.35:enable='gt(t,{clip_end_in_preview:.3f})'"
    )

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(preview_start),
        "-i", str(source_path),
        "-t", str(preview_dur),
        "-af", af,
        "-ar", "44100",
        "-b:a", "128k",
        "-map_metadata", "-1",
        tmp_path,
    ], capture_output=True)

    data = Path(tmp_path).read_bytes()
    os.unlink(tmp_path)
    return data


def do_clip(match: dict) -> bool:
    source_path = SCRIPT_DIR / match["source_file"]
    out = AUDIO_OUT / f"{match['id']}.mp3"
    start = float(match["start"])
    end = float(match["end"])
    duration = round(end - start, 3)
    fade = min(0.1, duration * 0.05)

    result = subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(source_path),
        "-t", str(duration),
        "-af", f"afade=t=in:st=0:d={fade},afade=t=out:st={duration-fade}:d={fade}",
        "-ar", "44100", "-b:a", "128k", "-map_metadata", "-1",
        str(out),
    ], capture_output=True)
    return result.returncode == 0


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rozanov Clip Admin</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0a0a0f; --surface: #13131a; --surface2: #1e1e2a;
    --border: #2a2a3a; --text: #f0f0f5; --muted: #8888aa;
    --green: #2a9d8f; --red: #e63946; --gold: #f4a261;
  }
  body { background: var(--bg); color: var(--text); font-family: system-ui, sans-serif;
         font-size: 14px; padding: 24px; }
  h1 { font-size: 1.3rem; margin-bottom: 4px; }
  .subtitle { color: var(--muted); font-size: 0.8rem; margin-bottom: 28px; }
  .clip-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 20px; margin-bottom: 16px;
  }
  .clip-card.approved { border-left: 3px solid var(--green); }
  .clip-card.not_found { border-left: 3px solid var(--red); opacity: 0.5; }
  .clip-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
  .clip-id { font-weight: 700; font-size: 0.95rem; }
  .clip-quote { color: var(--muted); font-style: italic; font-size: 0.82rem; flex: 1; }
  .clip-status { font-size: 0.7rem; text-transform: uppercase; letter-spacing: .08em;
                 padding: 2px 8px; border-radius: 4px; background: var(--surface2); }
  .controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  label { color: var(--muted); font-size: 0.78rem; }
  input[type=number] {
    background: var(--surface2); border: 1px solid var(--border); color: var(--text);
    padding: 5px 8px; border-radius: 6px; width: 80px; font-size: 0.85rem;
  }
  .nudge-group { display: flex; gap: 2px; }
  button {
    padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border);
    background: var(--surface2); color: var(--text); cursor: pointer;
    font-size: 0.8rem; transition: all .15s;
  }
  button:hover { border-color: var(--muted); }
  .btn-preview { border-color: var(--gold); color: var(--gold); }
  .btn-preview:hover { background: #f4a26122; }
  .btn-clip { border-color: var(--green); color: var(--green); }
  .btn-clip:hover { background: #2a9d8f22; }
  .btn-nudge { padding: 4px 8px; font-size: 0.75rem; }
  audio { width: 100%; margin-top: 10px; accent-color: var(--gold); }
  .audio-wrap { display: none; }
  .audio-wrap.visible { display: block; }
  .msg { font-size: 0.78rem; padding: 4px 10px; border-radius: 4px; margin-left: 8px; }
  .msg.ok { background: #2a9d8f33; color: var(--green); }
  .msg.err { background: #e6394633; color: var(--red); }
  .source { font-size: 0.72rem; color: var(--muted); margin-top: 8px; }
  .not-found-label { color: var(--muted); font-size: 0.82rem; font-style: italic; }
</style>
</head>
<body>
<h1>🎛 Rozanov Clip Admin</h1>
<p class="subtitle">Preview clips with {ctx}s context either side. Adjust timestamps, then re-clip.</p>

<div id="clips"></div>

<script>
const matches = MATCHES_JSON;

function render() {
  const el = document.getElementById('clips');
  el.innerHTML = '';
  matches.forEach((m, idx) => {
    const card = document.createElement('div');
    card.className = 'clip-card ' + m.status;
    card.id = 'card-' + m.id;

    if (m.status === 'not_found') {
      card.innerHTML = `
        <div class="clip-header">
          <span class="clip-id">${m.id}</span>
          <span class="clip-quote">"${m.quote}"</span>
          <span class="clip-status" style="color:var(--red)">not found</span>
        </div>
        <p class="not-found-label">No source clip — add more URLs to clips.txt</p>`;
      el.appendChild(card);
      return;
    }

    card.innerHTML = `
      <div class="clip-header">
        <span class="clip-id">${m.id}</span>
        <span class="clip-quote">"${m.quote}"</span>
        <span class="clip-status">${m.status}</span>
        <span id="msg-${m.id}" class="msg" style="display:none"></span>
      </div>
      <div class="controls">
        <label>Start (s)</label>
        <div class="nudge-group">
          <button class="btn-nudge" onclick="nudge('${m.id}','start',-0.5)">−0.5</button>
          <button class="btn-nudge" onclick="nudge('${m.id}','start',-0.1)">−0.1</button>
        </div>
        <input type="number" id="start-${m.id}" value="${m.start}" step="0.1"
               onchange="updateVal('${m.id}','start',this.value)">
        <div class="nudge-group">
          <button class="btn-nudge" onclick="nudge('${m.id}','start',0.1)">+0.1</button>
          <button class="btn-nudge" onclick="nudge('${m.id}','start',0.5)">+0.5</button>
        </div>

        <label style="margin-left:12px">End (s)</label>
        <div class="nudge-group">
          <button class="btn-nudge" onclick="nudge('${m.id}','end',-0.5)">−0.5</button>
          <button class="btn-nudge" onclick="nudge('${m.id}','end',-0.1)">−0.1</button>
        </div>
        <input type="number" id="end-${m.id}" value="${m.end}" step="0.1"
               onchange="updateVal('${m.id}','end',this.value)">
        <div class="nudge-group">
          <button class="btn-nudge" onclick="nudge('${m.id}','end',0.1)">+0.1</button>
          <button class="btn-nudge" onclick="nudge('${m.id}','end',0.5)">+0.5</button>
        </div>

        <button class="btn-preview" onclick="preview('${m.id}')">▶ Preview (±${ctx}s)</button>
        <button class="btn-clip" onclick="clip('${m.id}')">✂ Re-clip</button>
      </div>
      <div class="audio-wrap" id="audio-wrap-${m.id}">
        <audio id="audio-${m.id}" controls></audio>
      </div>
      <p class="source">${m.source_file} &nbsp;·&nbsp; current: ${m.start}s → ${m.end}s</p>`;

    el.appendChild(card);
  });
}

function getMatch(id) { return matches.find(m => m.id === id); }

function nudge(id, field, delta) {
  const m = getMatch(id);
  const input = document.getElementById(field + '-' + id);
  const val = Math.round((parseFloat(input.value) + delta) * 1000) / 1000;
  input.value = val;
  m[field] = val;
  updateSource(id);
}

function updateVal(id, field, val) {
  const m = getMatch(id);
  m[field] = Math.round(parseFloat(val) * 1000) / 1000;
  updateSource(id);
}

function updateSource(id) {
  const m = getMatch(id);
  const src = document.querySelector(`#card-${id} .source`);
  if (src) src.textContent = m.source_file + ' · current: ' + m.start + 's → ' + m.end + 's';
}

function showMsg(id, text, type) {
  const el = document.getElementById('msg-' + id);
  el.textContent = text; el.className = 'msg ' + type; el.style.display = 'inline';
  setTimeout(() => { el.style.display = 'none'; }, 3000);
}

function preview(id) {
  const m = getMatch(id);
  const wrap = document.getElementById('audio-wrap-' + id);
  const audio = document.getElementById('audio-' + id);
  wrap.classList.add('visible');
  audio.src = '/preview/' + id + '?start=' + m.start + '&end=' + m.end + '&t=' + Date.now();
  audio.load();
  audio.play();
}

async function clip(id) {
  const m = getMatch(id);
  showMsg(id, 'Clipping…', 'ok');
  const res = await fetch('/clip/' + id, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start: m.start, end: m.end })
  });
  const data = await res.json();
  showMsg(id, data.ok ? '✓ Clipped!' : '✗ ' + data.error, data.ok ? 'ok' : 'err');
}

render();
</script>
</body>
</html>
""".replace("{ctx}", str(CONTEXT_SECS))


class AdminHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence access log

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/":
            matches = load_matches()
            html = HTML.replace("MATCHES_JSON", json.dumps(matches, ensure_ascii=False))
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif path.startswith("/preview/"):
            clip_id = path[len("/preview/"):]
            try:
                start = float(qs.get("start", [0])[0])
                end = float(qs.get("end", [5])[0])
                matches = load_matches()
                m = next((x for x in matches if x["id"] == clip_id), None)
                if not m or not m.get("source_file"):
                    self.send_response(404); self.end_headers(); return
                source = SCRIPT_DIR / m["source_file"]
                audio = make_preview(source, start, end)
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", len(audio))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(audio)
            except Exception as e:
                self.send_response(500); self.end_headers()

        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        if path.startswith("/clip/"):
            clip_id = path[len("/clip/"):]
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            start = float(body["start"])
            end = float(body["end"])

            matches = load_matches()
            m = next((x for x in matches if x["id"] == clip_id), None)
            if not m:
                self.send_json({"ok": False, "error": "not found"}, 404); return

            m["start"] = start
            m["end"] = end
            save_matches(matches)

            ok = do_clip(m)
            self.send_json({"ok": ok, "error": "" if ok else "ffmpeg failed"})

        else:
            self.send_response(404); self.end_headers()


def main():
    server = HTTPServer(("localhost", PORT), AdminHandler)
    url = f"http://localhost:{PORT}"
    print(f"Rozanov Admin → {url}")
    print("Ctrl+C to stop\n")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
