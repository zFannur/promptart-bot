import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"
SUPPORTED_LANGS: tuple[str, ...] = ("en",)
DEFAULT_LANG = "en"


@lru_cache(maxsize=4)
def load_locale(lang: str = DEFAULT_LANG) -> dict[str, str]:
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    path = LOCALES_DIR / f"{lang}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def detect_lang(language_code: str | None) -> str:
    return DEFAULT_LANG


def t(i18n: dict[str, str], key: str, **kwargs: object) -> str:
    template = i18n.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
