# Product Requirements Document
## Rozanov Soundboard — Heated Rivalry Fan App

**Version:** 1.0
**Date:** April 2026
**Status:** In Development

---

## 1. Overview

A fan-made web app that plays soundbites from **Ilya Rozanov**, the breakout character from the Canadian/HBO Max series *Heated Rivalry* (Crave, 2025). The app is a love letter to the character and the show — non-commercial, attribution-forward, and built by a fan for fans.

---

## 2. Problem Statement

*Heated Rivalry* became a viral phenomenon in late 2025, with Ilya Rozanov's quotes and clips circulating widely across TikTok, X, Instagram and Tumblr. Fans want to revisit and share these moments, but currently have to hunt across platforms to find specific lines. There is no single, dedicated, high-quality destination for the character's iconic soundbites.

---

## 3. Goals

| Goal | Description |
|---|---|
| **Delight fans** | Give fans instant access to the quotes that made them fall in love with the character |
| **Promote the show** | Every page view links directly to Crave and Max — drive subscriptions |
| **Non-commercial** | No ads, no monetisation, no paywalls. Pure fan project |
| **Copyright-respectful** | Clear attribution, takedown contact, and prominent "watch the show" CTAs |
| **Extensible** | Architecture supports future iOS/Android app if appetite exists |

---

## 4. Non-Goals

- No user accounts or social features in v1
- No video — audio clips only
- Not a general *Heated Rivalry* fan site (character-focused)
- No monetisation of any kind
- Not affiliated with, endorsed by, or connected to Bell Media, Crave, or HBO Max

---

## 5. Target Audience

- Existing *Heated Rivalry* fans who want to replay iconic Ilya moments
- Social media users who've seen clips and want to explore more
- People who haven't seen the show yet — secondary, discovery audience

---

## 6. Core Features

### 6.1 Soundbite Player
- Play individual audio clips of Ilya Rozanov quotes
- Display the quote text, episode, and contextual note while audio plays
- Progress bar with seek support
- Prev / Next navigation
- **Random** button — the primary hero interaction

### 6.2 Category Filtering
Clips are tagged by tone:
- **Denial** — Ilya refusing to admit his feelings
- **Rivalry** — Hockey trash talk and competitive lines
- **Confidence** — Ilya's legendary self-assurance
- **Tender** — Vulnerable, romantic moments
- **Blunt** — Characteristically direct observations
- **Comedy** — The purely funny moments (e.g., the loon incident)

### 6.3 Quote Grid
- Browse all clips at a glance
- Click any to jump directly to it in the player

### 6.4 Attribution & Copyright
- Persistent footer on every page with:
  - Clear "unofficial fan project" statement
  - Copyright ownership acknowledged (Bell Media / Warner Bros. Discovery)
  - Takedown contact email
  - Direct links to watch the show on Crave and Max

---

## 7. Content Scope — v1 Soundbites

16 clips targeted for v1, spanning all 6 episodes of Season 1:

| ID | Quote (truncated) | Episode | Category |
|---|---|---|---|
| russians-dont-blush | "Never in life have I blushed…" | S01E02 | Denial |
| see-you-in-final | "You will not be so nice when we beat you…" | S01E01 | Rivalry |
| bronze-medal | "Dreaming of what? Bronze medal?" | S01E01 | Rivalry |
| fifty-goals | "I never said 40 goals. Liar told you that. I said 50." | S01E03 | Confidence |
| cover-of-the-game | "I'm on the cover of the fucking game." | S01E03 | Confidence |
| only-one-person | "I have only been in love with one person." | S01E04 | Tender |
| problem-never-go-away | "I do not want the problem to ever go away." | S01E04 | Tender |
| ruined-you | "I have ruined you. No one else will do." | S01E04 | Tender |
| panic-attack | "Hollander, you are having a panic attack…" | S01E02 | Blunt |
| mr-hollander-perfect | "How does it feel to be perfect? Fucking perfect." | S01E04 | Tender |
| stupid-canadian-wolf-bird | "Fuck you and your loon. Stupid Canadian wolf bird." | S01E06 | Comedy |
| sounds-like-wolf | "What the fuck bird makes a noise like that?" | S01E06 | Comedy |
| im-coming-to-the-cottage | "I'm coming to the cottage." | S01E06 | Tender |
| love-confession-russian | "It's always you. I'm so in love with you…" | S01E05 | Tender |
| freckles | "Your freckles are stunning." | S01E02 | Tender |
| short-hockey-player | "I cannot stop thinking about this short fucking hockey player…" | S01E01 | Denial |

More clips can be added as the show's season 2 releases (April 2027).

---

## 8. Audio Sourcing Pipeline

Audio files are **not stored in the repository**. They are extracted via an offline pipeline:

1. **Search** — identify YouTube uploads of scene clips and fan compilations using known quote text
2. **Download** — `yt-dlp` to fetch video/audio
3. **Transcribe** — OpenAI Whisper (local model) produces word-level timestamps
4. **Match** — align known quote text to transcription timestamps
5. **Clip** — `ffmpeg` extracts the precise segment as `.mp3`
6. **Deploy** — clips placed in `website/public/audio/` and served as static assets

Audio files are gitignored. The pipeline scripts live in `/scripts/`.

---

## 9. Deployment

- Hosted on **StackRamp** (`rozanov.stackramp.io`)
- CI/CD via GitHub Actions (`.github/workflows/deploy.yml`) — deploys on push to `main` when `website/**` changes
- Static site — no backend, no database
- Audio files served as static assets from `public/audio/`

---

## 10. Future Considerations

| Feature | Priority | Notes |
|---|---|---|
| iOS/Android app | Medium | React Native reuse of existing components |
| Share a clip | Low | Native Web Share API — no backend needed |
| Season 2 clips | High | New content when S02 drops (April 2027) |
| Keyboard shortcuts | Low | Space to play, arrows to navigate |
| Favourites | Low | localStorage, no account needed |
| Russian language toggle | Medium | Show original Russian transcript for the monologue |

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Copyright takedown | Attribution-first design; takedown contact prominent; willing to comply immediately |
| YouTube clips being removed | Pipeline re-runnable from any source; not dependent on specific URLs |
| Whisper transcription errors | Manual review of all clip boundaries before publishing |
| Audio quality variance | Prefer scene uploads over fan edits; normalise audio with ffmpeg |
