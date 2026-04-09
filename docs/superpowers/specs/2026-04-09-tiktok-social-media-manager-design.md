# TikTok Social Media Manager — Design Spec

**Date:** 2026-04-09
**Account:** @eldatocurioso (TikTok)
**Stack:** Python + FFmpeg + gTTS + TikTok API v2 + n8n (self-hosted)
**Constraint:** 100% free/open-source tools only

---

## 1. Overview

An automated TikTok content pipeline that generates curiosity-driven short videos, publishes them continuously, auto-responds to comments, and tracks performance via a visual analytics dashboard. Everything runs locally using the existing n8n + Docker stack.

**Content niche:** Datos curiosos generales (general trivia/curiosities), adjusted over time based on engagement analytics.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    n8n (Scheduler)                       │
│  Cron every 4h → HTTP trigger → Python pipeline         │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP POST to localhost webhook
┌──────────────────▼──────────────────────────────────────┐
│              Python Pipeline (local)                     │
│                                                          │
│  1. script_generator.py  → Claude API → curiosity script│
│  2. tts.py               → gTTS → MP3 audio             │
│  3. video_builder.py     → FFmpeg → 1080x1920 MP4       │
│  4. tiktok_uploader.py   → TikTok Content Posting API v2│
└──────────────────┬──────────────────────────────────────┘
                   │ writes to outputs/state.json
┌──────────────────▼──────────────────────────────────────┐
│              n8n Workflows (parallel, always-on)         │
│                                                          │
│  Workflow A — Comment Responder (every 30 min)           │
│  Workflow B — Analytics Dashboard (every 6h)             │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
tiktok-manager/
├── .env                        # All secrets — never committed
├── pipeline.py                 # Main entry point / orchestrator
├── server.py                   # Local HTTP server (n8n trigger endpoint)
├── modules/
│   ├── script_generator.py     # Claude API → curiosity script
│   ├── tts.py                  # gTTS → MP3
│   ├── video_builder.py        # FFmpeg → 1080x1920 MP4
│   └── tiktok_uploader.py      # TikTok Content Posting API v2
├── assets/
│   ├── backgrounds/            # Free stock images/video loops (Pixabay)
│   ├── fonts/                  # Open-source fonts (e.g. Montserrat)
│   └── music/                  # Optional: royalty-free background music
├── outputs/
│   ├── videos/                 # Generated MP4 files
│   ├── state.json              # Pipeline state (dedup, daily count, tokens)
│   └── dashboard.html          # Analytics dashboard (regenerated every 6h)
└── n8n-workflows/
    ├── scheduler.json          # Workflow 1: Cron trigger
    ├── comment-responder.json  # Workflow 2: Auto-reply comments
    └── analytics.json          # Workflow 3: Dashboard generator
