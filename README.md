# PromptArt — AI Generation & Editing Telegram Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Powered by Pollinations.ai](https://img.shields.io/badge/Powered%20by-Pollinations.ai-ff69b4.svg)](https://pollinations.ai)

> Telegram bot for AI image, video, audio (TTS) generation, persistent text chat, and in-context image editing via
> [Pollinations.ai](https://pollinations.ai). Redesigned settings menus, history, and balance.

<p align="center">
  <img src="assets/logo.png" alt="PromptArt logo" width="180" />
</p>

> **Every user brings their own Pollinations key.** The bot has no shared key: each
> person sends `/token <key>` once, it is stored per user, and their generations bill
> their own balance. Whoever runs the bot pays nothing for other people's images — see
> [Pollinations keys](#pollinations-keys).

## Features

### Modalities

#### 🎨 Image Generation & Editing (In-context, 1–4 photos)
- **21+ live image models** fetched from `gen.pollinations.ai/models` (flux, zimage, klein, etc.).
- **5 aspect ratios** at SDXL resolutions (1024², 1344×768, 768×1344, 1152×896, 896×1152).
- **7 style presets** — photorealistic, anime, digital painting, oil, 3D, cyberpunk, sketch.
- **In-context editing**: Send a photo directly or tap «✏️ Edit» and drop 1–4 photos + a description (e.g., "replace background with neon city").
- **Edit model** setting (default `klein` @ 0.01p, pickers filtered to image-input models).
- **Again / Enhance** under every generated/edited image.

#### 🎥 Video Generation
- **10+ live video models** (e.g. `ltx-2`, `wan-fast`, `veo`, `nova-reel`).
- **Custom aspect ratios** (`16:9`, `9:16`, `1:1`).
- **Duration picker** (5s or 10s, depending on model limits).
- Fast and reliable video downloads using Pollinations `GET /video/{prompt}` API with 300s connection timeouts.

#### 🔊 Audio (TTS) Generation
- **10+ live audio models** (e.g. `openai-audio`, `elevenlabs`, `acestep`).
- **Custom voice picker** supporting alloy, echo, fable, onyx, nova, and shimmer.
- Generates and uploads voice/audio MP3s via OpenAI-compatible `POST /v1/audio/speech` endpoint.

#### 💬 Persistent AI Text Chat
- **52+ live text models** (e.g. `openai`, `mistral`, `deepseek`, `scribe`).
- Interactive chat mode: stay in conversational state until clicking any navigation button.
- **Long responses safeguard**: Answers exceeding 4,000 characters are automatically formatted and sent as attached `.md` documents, preventing Telegram truncation errors.

### Settings Submenus
- Redesigned **`/settings`** menu with dedicated submenus:
  - **Image Settings** (Models, Aspect Ratio, Style Presets)
  - **Video Settings** (Video Models, Aspect Ratio, Duration)
  - **Audio Settings** (TTS Models, Voice Profiles)
  - **Chat Settings** (Text Models)
- **Live pricing** displayed inline, in the unit the model is actually billed in: per image,
  `/s` for video and speech, `/1K` for token-priced text and audio. Models billed per token
  show an estimate for one item, prefixed `~`, that includes the input cost (prompt, plus a
  reference image for editing models).
- Models that need a topped-up balance are marked `💰` and sorted last, but remain
  selectable — you pay with your own key, so the choice is yours.
- Long model lists are paged (30 per page) to stay within Telegram's keyboard limits.
- Interactive checkmark (`✅`) state indicators update immediately on click.

### Limit Increase
- Maximum prompt length limits across all modalities expanded from `500` to **`4000`** characters (matching Telegram limits).

### History & Balance
- **/history** and **/favorites** preview media with regeneration/favorite inline options.
- **/balance** shows total pollen balance + detailed breakdown (Tier remaining vs Paid credits).

### Localization
- English and Russian, picked automatically from the Telegram client language and stored per user.
- The Telegram command menu is published in both languages on startup.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/zFannur/promptart-bot.git
cd promptart-bot
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# only BOT_TOKEN and ADMIN_ID are required; leave POLLINATIONS_API_KEY empty
# (see "Getting tokens" below)

# 3. Run
python bot.py
```

## Commands

| Command | What it does |
|---|---|
| `/start` | Main menu. Without a key, explains how to get one. |
| `/token` | Show, set, or remove **your** Pollinations key. Required before anything generates. |
| `/balance` | Pollen balance and prices. |
| `/edit` | Combine / edit 1–4 of your photos. |
| `/prompts` | Prompt builder, templates, and library. |
| `/settings` | Model, aspect ratio, style, and voice pickers. |
| `/history` | Recent generations. |
| `/favorites` | Saved favorites. |
| `/help` | Command reference. |

The list is published to Telegram on startup (`setup_commands` in `bot.py`), so it also
appears under the client's **Menu** button and in `/` autocomplete.

## Getting Tokens

**Telegram bot token:**
1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Send `/newbot`, follow the prompts.
3. Copy the token like `123456789:ABCDef...` into `BOT_TOKEN`.

### Pollinations keys

Keys are **per user, not per deployment**. Leave `POLLINATIONS_API_KEY` **empty** in
`.env`: filling it makes every user of the bot generate on *your* balance, which is
exactly what this design avoids.

Each user, including the operator, does this once in the chat:

1. Go to [enter.pollinations.ai](https://enter.pollinations.ai) and sign in via GitHub.
2. Create a key with `profile` + `usage` permissions (`usage` is what makes the
   `/balance` breakdown work).
3. Send it to the bot: `/token sk_...`

The bot deletes the message containing the key as soon as it is stored, and keeps it in
`users.pollinations_token`. `/token` alone shows the current key masked, `/token delete`
removes it. Until a key is set, every generation replies with instructions instead.

---

## Project Structure

```
promptart_bot/
├── bot.py                  # entry point, router wiring, command menu, ephemeral-DB warning
├── config.py               # pydantic-settings
├── Dockerfile              # python:3.11-slim, declares VOLUME /data
├── Procfile                # worker: python bot.py (buildpack platforms)
├── handlers/
│   ├── start.py            # /start, /help, main reply menu
│   ├── token.py            # /token — set / show / delete the user's own key
│   ├── generation.py       # «Create Image» flow, Again/Enhance callbacks
│   ├── edit.py             # «Edit Image» flow, photo collection, auto-detect
│   ├── video.py            # «Create Video» flow and prompt collector
│   ├── audio.py            # «Create Audio» flow (TTS) and voice sender
│   ├── chat.py             # «Chat (Text)» interactive persistent chat router
│   ├── prompts.py          # /prompts — builder, templates, saved prompts
│   ├── settings.py         # model / ratio / style / voice pickers (with submenus)
│   ├── history.py          # /history and /favorites with media previews
│   ├── balance.py          # /balance command and menu button
│   └── errors.py           # global error handler (turns TokenRequired into instructions)
├── services/
│   ├── pollinations.py     # async httpx client for /v1/* and /video/* endpoints
│   └── database.py         # aiosqlite + idempotent column migrations
├── keyboards/              # main (incl. the "get a key" button), generation, edit, settings
├── middlewares/            # i18n, rate limit, token (binds the caller's key to the update)
├── states/                 # FSM states (GenStates, EditStates)
├── utils/                  # constants, helpers (models, aspect_ratios, styles, prompts, menu)
├── locales/                # en.json, ru.json — UI strings
├── data/                   # sqlite db (gitignored; use a mounted volume in production)
└── assets/                 # screenshots, logo
```

---

## Deployment

> ⚠️ **DATA LOSS WARNING.** Container filesystems are wiped on every redeploy. The
> database holds every user's Pollinations key, so without a persistent volume everyone
> has to re-send `/token` after each deploy. `bot.py` logs a loud warning at startup if
> `DB_PATH` looks ephemeral.

**Docker** (the `Dockerfile` sets `DB_PATH=/data/bot.db` and declares `VOLUME /data`):

```bash
docker build -t promptart-bot .
docker run -d --name promptart-bot \
  -e BOT_TOKEN=123456789:ABCDef... \
  -e ADMIN_ID=your_telegram_id \
  -v promptart-data:/data \
  promptart-bot
```

The bot uses **long polling** and listens on no port, so it needs no domain, no reverse
proxy, and no health check endpoint. Run exactly **one** instance per bot token —
a second one makes Telegram return `409 Conflict` and both start dropping updates.

On PaaS platforms (Railway, Render, Fly): attach a volume mounted at `/data` and set
`DB_PATH=/data/bot.db`.

---

## Pollinations API Endpoints Used

All requests go to `https://gen.pollinations.ai` with `Authorization: Bearer sk_...`, where
the key is the one the calling user set via `/token`.

| Purpose | Endpoint | Method |
|---|---|---|
| List models with pricing | `/models` | GET |
| Get pollen balance | `/account/balance` | GET |
| Get account profile (tier) | `/account/profile` | GET |
| Get usage history | `/account/usage` | GET |
| Text-to-image generation | `/v1/images/generations` | POST (JSON) |
| In-context image editing | `/v1/images/edits` | POST (multipart) |
| Text-to-video generation | `/video/{prompt}` | GET (binary) |
| Text-to-speech (audio) | `/v1/audio/speech` | POST (JSON) |
| Text generation / Chat | `/v1/chat/completions` | POST (JSON) |

## Tech Stack

- **aiogram 3.13** — async Telegram framework
- **httpx** — async HTTP client with timeout/retry overrides
- **aiosqlite** — async SQLite database
- **pydantic-settings** — env configuration
- **loguru** — logging

## License

MIT — see [LICENSE](LICENSE).
