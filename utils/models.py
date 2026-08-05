"""User-facing image model registry.

The live source of truth is `services.pollinations.list_image_models()`
which queries `gen.pollinations.ai/models`. This module only holds:
- The default model key
- The legacy key migration map (for users who picked a model before the
  Pollinations v1 endpoint switch)
"""

DEFAULT_MODEL = "flux"
# Cheapest model that accepts image input (in-context editing).
# Verified 2026-08: klein = FLUX.2 Klein 4B @ 0.005 pollen/image.
DEFAULT_EDIT_MODEL = "klein"

# Legacy → current key migration for users registered before the v1 endpoint switch.
LEGACY_MODEL_REMAP: dict[str, str] = {
    "turbo": "zimage",
    "seedream-4.0": "seedream",
    "gpt-image-2": "gptimage",
}


def format_price(pollen: float) -> str:
    """Render pollen price compactly: 0.002 -> '0.002p', 0.0525 -> '0.053p'.

    The zero-stripping used to run after "p" was appended, so it never matched and
    prices came out padded — 0.002 rendered as "0.0020p" and 0.1 as "0.100p".
    """
    if pollen <= 0:
        return "free"
    if pollen < 0.001:
        digits = f"{pollen:.5f}"
    elif pollen < 0.01:
        digits = f"{pollen:.4f}"
    else:
        digits = f"{pollen:.3f}"
    return digits.rstrip("0").rstrip(".") + "p"


# Marks a model that the free hourly tier grant will not cover.
PAID_ICON = "💰"


def price_label(model) -> str:
    """Price as shown to the user: unit included, '~' when it is an estimate.

    `model` is a services.pollinations.ModelInfo — taken untyped to keep this
    module import-free of the client.
    """
    if model.price_pollen <= 0:
        return "free"
    prefix = "~" if getattr(model, "price_estimated", False) else ""
    return f"{prefix}{format_price(model.price_pollen)}{getattr(model, 'price_unit', '')}"


def model_label(model) -> str:
    """`name · price` plus the paid marker — the one place that layout is decided."""
    paid = f" {PAID_ICON}" if getattr(model, "paid_only", False) else ""
    return f"{model.name} · {price_label(model)}{paid}"
