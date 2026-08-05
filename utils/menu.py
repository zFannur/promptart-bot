from aiogram import F

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
CLEAR_CONTEXT_LABELS = _labels("menu.clear_context")
BACK_TO_MENU_LABELS = _labels("menu.back_to_menu")

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
    | CLEAR_CONTEXT_LABELS
    | BACK_TO_MENU_LABELS
)

# Text that is actual user content, not a tap on a reply-keyboard button.
# Every prompt-collecting handler must filter on this: without it, pressing
# "🏠 Main menu" while a prompt is awaited generates an image of the words
# "🏠 Main menu". A bot restart wipes MemoryStorage while the old keyboard
# stays on screen, so this happens without the user doing anything odd.
USER_TEXT = F.text & ~F.text.in_(ALL_MENU_LABELS)
