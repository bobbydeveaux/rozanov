# High-Level Design
## Rozanov Soundboard — Heated Rivalry Fan App

**Version:** 1.0
**Date:** April 2026

---

## 1. System Overview

The app is intentionally simple: a **fully static web application** with no backend. All content is pre-built and served as static files. Audio clips are served directly from the CDN alongside the JS/CSS bundle.

```
┌─────────────────────────────────────────────────────┐
│                    User's Browser                    │
│                                                      │
│   React/Vite SPA  ←──►  /public/audio/*.mp3         │
│   (HTML/CSS/JS)          (static audio assets)      │
└─────────────────────────────────────────────────────┘
              ▲
              │  HTTPS
              ▼
┌─────────────────────────────────────────────────────┐
│                    StackRamp CDN                     │
│              rozanov.stackramp.io                   │
└─────────────────────────────────────────────────────┘
              ▲
              │  deploy on push to main
              ▼
┌─────────────────────────────────────────────────────┐
│                GitHub Actions CI/CD                  │
│     .github/workflows/deploy.yml                    │
│     → bobbydeveaux/stackramp platform.yml           │
└─────────────────────────────────────────────────────┘
```

---

## 2. Repository Structure

```
rozanov/
├── stackramp.yaml                  ← StackRamp deployment config
├── .gitignore
├── .github/
│   └── workflows/
│       └── deploy.yml              ← CI/CD pipeline
├── docs/
│   ├── PRD.md
│   └── HLD.md
├── clips.txt                       ← one URL per line (YouTube / Instagram)
├── scripts/
│   ├── pipeline.sh                 ← orchestrates all steps
│   ├── download.sh                 ← yt-dlp wrapper (reads clips.txt)
│   ├── transcribe.py               ← Whisper transcription → JSON
│   ├── match.py                    ← fuzzy-matches quotes to timestamps
│   ├── clip.py                     ← ffmpeg clipping of approved matches
│   ├── quotes.json                 ← quote text for matching
│   └── matches.json                ← review file (gitignored after generation)
└── website/                        ← StackRamp frontend root
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── public/
    │   └── audio/                  ← *.mp3 files (gitignored)
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── App.css
        ├── index.css
        ├── soundbites.js           ← content manifest
        └── components/
            └── Player.jsx
```

---

## 3. Frontend Architecture

### 3.1 Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | React 18 | Component model suits player state; familiar |
| Build tool | Vite 6 | Fast dev server, optimised static output |
| Styling | Plain CSS (custom properties) | No dependency overhead; full control |
| Audio | Web Audio API (via `<audio>`) | Native browser support; no library needed |
| State | `useState` / `useCallback` | No global state needed; local is sufficient |
| Routing | None | Single-page app; no routes required |

### 3.2 Component Tree

```
App
├── <header>          — title, show links
├── FilterBar         — category chip buttons
├── Player            — main audio player
│   ├── <audio>       — native audio element (ref-controlled)
│   ├── Quote display
│   ├── Context / episode metadata
│   ├── Progress bar  — clickable seek
│   └── Controls      — prev, play/pause, next, random
├── Grid              — browsable list of all clips
│   └── GridItem[]    — click to select
└── <footer>          — copyright, attribution, CTA
```

### 3.3 Data Flow

```
soundbites.js (static manifest)
       │
       ▼
App (filtered list + currentIndex)
       │
       ├──► Player (receives current bite, calls onNext/onPrev/onRandom)
       │
       └──► Grid (receives filtered list + currentIndex, calls setCurrentIndex)
```

State is minimal and local to `App`:
- `currentIndex` — which clip is selected
- `activeCategory` — active filter (null = all)

No context, no reducers, no external state library.

### 3.4 Audio Playback Model

```
User clicks Play
       │
       ▼
audioRef.current.play()   ← native HTMLAudioElement
       │
       ├── onTimeUpdate → updates progress bar
       ├── onEnded      → resets playing state
       └── onError      → shows "unavailable" fallback
```

When the selected clip changes (`bite.id` changes), a `useEffect` pauses and reloads the audio element, resetting progress to zero.

---

## 4. Content Manifest

`soundbites.js` is the single source of truth for all clip metadata:

```js
{
  id: string,          // filename stem, e.g. "russians-dont-blush"
  quote: string,       // full quote text
  context: string,     // scene description
  episode: string,     // "S01E02 — Olympians"
  category: string,    // "denial" | "rivalry" | "confidence" | "tender" | "blunt" | "comedy"
  audio: string,       // "/audio/{id}.mp3"
}
```

