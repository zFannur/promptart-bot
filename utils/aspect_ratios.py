from dataclasses import dataclass


@dataclass(frozen=True)
class AspectRatio:
    key: str
    label: str
    width: int
    height: int


RATIOS: tuple[AspectRatio, ...] = (
    AspectRatio("1:1", "1:1", 1024, 1024),
    AspectRatio("16:9", "16:9", 1920, 1080),
    AspectRatio("9:16", "9:16", 1080, 1920),
    AspectRatio("4:3", "4:3", 1600, 1200),
    AspectRatio("3:4", "3:4", 1200, 1600),
)

RATIOS_BY_KEY: dict[str, AspectRatio] = {r.key: r for r in RATIOS}

DEFAULT_RATIO = "1:1"
