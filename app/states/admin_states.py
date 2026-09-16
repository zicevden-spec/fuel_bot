from aiogram.fsm.state import State, StatesGroup


class AddCity(StatesGroup):
    waiting_name = State()


class AddStation(StatesGroup):
    waiting_city = State()
    waiting_name = State()
    waiting_brand = State()
    waiting_address = State()
    waiting_fuel = State()


class BroadcastState(StatesGroup):
    waiting_message = State()
    confirming = State()