Adding a new clip = add an entry here + drop the `.mp3` in `public/audio/`. No code changes needed.

---

## 5. Audio Extraction Pipeline

This pipeline runs **locally** (not in CI). Output `.mp3` files are committed separately or uploaded manually to the deployment.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   YouTube    │    │   yt-dlp     │    │   Whisper    │    │   ffmpeg     │
│  clip URLs   │───►│  download    │───►│  transcribe  │───►│  clip .mp3   │
│  (manual)    │    │  audio-only  │    │  + timestamps│    │  per quote   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                    │
                                                                    ▼
                                                         website/public/audio/
                                                         {id}.mp3
```

### Steps in detail

**1. Source identification**
- Search YouTube for scene clips, compilation videos, fan edits
- Prefer official or high-quality uploads
- Log source URLs in `scripts/sources.txt` for reproducibility

**2. Download (`scripts/download.sh`)**
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 -o "raw/%(id)s.%(ext)s" <URL>
```

**3. Transcribe (`scripts/transcribe.py`)**
```python
import whisper
model = whisper.load_model("medium")
result = model.transcribe("raw/video.mp3", word_timestamps=True)
# outputs JSON with word-level start/end times
```

**4. Match & Clip (`scripts/clip.sh`)**
```bash
# Given start=14.2 end=17.8 from transcription review:
ffmpeg -i raw/source.mp3 -ss 14.2 -to 17.8 \
       -af "afade=t=in:st=0:d=0.1,afade=t=out:st=3.5:d=0.1" \
       -ar 44100 -b:a 128k \
       website/public/audio/russians-dont-blush.mp3
```
Short fade-in/out prevents hard cuts.

---

## 6. Deployment

### 6.1 StackRamp Config (`stackramp.yaml`)

```yaml
name: rozanov
domain: rozanov.stackramp.io
frontend:
  framework: react
  dir: website
  node_version: "20"
database: false
```

### 6.2 CI/CD (`.github/workflows/deploy.yml`)

Triggers on push to `main` (or PRs) when files under `website/**` change. Delegates entirely to the shared StackRamp platform workflow via `secrets: inherit`.

### 6.3 Build Output

```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js    (~153 kB, ~49 kB gzip)
│   └── index-[hash].css   (~4.5 kB, ~1.4 kB gzip)
└── audio/
    └── *.mp3              (served as static assets)
```

---

## 7. Audio File Considerations

| Concern | Decision |
|---|---|
| Format | MP3 (universal browser support) |
| Bitrate | 128 kbps (sufficient for speech; keeps file sizes small) |
| Sample rate | 44.1 kHz |
| Typical clip length | 3–15 seconds |
| Estimated file size per clip | 50–250 kB |
| Total estimated audio size (16 clips) | ~2 MB |
| Git strategy | **Gitignored** — not stored in repo; deployed separately |

Audio files are not in git because:
- They are derived assets (source is the show, not original work)
- Copyright sensitivity — keeping them out of version history is cleaner
- They can be regenerated from the pipeline at any time

---

## 8. Future: iOS / Android

The React codebase is intentionally kept dependency-light so that the core logic (`soundbites.js`, player state, category filtering) can be ported to **React Native** with minimal rework.

```
Shared
├── soundbites.js        ← identical
└── business logic       ← hooks extracted from App.jsx

Web (current)
└── App.jsx + CSS        ← web-specific rendering

Mobile (future)
└── App.native.jsx       ← RN StyleSheet, Sound library (expo-av)
```

No decisions made yet — flagged as a future option only.

---

## 9. Security & Privacy

- No user data collected
- No cookies, no analytics, no tracking in v1
- No backend = no attack surface
- All external links use `rel="noopener noreferrer"`
- Content Security Policy to be configured at StackRamp layer

---

## 10. Copyright & Legal Position

| Aspect | Position |
|---|---|
| Nature of use | Non-commercial fan project |
| Attribution | Bell Media / Warner Bros. Discovery credited on every page |
| Show promotion | Direct links to Crave and Max on every page |
| Takedown readiness | Contact email prominent; willing to comply immediately |
| Audio in git | No — keeps repo clean and reduces exposure |
| Fair use argument | Educational/fan commentary; no monetisation; promotes the original work |
