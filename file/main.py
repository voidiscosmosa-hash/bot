# main.py (исправлено: кнопка back_to_user_menu, NameError, добавление каналов/чатов, улучшено логирование)

import asyncio
import logging
import os
import shutil
import random
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types.error_event import ErrorEvent
import aiosqlite
from giveaway_system import GiveawaySystem
from config import BOT_TOKEN, ADMIN_ID
from database import db
from keyboards import (
    get_admin_menu, get_user_menu, get_commission_menu,
    get_ad_menu, get_giveaway_menu_keyboard, get_strategy_menu,
    get_delay_menu, get_currency_menu, get_stats_menu, get_channels_menu,
    get_manage_admins_menu, get_commission_type_keyboard, get_favorite_type_keyboard,
    get_giveaway_target_menu, get_giveaway_info_keyboard, get_giveaway_list_keyboard
)
from states import (
    CommissionStates, AdStates, GiveawayStates,
    ChannelStates, BalanceStates, AdminStates
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация системы розыгрышей
giveaway_system = None

# Временное хранилище настроек розыгрыша
giveaway_settings = {
    'strategy': 'random',
    'delay': 60,
    'winners': 1,
    'currency': 'USDT',
    'prize': 0
}

# Путь к БД
try:
    from config import DATABASE_PATH
except ImportError:
    DATABASE_PATH = "giveaway_bot.db"

# Глобальные переменные для активного розыгрыша
active_giveaway = None
giveaway_participants = set()
giveaway_task = None

# Для рекламы
ad_active = False
ad_interval = 60

async def is_admin(user_id: int) -> bool:
    logger.info(f"Проверка админа для user_id={user_id}")
    admins = await db.get_all_admins()
    return user_id in [admin['user_id'] for admin in admins]

async def check_subscription(user_id: int, chat_id: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        logger.info(f"Проверка подписки: user_id={user_id}, chat_id={chat_id}, status={member.status}")
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки для user_id={user_id}, chat_id={chat_id}: {e}")
        return False

async def cancel_action(message: Message, state: FSMContext):
    """Отмена действия и возврат в главное меню"""
    await state.clear()
    is_active = active_giveaway is not None
    is_admin_user = await is_admin(message.from_user.id)
    await message.answer(
        "Действие отменено",
        reply_markup=get_user_menu(active_giveaway=is_active, is_admin=is_admin_user),
        parse_mode="HTML"
    )

# === СТАРТ БОТА ===
async def on_startup():
    global giveaway_system
    logger.info("Инициализация базы данных...")
    await db.init_db()
    await db.init_db_v2_tables()
    await db.update_channels_table()  # Миграция таблицы channels
    await db.add_admin(ADMIN_ID)
    logger.info("База данных готова!")
    giveaway_system = GiveawaySystem(bot, db)
    logger.info("Система розыгрышей инициализирована!")
    os.makedirs("backups", exist_ok=True)
    os.makedirs("giveaway_photos", exist_ok=True)
    logger.info("Бот запущен и готов к работе!")

# === КОМАНДЫ ===
@dp.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"Команда /start от user_id={message.from_user.id}")
    user_id = message.from_user.id
    username = message.from_user.username

    await db.add_user(user_id, username)

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("join_"):
        giveaway_id = int(args[1].replace("join_", ""))
        logger.info(f"Попытка участия в розыгрыше giveaway_id={giveaway_id} от user_id={user_id}")
        result = await giveaway_system.join_giveaway(giveaway_id, user_id)

        if result['success']:
            await message.answer(
                f"🎉 <b>Вы участвуете в розыгрыше!</b>\n\n"
                f"💰 Приз на победителя: ~{result['prize_per_winner']:.2f}\n"
                f"👥 Всего участников: {result['participants_count']}\n\n"
                f"Следите за результатами в канале/чате!\n"
                f"Удачи! 🍀",
                parse_mode="HTML"
            )
        else:
            reasons = {
                'not_found': "Розыгрыш не найден или уже завершен",
                'ended': "Розыгрыш уже завершен",
                'already_joined': "Вы уже участвуете в этом розыгрыше!",
                'not_subscribed': "Вы должны быть подписаны на канал/чат для участия"
            }
            await message.answer(
                f"❌ {reasons.get(result['reason'], 'Неизвестная ошибка')}",
                parse_mode="HTML"
            )
        return

    is_active = active_giveaway is not None
    is_admin_user = await is_admin(user_id)
    await message.answer(
        "Добро пожаловать!\n\n"
        "Я бот для проведения розыгрышей.\n",
        reply_markup=get_user_menu(active_giveaway=is_active, is_admin=is_admin_user),
        parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        logger.warning(f"Попытка доступа к админ-панели от не-админа user_id={user_id}")
        await message.answer("У вас нет доступа к админ-панели")
        return

    await message.answer(
        "Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )

# === CALLBACK - ГЛАВНОЕ МЕНЮ ===
@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        logger.warning(f"Попытка доступа к back_to_admin от не-админа user_id={user_id}")
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await callback.message.edit_text(
        "Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_user_menu")
async def back_to_user_menu(callback: CallbackQuery):
    logger.info(f"Переход в пользовательское меню для user_id={callback.from_user.id}")
    is_active = active_giveaway is not None
    is_admin_user = await is_admin(callback.from_user.id)
    await callback.message.edit_text(
        "Добро пожаловать!\n\n"
        "Я бот для проведения розыгрышей.\n",
        reply_markup=get_user_menu(active_giveaway=is_active, is_admin=is_admin_user),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "go_to_admin")
async def go_to_admin(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        logger.warning(f"Попытка доступа к go_to_admin от не-админа user_id={user_id}")
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await callback.message.edit_text(
        "Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

# === УПРАВЛЕНИЕ КАНАЛАМИ ===
@dp.callback_query(F.data == "channels_menu")
async def channels_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        logger.warning(f"Попытка доступа к channels_menu от не-админа user_id={user_id}")
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await callback.message.edit_text(
        "Управление каналами\n\n"
        "Выберите действие:",
        reply_markup=get_channels_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        logger.warning(f"Попытка доступа к add_channel от не-админа user_id={user_id}")
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await callback.message.edit_text(
        "Добавление канала\n\n"
        "Отправьте ID канала в формате: <code>@channel_name</code>, <code>-100123456789</code>, или ссылку <code>t.me/channel_name</code>\n\n"
        "Отмена: /cancel",
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.adding_channel)
    await state.update_data(is_admin=True)
    await callback.answer()

@dp.callback_query(F.data == "add_user_channel")
async def add_user_channel_start(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Начало добавления канала/чата для user_id={callback.from_user.id}")
    await callback.message.edit_text(
        "Добавление вашего канала или чата\n\n"
        "Отправьте ID в формате: <code>@channel_name</code>, <code>-100123456789</code>, или ссылку <code>t.me/channel_name</code>\n\n"
        "Убедитесь, что бот добавлен как администратор (для каналов) или участник (для чатов).\n\n"
        "Отмена: /cancel",
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.adding_channel)
    await state.update_data(is_admin=False)
    await callback.answer()

@dp.message(ChannelStates.adding_channel)
async def add_channel_process(message: Message, state: FSMContext):
    logger.info(f"Обработка добавления канала/чата от user_id={message.from_user.id}, текст={message.text}")
    text = message.text.strip()
    if text == "/cancel" or text.lower() == "отмена":
        await cancel_action(message, state)
        return

    data = await state.get_data()
    is_admin = data.get('is_admin', False)

    # Обработка ввода: @username, числовой ID или t.me ссылка
    channel_id = text
    if channel_id.startswith('t.me/'):
        channel_id = '@' + channel_id.split('/')[-1]
    elif channel_id.startswith('https://t.me/'):
        channel_id = '@' + channel_id.split('/')[-1]

    try:
        chat = await bot.get_chat(channel_id)
        channel_name = chat.title or chat.username or channel_id
        chat_type = 'channel' if chat.type in ['channel', 'supergroup'] else 'chat'

        # Проверка прав бота
        bot_member = await bot.get_chat_member(channel_id, bot.id)
        if chat_type == 'channel' and bot_member.status not in ['administrator', 'creator']:
            logger.error(f"Бот не является админом в канале {channel_id} для user_id={message.from_user.id}")
            await message.answer(
                "Ошибка: Бот должен быть администратором в канале.\nДобавьте бота как администратора и попробуйте снова.",
                parse_mode="HTML"
            )
            return
        elif chat_type == 'chat' and bot_member.status not in ['member', 'administrator', 'creator']:
            logger.error(f"Бот не является участником чата {channel_id} для user_id={message.from_user.id}")
            await message.answer(
                "Ошибка: Бот должен быть участником чата.\nДобавьте бота в чат и попробуйте снова.",
                parse_mode="HTML"
            )
            return

        # Проверка прав пользователя (только для не-админов)
        if not is_admin:
            user_member = await bot.get_chat_member(channel_id, message.from_user.id)
            if user_member.status not in ['administrator', 'creator']:
                logger.error(f"Пользователь user_id={message.from_user.id} не является админом в {channel_id}")
                await message.answer(
                    "Ошибка: Вы должны быть администратором или создателем канала/чата.",
                    parse_mode="HTML"
                )
                return

        await db.add_channel(channel_id, channel_name, chat_type=chat_type, added_by=message.from_user.id if not is_admin else None)

        is_active = active_giveaway is not None
        is_admin_user = await is_admin(message.from_user.id)
        reply_markup = get_admin_menu() if is_admin else get_user_menu(active_giveaway=is_active, is_admin=is_admin_user)
        await message.answer(
            f"{'Канал' if chat_type == 'channel' else 'Чат'} добавлен!\n\n"
            f"Название: {channel_name}\n"
            f"ID: <code>{channel_id}</code>\n"
            f"Комиссия: 5%",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка добавления канала/чата {channel_id} для user_id={message.from_user.id}: {e}")
        await message.answer(
            f"Ошибка добавления:\n\n"
            f"Причина: {str(e)}\n\n"
            f"Убедитесь, что:\n"
            f"• Бот добавлен в канал/чат\n"
            f"• ID или ссылка указаны правильно",
            reply_markup=get_admin_menu() if is_admin else get_user_menu(active_giveaway=active_giveaway is not None, is_admin=await is_admin(message.from_user.id)),
            parse_mode="HTML"
        )

    await state.clear()

@dp.callback_query(F.data == "list_channels")
async def list_channels(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        logger.warning(f"Попытка доступа к list_channels от не-админа user_id={user_id}")
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    channels = await db.get_all_channels()

    if not channels:
        await callback.message.edit_text(
            "Список каналов пуст\n\n"
            "Добавьте канал для начала работы.",
            reply_markup=get_channels_menu(),
            parse_mode="HTML"
        )
    else:
        text = "Список каналов:\n\n"
        for channel in channels:
            text += (
                f"• {channel['channel_name']}\n"
                f"  ID: <code>{channel['channel_id']}</code>\n"
                f"  Тип: {channel['chat_type']}\n"
                f"  Комиссия: {channel['commission']} {channel['commission_type']}\n"
                f"  {'Активен' if channel['active'] else 'Неактивен'}\n"
                f"  Добавил: {'Админ' if channel['added_by'] is None else f'ID {channel['added_by']}'}\n\n"
            )

        await callback.message.edit_text(
            text,
            reply_markup=get_channels_menu(),
            parse_mode="HTML"
        )

    await callback.answer()

@dp.callback_query(F.data == "delete_channel")
async def delete_channel_start(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        logger.warning(f"Попытка доступа к delete_channel от не-админа user_id={user_id}")
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    channels = await db.get_all_channels()

    if not channels:
        await callback.answer("Нет каналов для удаления", show_alert=True)
        return

    text = "Удаление канала\n\n"
    text += "Отправьте ID канала для удаления:\n\n"
    for channel in channels:
        text += f"• {channel['channel_name']}: <code>{channel['channelOld channel_id']}</code>\n"
    text += "\nОтмена: /cancel"

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(ChannelStates.deleting_channel)
    await callback.answer()

@dp.message(ChannelStates.deleting_channel)
async def delete_channel_process(message: Message, state: FSMContext):
    logger.info(f"Обработка удаления канала от user_id={message.from_user.id}, текст={message.text}")
    text = message.text.strip()
    if text == "/cancel" or text.lower() == "отмена":
        await cancel_action(message, state)
        return

    channel_id = text
    channel = await db.get_channel(channel_id)
    if not channel:
        await message.answer("Канал не найден!", reply_markup=get_admin_menu())
        await state.clear()
        return

    await db.delete_channel(channel_id)
    await message.answer(
        f"Канал {channel['channel_name']} удалён!",
        reply_markup=get_admin_menu()
    )
    await state.clear()

@dp.message(GiveawayStates.uploading_photo)
async def process_giveaway_photo(message: Message, state: FSMContext):
    logger.info(f"Обработка фото розыгрыша от user_id={message.from_user.id}")
    photo_path = None
    
    if message.text not in ["/skip", "/cancel", "отмена"]:
        if message.photo:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            
            os.makedirs("giveaway_photos", exist_ok=True)
            photo_path = f"giveaway_photos/{photo.file_id}.jpg"
            
            await bot.download_file(file.file_path, photo_path)
        else:
            await message.answer("Это не фото! Отправьте фото или /skip")
            return
    elif message.text in ["/cancel", "отмена"]:
        await cancel_action(message, state)
        return
    
    await state.update_data(photo_path=photo_path)
    
    data = await state.get_data()
    
    prize_per_winner = data['prize_amount'] / data['winners_count']
    
    text = (
        "✅ <b>Подтверждение создания розыгрыша</b>\n\n"
        f"📍 Место: {data['target_name']}\n"
        f"💰 Призовой фонд: {data['prize_amount']} {data['currency']}\n"
        f"🏆 Победителей: {data['winners_count']}\n"
        f"💵 На каждого: ~{prize_per_winner:.2f} {data['currency']}\n"
        f"⏱ Длительность: {data['duration_minutes']} минут\n"
        f"🎯 Стратегия: {data['strategy']}\n"
    )
    
    if data.get('description'):
        text += f"📝 Описание: {data['description'][:100]}...\n"
    if data.get('photo_path'):
        text += "🖼 С изображением\n"
    
    text += "\n<b>Все верно?</b>"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="✅ Запустить", callback_data="confirm_giveaway"))
    keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_admin" if await is_admin(message.from_user.id) else "back_to_user_menu"))
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(GiveawayStates.confirming)

# === ОШИБКИ ===
@dp.error()
async def error_handler(update: ErrorEvent):
    logger.error(f"Ошибка при обработке обновления: {update.exception}")
    if update.update.message:
        await update.update.message.answer("Произошла ошибка, попробуйте позже")
    elif update.update.callback_query:
        await update.update.callback_query.answer("Произошла ошибка", show_alert=True)

# === ЗАПУСК БОТА ===
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())