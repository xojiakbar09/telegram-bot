from aiogram.fsm.state import State, StatesGroup

class AnimeStates(StatesGroup):
    waiting_for_search = State()
    waiting_for_code = State()
    waiting_for_genre = State()

class AdminStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_genre = State()
    waiting_for_code = State()
    waiting_for_image = State()
    waiting_for_video = State()
    waiting_for_vip_price = State() 