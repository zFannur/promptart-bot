from dataclasses import dataclass


@dataclass(frozen=True)
class AspectRatio:
    key: str
    label: str
    width: int
    height: int


# Resolutions are SDXL-canonical buckets: multiples of 64, ~1 MP each.
# Flux / zimage / kontext / qwen-image all train near these sizes, so non-
# bucket dimensions (e.g. 1920×1080) get silently snapped or produce warped
# compositions. Keeping ratios close to the listed label (not exact) trades
# 1–2% aspect drift for clean, undistorted output.
RATIOS: tuple[AspectRatio, ...] = (
    AspectRatio("1:1", "1:1", 1024, 1024),
    AspectRatio("16:9", "16:9", 1344, 768),
    AspectRatio("9:16", "9:16", 768, 1344),
    AspectRatio("4:3", "4:3", 1152, 896),
    AspectRatio("3:4", "3:4", 896, 1152),
)

RATIOS_BY_KEY: dict[str, AspectRatio] = {r.key: r for r in RATIOS}

DEFAULT_RATIO = "1:1"
