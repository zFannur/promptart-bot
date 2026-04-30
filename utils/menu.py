from utils.i18n import SUPPORTED_LANGS, load_locale


def _labels(key: str) -> frozenset[str]:
    return frozenset(load_locale(lang)[key] for lang in SUPPORTED_LANGS)


CREATE_LABELS = _labels("menu.create")
SETTINGS_LABELS = _labels("menu.settings")
HISTORY_LABELS = _labels("menu.history")
FAVORITES_LABELS = _labels("menu.favorites")
HELP_LABELS = _labels("menu.help")
