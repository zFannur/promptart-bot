from dataclasses import dataclass


@dataclass(frozen=True)
class ImageModel:
    key: str
    label: str
    description_key: str


MODELS: tuple[ImageModel, ...] = (
    ImageModel("flux", "Flux", "model.flux"),
    ImageModel("turbo", "Turbo", "model.turbo"),
    ImageModel("seedream-4.0", "Seedream", "model.seedream"),
    ImageModel("gpt-image-2", "GPT Image", "model.gpt_image"),
)

MODELS_BY_KEY: dict[str, ImageModel] = {m.key: m for m in MODELS}

DEFAULT_MODEL = "flux"
INLINE_MODEL = "turbo"