```

---

## 4. Python Pipeline — Module Details

### 4.1 `script_generator.py`

Calls Claude API (`claude-haiku-4-5-20251001` for cost efficiency) with a prompt that produces:
- **Hook** (first 3 seconds): surprising opener, e.g. "¿Sabías que los pulpos tienen 3 corazones?"
- **Body** (3-4 curiosity facts, 60–80 words total)
- **CTA** (last 3 seconds): e.g. "Síguenos para más datos ocultos 🔍"
- **Caption** (TikTok post text, max 2200 chars, includes hashtags)
- **Hashtags**: generated dynamically based on topic + trending curiosity tags

Claude is also instructed to avoid repeating topics by receiving the last 10 titles from `state.json`.

### 4.2 `tts.py`

Uses `gTTS` (Google Text-to-Speech, free, no API key needed) to convert the script body to MP3. Voice: Spanish (`es`), slow=False. Output: `outputs/audio_<timestamp>.mp3`.

### 4.3 `video_builder.py`

Uses FFmpeg to compose the final 9:16 video (1080×1920):

1. Select random background from `assets/backgrounds/`
2. Overlay animated text (word-by-word, timed to audio duration)
3. Mix audio (TTS + optional background music at 20% volume)
4. Add branding: channel name watermark bottom-right
5. Duration: matches TTS audio length (typically 45–90 seconds)
6. Output: `outputs/videos/video_<timestamp>.mp4`

### 4.4 `tiktok_uploader.py`

Uses TikTok Content Posting API v2 (direct post flow):
1. Initialize upload with video metadata
2. Upload video chunks
3. Post with caption + hashtags
4. Write `video_id` to `state.json`

Handles token refresh automatically using the stored refresh token.

---

## 5. n8n Workflows

### Workflow 1 — Scheduler
- **Trigger:** Cron, every 4 hours
- **Action:** HTTP POST to `localhost:8765/run-pipeline`
- **On failure:** Log to `outputs/errors.log`, retry once after 10 minutes

### Workflow 2 — Comment Auto-Responder
- **Trigger:** Cron, every 30 minutes
- **Steps:**
  1. GET `/v2/video/comment/list` for all published videos
  2. Filter comments not yet in `state.json → comments_replied[]`
  3. For each new comment: call Claude API with comment text + video topic → generate reply (max 150 chars, friendly/curious tone)
  4. POST `/v2/video/comment/reply`
  5. Append comment ID to `state.json`
- **Spam filter:** Skip comments containing URLs or flagged keywords

### Workflow 3 — Analytics Dashboard
- **Trigger:** Cron, every 6 hours
- **Steps:**
  1. GET `/v2/video/list` + `/v2/video/query` for stats per video
  2. Compute quality score per video (0–100):
     - Completion rate (retention): 40%
     - Engagement ratio (likes+comments+shares / views): 30%
     - Follower growth attributed: 20%
     - View velocity (first 2h): 10%
  3. Render `outputs/dashboard.html` using Chart.js (CDN, no build step)
  4. Dashboard sections: total stats, per-video quality scores, top performer, trend over time

---

## 6. State File Schema

`outputs/state.json`:
```json
{
  "last_video_id": "7xxx",
  "videos_published": ["7xxx", "7yyy"],
  "last_10_topics": ["pulpos", "cerebro humano", "..."],
  "comments_replied": ["comment_id_1", "comment_id_2"],
  "daily_count": 3,
  "last_upload_ts": "2026-04-09T14:00:00Z",
  "tiktok_access_token": "...",
  "tiktok_refresh_token": "...",
  "token_expires_at": "2026-04-09T20:00:00Z"
}
```

---

## 7. Environment Variables (`.env`)

```
ANTHROPIC_API_KEY=sk-ant-...
TIKTOK_CLIENT_ID=aw38x3be74y38fj6
TIKTOK_CLIENT_SECRET=<rotated — do not use original>
TIKTOK_REDIRECT_URI=http://localhost:8765/callback
PIPELINE_WEBHOOK_PORT=8765
```

> **Security note:** The original Client Secret shared in conversation must be rotated at developers.tiktok.com before use. Never commit `.env` to git.

---

## 8. Error Handling

| Layer | Error | Action |
|---|---|---|
| Claude API | Rate limit / timeout | Retry 2x with exponential backoff |
| gTTS | Network unavailable | Use cached audio from previous run |
| FFmpeg | Render error | Log + skip, attempt next cycle |
| TikTok API | Token expired | Auto-refresh using refresh token |
| TikTok API | Daily quota exceeded | Pause uploads until midnight UTC |
| n8n workflow | Any failure | Write to `outputs/errors.log` |

---

## 9. First Video — Day 1 Checklist

1. Rotate TikTok Client Secret at developers.tiktok.com
2. Complete TikTok OAuth flow (one-time manual step, stores tokens in `state.json`)
3. Run `pip install anthropic gtts ffmpeg-python requests flask`
4. Add 3–5 background images to `assets/backgrounds/`
5. Run `python pipeline.py` manually → verify first video renders and uploads
6. Import n8n workflows from `n8n-workflows/`
7. Activate all 3 workflows in n8n
8. Open `outputs/dashboard.html` in browser to verify analytics

---

## 10. Out of Scope

- Instagram (can be added later as a second publisher module)
- Paid video AI tools (Runway, Pika, HeyGen)
- Multi-language support (Spanish only for now)
- A/B testing of scripts (post-MVP)
