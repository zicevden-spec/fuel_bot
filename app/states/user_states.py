from aiogram.fsm.state import State, StatesGroup


class ReportState(StatesGroup):
    waiting_availability = State()
    waiting_queue = State()
