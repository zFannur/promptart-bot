from dataclasses import dataclass


@dataclass(frozen=True)
class ImageModel:
    key: str
    label: str
    description_key: str


# Keys MUST match Pollinations' /v1/images/generations `model` enum.
MODELS: tuple[ImageModel, ...] = (
    ImageModel("flux", "Flux", "model.flux"),
    ImageModel("zimage", "Turbo", "model.zimage"),
    ImageModel("seedream", "Seedream", "model.seedream"),
    ImageModel("gpt-image-2", "GPT Image", "model.gpt_image"),
)

MODELS_BY_KEY: dict[str, ImageModel] = {m.key: m for m in MODELS}

DEFAULT_MODEL = "flux"

# Legacy → current key migration for users registered before the v1 endpoint switch.
LEGACY_MODEL_REMAP: dict[str, str] = {
    "turbo": "zimage",
    "seedream-4.0": "seedream",
}
