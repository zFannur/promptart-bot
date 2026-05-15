"""User-facing image model registry.

The live source of truth is `services.pollinations.list_image_models()`
which queries `gen.pollinations.ai/models`. This module only holds:
- The default model key
- The legacy key migration map (for users who picked a model before the
  Pollinations v1 endpoint switch)
"""

DEFAULT_MODEL = "flux"
# Cheapest model that accepts image input (in-context editing).
# Verified 2026-05: klein = FLUX.2 Klein 4B @ ~0.01 pollen/image.
DEFAULT_EDIT_MODEL = "klein"

# Legacy → current key migration for users registered before the v1 endpoint switch.
LEGACY_MODEL_REMAP: dict[str, str] = {
    "turbo": "zimage",
    "seedream-4.0": "seedream",
    "gpt-image-2": "gptimage",
}


def format_price(pollen: float) -> str:
    """Render pollen price compactly: 0.001 -> '0.001p', 0.0525 -> '0.053p'."""
    if pollen <= 0:
        return "free"
    if pollen < 0.001:
        return f"{pollen:.5f}p".rstrip("0").rstrip(".")
    if pollen < 0.01:
        return f"{pollen:.4f}p".rstrip("0").rstrip(".")
    return f"{pollen:.3f}p".rstrip("0").rstrip(".")
