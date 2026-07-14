from aiogram.fsm.state import State, StatesGroup

class DealCreation(StatesGroup):
    currency = State()
    amount = State()
    description = State()
    nft_link = State()

class RequisitesEdit(StatesGroup):
    text = State()

class Withdraw(StatesGroup):
    amount = State()
    # requisites берем из профиля

class AddBalanceAdmin(StatesGroup):
    user_id = State()
    amount = State()

class BoostSuccessAdmin(StatesGroup):
    user_id = State()
    count = State()

class ChatAdmin(StatesGroup):
    username = State()
    message = State()

class HostleBuyAdmin(StatesGroup):
    memo = State()

class RefAdmin(StatesGroup):
    deal_id = State()
