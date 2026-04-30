# PromptArt — AI Image Generation Telegram Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Powered by Pollinations.ai](https://img.shields.io/badge/Powered%20by-Pollinations.ai-ff69b4.svg)](https://pollinations.ai)

> Telegram bot for AI image generation via [Pollinations.ai](https://pollinations.ai). Style presets, prompt enhancement, inline mode, history & favorites.

<p align="center">
  <img src="assets/logo.png" alt="PromptArt logo" width="180" />
</p>

## Features

- **Image generation** — 4 models (Flux, Turbo, Seedream-4.0, GPT-Image-2)
- **5 aspect ratios** — 1:1, 16:9, 9:16, 4:3, 3:4
- **7 style presets** — photorealistic, anime, digital painting, oil, 3D, cyberpunk, sketch
- **Prompt enhancement** — one-tap improvement via Pollinations Text API
- **Inline mode** — `@bot prompt` in any chat returns 3 variants
- **History & favorites** — last 10 generations, save to favorites for quick re-send
- **Rate limiting** — built-in protection (5 generations / minute)

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/zFannur/promptart-bot.git
cd promptart-bot
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# edit .env with your tokens

# 3. Run
python bot.py
```

## Getting tokens

**Telegram bot token:**
1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot`, follow the prompts
3. Copy the token like `123456789:ABCDef...` into `BOT_TOKEN`
4. Send `/setinline` and pick a placeholder text (e.g. "Describe an image…")

**Pollinations API key:**
1. Go to [pollinations.ai](https://pollinations.ai) and sign in via GitHub
2. Generate an API key in your dashboard
3. Copy the `sk_...` key into `POLLINATIONS_API_KEY`

**Your Telegram ID** (for `ADMIN_ID`):
- Open [@userinfobot](https://t.me/userinfobot) and send any message

## Project structure

```
promptart_bot/
├── bot.py                  # entry point
├── config.py               # pydantic-settings
├── handlers/               # telegram handlers
├── services/               # pollinations client, db
├── keyboards/              # inline + reply keyboards
├── middlewares/            # i18n, rate limit
├── states/                 # FSM
├── utils/                  # constants, helpers
├── locales/                # en.json
├── data/                   # sqlite db (gitignored)
└── assets/                 # screenshots, logo
```

## Deploy to Railway

1. Push the repo to GitHub.
2. Sign in at [railway.app](https://railway.app) with GitHub.
3. **New Project → Deploy from GitHub repo** → pick this repo.
4. In **Variables**, add:
   - `BOT_TOKEN`
   - `POLLINATIONS_API_KEY`
   - `ADMIN_ID`
   - `DB_PATH=/data/bot.db`
5. In **Settings → Volumes**, create a volume mounted at `/data` (persists DB across redeploys).
6. Done — Railway uses `Procfile` automatically.

## Tech stack

- **aiogram 3.13** — async Telegram framework
- **httpx** — async HTTP client with timeout/retry
- **aiosqlite** — async SQLite
- **pydantic-settings** — env config
- **loguru** — logging
- **Pillow** — image post-processing

## Pollinations Hive

This bot is built for the [Pollinations Hive](https://github.com/pollinations/hive) registry. All API calls include `referrer=promptart-bot` for proper attribution.

## License

MIT — see [LICENSE](LICENSE).

Built with [Pollinations.ai](https://pollinations.ai).
