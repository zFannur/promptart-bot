from aiogram.fsm.state import State, StatesGroup


class GenStates(StatesGroup):
    waiting_for_prompt = State()
    confirming_enhanced = State()


class EditStates(StatesGroup):
    # User has tapped «✏️ Edit». Bot collects photos (file_ids) into FSM
    # data['photos'] until a text message arrives — that text is the prompt
    # and triggers the edit call.
    collecting = State()
