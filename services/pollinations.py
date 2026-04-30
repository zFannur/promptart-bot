import asyncio
import random
from urllib.parse import quote

import httpx
from loguru import logger

from config import settings

IMAGE_URL = "https://image.pollinations.ai/prompt/{prompt}"
TEXT_URL = "https://text.pollinations.ai/openai"

ENHANCER_SYSTEM_PROMPT = (
    "You are an expert prompt engineer for image generation models. "
    "Take the user's prompt and enhance it with vivid visual details, "
    "lighting, composition, color palette, and artistic style descriptors. "
    "Keep it under 400 characters. Return ONLY the enhanced prompt — "
    "no explanations, no quotes, no preamble."
)


class PollinationsError(Exception):
    """Base error for Pollinations API failures."""


class NSFWRejected(PollinationsError):
    """Prompt was rejected by the moderation filter."""


class QuotaExhausted(PollinationsError):
    """API quota exhausted on the current tier."""


class PollinationsClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(90.0, connect=10.0),
            follow_redirects=True,
        )
        self._headers = {"Authorization": f"Bearer {settings.pollinations_api_key}"}
        self._referrer = settings.pollinations_referrer

    async def close(self) -> None:
        await self._client.aclose()

    async def generate_image(
        self,
        prompt: str,
        *,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux",
        seed: int | None = None,
    ) -> tuple[bytes, int]:
        """Returns (image_bytes, used_seed)."""
        if seed is None:
            seed = random.randint(0, 2**31 - 1)

        params = {
            "width": width,
            "height": height,
            "model": model,
            "seed": seed,
            "nologo": "true",
            "private": "true",
            "referrer": self._referrer,
        }
        url = IMAGE_URL.format(prompt=quote(prompt, safe=""))

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._client.get(url, params=params, headers=self._headers)
                if resp.status_code == 200:
                    if not resp.content or len(resp.content) < 100:
                        raise PollinationsError("empty image response")
                    return resp.content, seed
                if resp.status_code == 400:
                    body = resp.text.lower()
                    if "nsfw" in body or "moderation" in body or "safety" in body:
                        raise NSFWRejected("moderation_filter")
                    raise PollinationsError(f"bad request (status 400, len={len(body)})")
                if resp.status_code in (401, 403):
                    raise PollinationsError(f"auth failed: {resp.status_code}")
                if resp.status_code in (402, 429):
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise QuotaExhausted(f"status {resp.status_code}")
                if 500 <= resp.status_code < 600:
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise PollinationsError(f"server error {resp.status_code}")
                raise PollinationsError(f"unexpected status {resp.status_code}")
            except (NSFWRejected, QuotaExhausted):
                raise
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exc = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise PollinationsError(f"network error: {e}") from e

        raise PollinationsError(str(last_exc) if last_exc else "exhausted retries")

    async def generate_image_url(
        self,
        prompt: str,
        *,
        width: int = 1024,
        height: int = 1024,
        model: str = "turbo",
        seed: int | None = None,
    ) -> str:
        """Build a public Pollinations URL for inline mode (no fetch)."""
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        params = {
            "width": width,
            "height": height,
            "model": model,
            "seed": seed,
            "nologo": "true",
            "private": "true",
            "referrer": self._referrer,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{IMAGE_URL.format(prompt=quote(prompt, safe=''))}?{query}"

    async def enhance_prompt(self, prompt: str) -> str:
        payload = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": ENHANCER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "referrer": self._referrer,
        }
        for attempt in range(2):
            try:
                resp = await self._client.post(
                    TEXT_URL,
                    json=payload,
                    headers=self._headers,
                    params={"referrer": self._referrer},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    enhanced = data["choices"][0]["message"]["content"].strip()
                    return enhanced.strip('"').strip("'")
                if resp.status_code in (429, 500, 502, 503):
                    if attempt < 1:
                        await asyncio.sleep(1)
                        continue
                logger.warning("enhance_prompt failed: {} {}", resp.status_code, resp.text[:100])
                raise PollinationsError(f"enhance failed: {resp.status_code}")
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < 1:
                    await asyncio.sleep(1)
                    continue
                raise PollinationsError(f"enhance network error: {e}") from e
        raise PollinationsError("enhance exhausted retries")


pollinations = PollinationsClient()
