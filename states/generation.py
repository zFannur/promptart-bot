from aiogram.fsm.state import State, StatesGroup


class GenStates(StatesGroup):
    waiting_for_prompt = State()
    confirming_enhanced = State()
