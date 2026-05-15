import asyncio
import base64
import random
import time
from dataclasses import dataclass

import httpx
from loguru import logger

from config import settings

BASE_URL = "https://gen.pollinations.ai"
IMAGE_URL = f"{BASE_URL}/v1/images/generations"
TEXT_URL = f"{BASE_URL}/v1/chat/completions"
MODELS_URL = f"{BASE_URL}/models"
BALANCE_URL = f"{BASE_URL}/account/balance"

MODELS_CACHE_TTL_SEC = 600  # 10 min


@dataclass(frozen=True)
class ModelInfo:
    name: str
    description: str
    price_pollen: float  # per single image, derived from completionImageTokens
    supports_image_input: bool  # True = supports img2img / edits
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class BalanceUnavailable:
    """Marker — key lacks 'profile usage' permission so balance can't be read."""
    reason: str

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
        self._models_cache: tuple[float, list[ModelInfo]] | None = None
        self._models_lock = asyncio.Lock()

    async def close(self) -> None:
        await self._client.aclose()

    async def list_image_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """Image-output models with pricing, sorted by price ascending.

        Cached for MODELS_CACHE_TTL_SEC. Falls back to a hardcoded baseline if
        the API is unreachable.
        """
        now = time.monotonic()
        if not force_refresh and self._models_cache is not None:
            ts, cached = self._models_cache
            if now - ts < MODELS_CACHE_TTL_SEC:
                return cached

        async with self._models_lock:
            # Re-check after acquiring the lock to avoid duplicate fetches.
            if not force_refresh and self._models_cache is not None:
                ts, cached = self._models_cache
                if now - ts < MODELS_CACHE_TTL_SEC:
                    return cached

            try:
                resp = await self._client.get(MODELS_URL, headers=self._headers)
                resp.raise_for_status()
                raw = resp.json()
            except Exception as e:
                logger.warning("list_image_models fetch failed: {}", e)
                if self._models_cache is not None:
                    return self._models_cache[1]
                return _FALLBACK_IMAGE_MODELS

            models: list[ModelInfo] = []
            for entry in raw if isinstance(raw, list) else []:
                if not isinstance(entry, dict):
                    continue
                if "image" not in entry.get("output_modalities", []):
                    continue
                pricing = entry.get("pricing") or {}
                # Heuristic from polli SKILL.md: if the pricing object has
                # *any* prompt* token fields, the completionImageTokens value
                # is per-token (~1000 tokens for a 1024×1024 image). Otherwise
                # it's flat per-image (flux=0.001, zimage=0.002, etc).
                price_raw = pricing.get("completionImageTokens")
                try:
                    price = float(price_raw) if price_raw is not None else 0.0
                except (TypeError, ValueError):
                    price = 0.0
                is_token_priced = any(
                    k for k in pricing
                    if k.startswith("prompt") and k != "currency"
                )
                if is_token_priced:
                    price *= 1000  # estimate for one 1024×1024 image

                models.append(
                    ModelInfo(
                        name=entry.get("name", ""),
                        description=(entry.get("description") or "").strip(),
                        price_pollen=price,
                        supports_image_input="image" in entry.get("input_modalities", []),
                        aliases=tuple(entry.get("aliases") or ()),
                    )
                )

            if not models:
                logger.warning("/models returned 0 image models; using fallback")
                models = list(_FALLBACK_IMAGE_MODELS)

            models.sort(key=lambda m: (m.price_pollen, m.name))
            self._models_cache = (now, models)
            return models

    async def get_balance(self) -> float | BalanceUnavailable:
        """Returns current pollen balance, or BalanceUnavailable if the key
        lacks the 'profile usage' permission (403) or the call fails."""
        try:
            resp = await self._client.get(BALANCE_URL, headers=self._headers)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            return BalanceUnavailable(f"network: {e}")

        if resp.status_code == 200:
            try:
                data = resp.json()
                return float(data.get("balance", 0))
            except Exception as e:
                return BalanceUnavailable(f"parse: {e}")

        if resp.status_code == 403:
            return BalanceUnavailable("missing_permission")
        if resp.status_code == 401:
            return BalanceUnavailable("unauthorized")
        return BalanceUnavailable(f"http_{resp.status_code}")

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


# Used if /models is unreachable at boot. Prices verified 2026-05.
_FALLBACK_IMAGE_MODELS: tuple[ModelInfo, ...] = (
    ModelInfo("flux", "Flux Schnell — fast high-quality", 0.001, False),
    ModelInfo("zimage", "Z-Image Turbo — fast 6B Flux", 0.002, False),
    ModelInfo("klein", "FLUX.2 Klein 4B — fast gen & edits", 0.01, True),
    ModelInfo("kontext", "FLUX.1 Kontext — in-context editing", 0.04, True),
    ModelInfo("qwen-image", "Qwen Image Plus — Alibaba", 0.045, True),
    ModelInfo("wan-image", "Wan 2.7 — Alibaba up to 2K", 0.0525, True),
)

pollinations = PollinationsClient()
