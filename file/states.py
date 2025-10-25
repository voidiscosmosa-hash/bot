# states.py (с интеграцией из states_update.py)

from aiogram.fsm.state import State, StatesGroup

class CommissionStates(StatesGroup):
    choosing_channel = State()
    setting_commission = State()
    setting_global_commission = State()  # Существующее состояние
    setting_channel_commission = State() 
    setting_chat_commission = State()
    setting_user_commission = State()
    setting_fav_commission = State()
    choosing_commission_type = State()
    adding_favorite = State()

class AdStates(StatesGroup):
    uploading_ad = State()
    deleting_ad = State()
    setting_interval = State()

class GiveawayStates(StatesGroup):
    # Старые состояния (оставляем для совместимости)
    choosing_strategy = State()
    setting_delay = State()
    custom_delay = State()
    setting_winners = State()
    choosing_currency = State()
    setting_prize = State()
    
    # Новые состояния для создания розыгрыша
    choosing_target = State()
    setting_description = State()
    uploading_photo = State()
    confirming = State()

class ChannelStates(StatesGroup):
    adding_channel = State()
    deleting_channel = State()

class BalanceStates(StatesGroup):
    adding_balance = State()

class AdminStates(StatesGroup):
    adding_admin = State()
    removing_admin = State()