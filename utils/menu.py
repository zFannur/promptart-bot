from utils.i18n import SUPPORTED_LANGS, load_locale


def _labels(key: str) -> frozenset[str]:
    return frozenset(load_locale(lang)[key] for lang in SUPPORTED_LANGS)


CREATE_IMAGE_LABELS = _labels("menu.create_image")
CREATE_VIDEO_LABELS = _labels("menu.create_video")
CREATE_AUDIO_LABELS = _labels("menu.create_audio")
CHAT_LABELS = _labels("menu.chat")
EDIT_LABELS = _labels("menu.edit")
SETTINGS_LABELS = _labels("menu.settings")
HISTORY_LABELS = _labels("menu.history")
FAVORITES_LABELS = _labels("menu.favorites")
BALANCE_LABELS = _labels("menu.balance")
HELP_LABELS = _labels("menu.help")

# Union of all menu reply-button labels. Useful in stateful handlers that
# need to ignore inputs that are actually menu navigation, not content.
ALL_MENU_LABELS = (
    CREATE_IMAGE_LABELS
    | CREATE_VIDEO_LABELS
    | CREATE_AUDIO_LABELS
    | CHAT_LABELS
    | EDIT_LABELS
    | SETTINGS_LABELS
    | HISTORY_LABELS
    | FAVORITES_LABELS
    | BALANCE_LABELS
    | HELP_LABELS
)
