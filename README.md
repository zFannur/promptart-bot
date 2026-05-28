# PromptArt — AI Generation & Editing Telegram Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Powered by Pollinations.ai](https://img.shields.io/badge/Powered%20by-Pollinations.ai-ff69b4.svg)](https://pollinations.ai)

> Telegram bot for AI image, video, audio (TTS) generation, persistent text chat, and in-context image editing via
> [Pollinations.ai](https://pollinations.ai). Redesigned settings menus, history, and balance.

<p align="center">
  <img src="assets/logo.png" alt="PromptArt logo" width="180" />
</p>

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
- **Live pricing** displayed inline with a `[paid]` tag for paid-only models.
- Interactive checkmark (`✅`) state indicators update immediately on click.

### Limit Increase
- Maximum prompt length limits across all modalities expanded from `500` to **`4000`** characters (matching Telegram limits).

### History & Balance
- **/history** and **/favorites** preview media with regeneration/favorite inline options.
- **/balance** shows total pollen balance + detailed breakdown (Tier remaining vs Paid credits).

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
# edit .env with your tokens (see "Getting tokens" below)

# 3. Run
python bot.py
```

## Getting Tokens

**Telegram bot token:**
1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Send `/newbot`, follow the prompts.
3. Copy the token like `123456789:ABCDef...` into `BOT_TOKEN`.

**Pollinations API key:**
1. Go to [enter.pollinations.ai](https://enter.pollinations.ai) and sign in via GitHub.
2. Create a new key with `profile` + `usage` permissions for `/balance` breakdown.
3. Copy the `sk_...` key into `POLLINATIONS_API_KEY`.

---

## Project Structure

```
promptart_bot/
├── bot.py                  # entry point, router wiring, ephemeral-DB warning
├── config.py               # pydantic-settings
├── handlers/
│   ├── start.py            # /start, /help, main reply menu
│   ├── generation.py       # «Create Image» flow, Again/Enhance callbacks
│   ├── edit.py             # «Edit Image» flow, photo collection, auto-detect
│   ├── video.py            # «Create Video» flow and prompt collector
│   ├── audio.py            # «Create Audio» flow (TTS) and voice sender
│   ├── chat.py             # «Chat (Text)» interactive persistent chat router
│   ├── settings.py         # model / ratio / style / voice pickers (with submenus)
│   ├── history.py          # /history and /favorites with media previews
│   ├── balance.py          # /balance command and menu button
│   └── errors.py           # global error handler
├── services/
│   ├── pollinations.py     # async httpx client for /v1/* and /video/* endpoints
│   └── database.py         # aiosqlite + idempotent column migrations
├── keyboards/              # main, generation, edit, settings keyboards
├── middlewares/            # i18n, rate limit
├── states/                 # FSM states (GenStates, EditStates)
├── utils/                  # constants, helpers (models, aspect_ratios, styles, menu)
├── locales/en.json         # UI strings
├── data/                   # sqlite db (gitignored; mounted volume on Railway)
└── assets/                 # screenshots, logo
```

---

## Deploy to Railway

> ⚠️ **DATA LOSS WARNING.** Railway containers have **ephemeral** filesystems.
> Set up a persistent volume at `/data` and map `DB_PATH=/data/bot.db` in your environment variables to ensure data persists.

---

## Pollinations API Endpoints Used

All requests go to `https://gen.pollinations.ai` with `Authorization: Bearer sk_...`.

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
