# keyboards.py (исправлено для корректной работы кнопок)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_menu():
    """Меню администратора"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 Создать розыгрыш", callback_data="create_giveaway"))
    builder.row(InlineKeyboardButton(text="📋 Активные розыгрыши", callback_data="active_giveaways"))
    builder.row(InlineKeyboardButton(text="📺 Управление каналами", callback_data="channels_menu"))
    builder.row(InlineKeyboardButton(text="💰 Управление комиссией", callback_data="commission_menu"))
    builder.row(InlineKeyboardButton(text="📢 Рекламная панель", callback_data="ad_panel"))
    builder.row(InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins"))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="statistics"))
    builder.row(InlineKeyboardButton(text="◶ Назад в меню пользователя", callback_data="back_to_user_menu"))
    return builder.as_markup()

def get_user_menu(active_giveaway: bool = False, is_admin: bool = False):
    """Меню пользователя"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats"))
    builder.row(InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_balance"))
    builder.row(InlineKeyboardButton(text="🚀 Начать розыгрыш", callback_data="create_giveaway"))
    builder.row(InlineKeyboardButton(text="➕ Добавить канал/чат", callback_data="add_user_channel"))
    if active_giveaway:
        builder.row(InlineKeyboardButton(text="🎁 Участвовать в розыгрыше", callback_data="join_giveaway"))
    if is_admin:
        builder.row(InlineKeyboardButton(text="🔑 Админ-панель", callback_data="go_to_admin"))
    return builder.as_markup()

def get_channels_menu():
    """Меню управления каналами"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel"))
    builder.row(InlineKeyboardButton(text="📜 Список каналов", callback_data="list_channels"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить канал", callback_data="delete_channel"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_admin"))
    return builder.as_markup()

def get_commission_menu():
    """Меню управления комиссией"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌍 Глобальная комиссия", callback_data="set_global_commission"))
    builder.row(InlineKeyboardButton(text="👤 Комиссия пользователя", callback_data="set_user_commission"))
    builder.row(InlineKeyboardButton(text="📢 Комиссия чата", callback_data="set_chat_commission"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_admin"))
    return builder.as_markup()

def get_ad_menu():
    """Меню рекламы"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Создать рекламу", callback_data="create_ad"))
    builder.row(InlineKeyboardButton(text="📜 Список объявлений", callback_data="list_ads"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить рекламу", callback_data="delete_ad"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_admin"))
    return builder.as_markup()

def get_giveaway_menu_keyboard():
    """Меню выбора типа розыгрыша"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 В канал/чат", callback_data="giveaway_to_chat"))
    builder.row(InlineKeyboardButton(text="👤 В личные сообщения", callback_data="giveaway_to_user"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_admin"))
    return builder.as_markup()

def get_strategy_menu():
    """Меню выбора стратегии розыгрыша"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎲 Случайный выбор", callback_data="strategy_random"))
    builder.row(InlineKeyboardButton(text="⏰ Первый участник", callback_data="strategy_first"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_giveaway_menu"))
    return builder.as_markup()

def get_delay_menu():
    """Меню выбора длительности розыгрыша"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏱ 30 минут", callback_data="delay_30"))
    builder.row(InlineKeyboardButton(text="⏱ 60 минут", callback_data="delay_60"))
    builder.row(InlineKeyboardButton(text="⏱ 120 минут", callback_data="delay_120"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_giveaway_menu"))
    return builder.as_markup()

def get_currency_menu():
    """Меню выбора валюты"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💵 USDT", callback_data="currency_usdt"))
    builder.row(InlineKeyboardButton(text="💶 RUB", callback_data="currency_rub"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_giveaway_menu"))
    return builder.as_markup()

def get_stats_menu():
    """Меню статистики"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📈 За месяц", callback_data="stats_month"))
    builder.row(InlineKeyboardButton(text="📊 За всё время", callback_data="stats_all"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_admin"))
    return builder.as_markup()

def get_manage_admins_menu():
    """Меню управления админами"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_admin"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить админа", callback_data="delete_admin"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_admin"))
    return builder.as_markup()

def get_commission_type_keyboard():
    """Клавиатура выбора типа комиссии"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Процент", callback_data="commission_percent"))
    builder.row(InlineKeyboardButton(text="Фиксированная", callback_data="commission_fixed"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="commission_menu"))
    return builder.as_markup()

def get_favorite_type_keyboard():
    """Клавиатура выбора типа избранного"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 Пользователь", callback_data="favorite_user"))
    builder.row(InlineKeyboardButton(text="📢 Чат", callback_data="favorite_chat"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="commission_menu"))
    return builder.as_markup()

def get_giveaway_target_menu(channels):
    """Меню выбора цели розыгрыша"""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.row(InlineKeyboardButton(
            text=channel['channel_name'],
            callback_data=f"giveaway_target_{channel['channel_id']}"
        ))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_giveaway_menu"))
    return builder.as_markup()

def get_giveaway_info_keyboard(giveaway_id: int):
    """Клавиатура для информации о розыгрыше"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить розыгрыш", callback_data=f"cancel_giveaway_{giveaway_id}"))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="active_giveaways"))
    return builder.as_markup()

def get_giveaway_list_keyboard(giveaways):
    """Клавиатура списка розыгрышей"""
    builder = InlineKeyboardBuilder()
    for giveaway in giveaways:
        builder.row(InlineKeyboardButton(
            text=f"Розыгрыш #{giveaway['id']}",
            callback_data=f"giveaway_info_{giveaway['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◄ Назад", callback_data="back_to_admin"))
    return builder.as_markup()