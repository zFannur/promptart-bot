import asyncio
import base64
import random

import httpx
from loguru import logger

from config import settings

BASE_URL = "https://gen.pollinations.ai"
IMAGE_URL = f"{BASE_URL}/v1/images/generations"
TEXT_URL = f"{BASE_URL}/v1/chat/completions"

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
    """API quota / pollen balance exhausted on the current tier."""


class PremiumRequired(PollinationsError):
    """The chosen model requires more pollen than the account has."""


class PollinationsClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(90.0, connect=10.0),
            follow_redirects=True,
        )
        self._headers = {"Authorization": f"Bearer {settings.pollinations_api_key}"}

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
        """Returns (image_bytes, used_seed) via gen.pollinations.ai/v1/images/generations."""
        if seed is None:
            seed = random.randint(0, 2**31 - 1)

        body = {
            "prompt": prompt,
            "model": model,
            "size": f"{width}x{height}",
            "response_format": "b64_json",
            "seed": seed,
            "nologo": True,
        }

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._client.post(IMAGE_URL, json=body, headers=self._headers)
                if resp.status_code == 200:
                    data = resp.json()
                    b64 = data.get("data", [{}])[0].get("b64_json")
                    if not b64:
                        raise PollinationsError("response missing b64_json")
                    image_bytes = base64.b64decode(b64)
                    if len(image_bytes) < 100:
                        raise PollinationsError("decoded image too small")
                    return image_bytes, seed

                self._raise_for_status(resp, kind="image")

            except (NSFWRejected, QuotaExhausted, PremiumRequired):
                raise
            except PollinationsError as e:
                # 5xx already retried inside _raise_for_status path; surface other 4xx immediately
                if attempt < 2 and "server error" in str(e):
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exc = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise PollinationsError(f"network error: {e}") from e

        raise PollinationsError(str(last_exc) if last_exc else "exhausted retries")

    async def enhance_prompt(self, prompt: str) -> str:
        payload = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": ENHANCER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        for attempt in range(2):
            try:
                resp = await self._client.post(TEXT_URL, json=payload, headers=self._headers)
                if resp.status_code == 200:
                    data = resp.json()
                    enhanced = data["choices"][0]["message"]["content"].strip()
                    return enhanced.strip('"').strip("'")
                if resp.status_code in (429, 500, 502, 503):
                    if attempt < 1:
                        await asyncio.sleep(1)
                        continue
                logger.warning("enhance_prompt non-200: status={}", resp.status_code)
                raise PollinationsError(f"enhance failed: {resp.status_code}")
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < 1:
                    await asyncio.sleep(1)
                    continue
                raise PollinationsError(f"enhance network error: {e}") from e
        raise PollinationsError("enhance exhausted retries")

    def _raise_for_status(self, resp: httpx.Response, *, kind: str) -> None:
        status = resp.status_code
        try:
            payload = resp.json()
        except Exception:
            payload = {}
        err = payload.get("error", {}) if isinstance(payload, dict) else {}
        code = err.get("code", "")
        msg = (err.get("message", "") or "").lower()

        if status == 400:
            if "nsfw" in msg or "moderation" in msg or "safety" in msg or "safety" in code.lower():
                raise NSFWRejected("moderation_filter")
            logger.warning("{} 400 code={}", kind, code or "?")
            raise PollinationsError(f"bad request ({code or '400'})")

        if status in (401, 403):
            logger.error("{} auth failed: status={}", kind, status)
            raise PollinationsError(f"auth failed ({status})")

        if status == 402:
            logger.info("{} payment required: {}", kind, msg[:120])
            raise PremiumRequired(msg[:200] or "insufficient pollen balance")

        if status == 429:
            raise QuotaExhausted("rate_limited")

        if 500 <= status < 600:
            raise PollinationsError(f"server error {status}")

        raise PollinationsError(f"unexpected status {status}")


pollinations = PollinationsClient()
