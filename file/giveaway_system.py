# Новая система розыгрышей
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

logger = logging.getLogger(__name__)

class GiveawaySystem:
    def __init__(self, bot: Bot, db):
        self.bot = bot
        self.db = db
        self.active_giveaways: Dict[int, Dict] = {}  # giveaway_id -> giveaway_data
        self.giveaway_tasks: Dict[int, asyncio.Task] = {}  # giveaway_id -> task
        
    async def create_giveaway(
        self,
        creator_id: int,
        target_type: str,  # 'channel' или 'chat'
        target_id: str,
        prize_amount: float,
        currency: str,
        winners_count: int,
        duration_minutes: int,
        photo_path: Optional[str] = None,
        description: Optional[str] = None,
        strategy: str = 'random'
    ) -> int:
        """Создание нового розыгрыша"""
        
        # Сохраняем в БД
        giveaway_id = await self.db.create_giveaway_v2(
            creator_id=creator_id,
            target_type=target_type,
            target_id=target_id,
            prize_amount=prize_amount,
            currency=currency,
            winners_count=winners_count,
            duration_minutes=duration_minutes,
            strategy=strategy,
            description=description,
            photo_path=photo_path
        )
        
        # Сохраняем в активные
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        self.active_giveaways[giveaway_id] = {
            'id': giveaway_id,
            'creator_id': creator_id,
            'target_type': target_type,
            'target_id': target_id,
            'prize_amount': prize_amount,
            'currency': currency,
            'winners_count': winners_count,
            'duration_minutes': duration_minutes,
            'strategy': strategy,
            'description': description,
            'photo_path': photo_path,
            'start_time': datetime.now(),
            'end_time': end_time,
            'participants': set(),
            'message_id': None
        }
        
        # Отправляем сообщение о розыгрыше
        await self._send_giveaway_message(giveaway_id)
        
        # Запускаем таймер
        task = asyncio.create_task(self._giveaway_timer(giveaway_id))
        self.giveaway_tasks[giveaway_id] = task
        
        logger.info(f"Создан розыгрыш #{giveaway_id} для {target_type} {target_id}")
        return giveaway_id
    
    async def _send_giveaway_message(self, giveaway_id: int):
        """Отправка сообщения о розыгрыше в канал/чат"""
        giveaway = self.active_giveaways[giveaway_id]
        
        # Расчет суммы на победителя
        prize_per_winner = giveaway['prize_amount'] / giveaway['winners_count']
        
        # Получаем комиссию для целевого объекта
        commission_info = await self._get_commission(giveaway['target_type'], giveaway['target_id'])
        commission_amount = self._calculate_commission(prize_per_winner, commission_info)
        final_prize_per_winner = prize_per_winner - commission_amount
        
        # Формируем текст
        end_time_str = giveaway['end_time'].strftime("%d.%m.%Y %H:%M")
        time_left = self._format_time_left(giveaway['end_time'])
        
        text = f"🎉 <b>РОЗЫГРЫШ</b> 🎉\n\n"
        
        if giveaway['description']:
            text += f"📝 {giveaway['description']}\n\n"
        
        text += f"💰 <b>Общий призовой фонд:</b> {giveaway['prize_amount']} {giveaway['currency']}\n"
        text += f"🏆 <b>Количество победителей:</b> {giveaway['winners_count']}\n"
        text += f"💵 <b>Каждый победитель получит:</b> {final_prize_per_winner:.2f} {giveaway['currency']}\n"
        
        if commission_amount > 0:
            text += f"💼 <i>Комиссия: {commission_amount:.2f} {giveaway['currency']}</i>\n"
        
        text += f"\n⏰ <b>Окончание:</b> {end_time_str}\n"
        text += f"⏳ <b>Осталось:</b> {time_left}\n\n"
        text += f"👥 <b>Участников:</b> 0\n\n"
        text += f"🎯 <b>Стратегия выбора:</b> {self._get_strategy_name(giveaway['strategy'])}\n\n"
        text += "Нажмите кнопку ниже, чтобы участвовать!"
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="🎁 Участвовать в розыгрыше",
            url=f"https://t.me/{(await self.bot.me()).username}?start=join_{giveaway_id}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="📊 Участники: 0",
            callback_data=f"giveaway_info_{giveaway_id}"
        ))
        
        # Отправляем сообщение
        try:
            if giveaway['photo_path']:
                # С фото
                photo = FSInputFile(giveaway['photo_path'])
                message = await self.bot.send_photo(
                    chat_id=giveaway['target_id'],
                    photo=photo,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=keyboard.as_markup()
                )
            else:
                # Без фото
                message = await self.bot.send_message(
                    chat_id=giveaway['target_id'],
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard.as_markup()
                )
            
            # Сохраняем ID сообщения
            giveaway['message_id'] = message.message_id
            await self.db.update_giveaway_message_id(giveaway_id, message.message_id)
            
            logger.info(f"Сообщение о розыгрыше #{giveaway_id} отправлено")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о розыгрыше #{giveaway_id}: {e}")
    
    async def join_giveaway(self, giveaway_id: int, user_id: int) -> Dict:
        """Присоединение пользователя к розыгрышу"""
        if giveaway_id not in self.active_giveaways:
            return {'success': False, 'reason': 'not_found'}
        
        giveaway = self.active_giveaways[giveaway_id]
        
        # Проверка, не закончился ли розыгрыш
        if datetime.now() >= giveaway['end_time']:
            return {'success': False, 'reason': 'ended'}
        
        # Проверка, не участвует ли уже
        if user_id in giveaway['participants']:
            return {'success': False, 'reason': 'already_joined'}
        
        # Проверка подписки на канал/чат
        if not await self._check_subscription(user_id, giveaway['target_id']):
            return {'success': False, 'reason': 'not_subscribed'}
        
        # Добавляем участника
        giveaway['participants'].add(user_id)
        await self.db.add_participant(giveaway_id, user_id)
        await self.db.increment_participation(user_id)
        
        # Обновляем сообщение
        await self._update_giveaway_message(giveaway_id)
        
        logger.info(f"Пользователь {user_id} присоединился к розыгрышу #{giveaway_id}")
        
        return {
            'success': True,
            'participants_count': len(giveaway['participants']),
            'prize_per_winner': giveaway['prize_amount'] / giveaway['winners_count']
        }
    
    async def _update_giveaway_message(self, giveaway_id: int):
        """Обновление сообщения о розыгрыше"""
        giveaway = self.active_giveaways[giveaway_id]
        
        if not giveaway['message_id']:
            return
        
        prize_per_winner = giveaway['prize_amount'] / giveaway['winners_count']
        commission_info = await self._get_commission(giveaway['target_type'], giveaway['target_id'])
        commission_amount = self._calculate_commission(prize_per_winner, commission_info)
        final_prize_per_winner = prize_per_winner - commission_amount
        
        end_time_str = giveaway['end_time'].strftime("%d.%m.%Y %H:%M")
        time_left = self._format_time_left(giveaway['end_time'])
        participants_count = len(giveaway['participants'])
        
        text = f"🎉 <b>РОЗЫГРЫШ</b> 🎉\n\n"
        
        if giveaway['description']:
            text += f"📝 {giveaway['description']}\n\n"
        
        text += f"💰 <b>Общий призовой фонд:</b> {giveaway['prize_amount']} {giveaway['currency']}\n"
        text += f"🏆 <b>Количество победителей:</b> {giveaway['winners_count']}\n"
        text += f"💵 <b>Каждый победитель получит:</b> {final_prize_per_winner:.2f} {giveaway['currency']}\n"
        
        if commission_amount > 0:
            text += f"💼 <i>Комиссия: {commission_amount:.2f} {giveaway['currency']}</i>\n"
        
        text += f"\n⏰ <b>Окончание:</b> {end_time_str}\n"
        text += f"⏳ <b>Осталось:</b> {time_left}\n\n"
        text += f"👥 <b>Участников:</b> {participants_count}\n\n"
        text += f"🎯 <b>Стратегия выбора:</b> {self._get_strategy_name(giveaway['strategy'])}\n\n"
        text += "Нажмите кнопку ниже, чтобы участвовать!"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="🎁 Участвовать в розыгрыше",
            url=f"https://t.me/{(await self.bot.me()).username}?start=join_{giveaway_id}"
        ))
        keyboard.row(InlineKeyboardButton(
            text=f"📊 Участники: {participants_count}",
            callback_data=f"giveaway_info_{giveaway_id}"
        ))
        
        try:
            if giveaway['photo_path']:
                await self.bot.edit_message_caption(
                    chat_id=giveaway['target_id'],
                    message_id=giveaway['message_id'],
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=keyboard.as_markup()
                )
            else:
                await self.bot.edit_message_text(
                    chat_id=giveaway['target_id'],
                    message_id=giveaway['message_id'],
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard.as_markup()
                )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения розыгрыша #{giveaway_id}: {e}")
    
    async def _giveaway_timer(self, giveaway_id: int):
        """Таймер розыгрыша"""
        giveaway = self.active_giveaways[giveaway_id]
        
        # Периодически обновляем сообщение
        update_interval = 60  # каждую минуту
        
        while datetime.now() < giveaway['end_time']:
            time_left = (giveaway['end_time'] - datetime.now()).total_seconds()
            
            if time_left <= 0:
                break
            
            # Ждем до следующего обновления или до конца
            wait_time = min(update_interval, time_left)
            await asyncio.sleep(wait_time)
            
            # Обновляем сообщение, если розыгрыш еще активен
            if giveaway_id in self.active_giveaways:
                await self._update_giveaway_message(giveaway_id)
        
        # Завершаем розыгрыш
        await self._finish_giveaway(giveaway_id)
    
    async def _finish_giveaway(self, giveaway_id: int):
        """Завершение розыгрыша и выбор победителей"""
        if giveaway_id not in self.active_giveaways:
            return
        
        giveaway = self.active_giveaways[giveaway_id]
        participants = list(giveaway['participants'])
        
        logger.info(f"Завершение розыгрыша #{giveaway_id}, участников: {len(participants)}")
        
        if not participants:
            # Нет участников
            await self._send_no_winners_message(giveaway_id)
            await self.db.finish_giveaway(giveaway_id)
            del self.active_giveaways[giveaway_id]
            return
        
        # Выбираем победителей по стратегии
        winners = await self._select_winners(giveaway_id, participants)
        
        # Вычисляем выплаты
        prize_per_winner = giveaway['prize_amount'] / len(winners)
        commission_info = await self._get_commission(giveaway['target_type'], giveaway['target_id'])
        commission_amount = self._calculate_commission(prize_per_winner, commission_info)
        final_prize = prize_per_winner - commission_amount
        
        # Выплачиваем призы
        for winner_id in winners:
            await self.db.update_balance(winner_id, final_prize)
            await self.db.add_transaction(
                winner_id,
                final_prize,
                "win",
                f"Выигрыш в розыгрыше #{giveaway_id}"
            )
            await self.db.increment_wins(winner_id)
            await self.db.update_participant_winner(giveaway_id, winner_id)
            
            # Уведомляем победителя
            try:
                await self.bot.send_message(
                    winner_id,
                    f"🎉 <b>Поздравляем!</b>\n\n"
                    f"Вы выиграли в розыгрыше!\n"
                    f"💰 Приз: {final_prize:.2f} {giveaway['currency']}\n\n"
                    f"Средства зачислены на ваш баланс.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления победителя {winner_id}: {e}")
        
        # Записываем комиссию
        total_commission = commission_amount * len(winners)
        if total_commission > 0:
            await self.db.add_transaction(
                giveaway['creator_id'],
                total_commission,
                "commission",
                f"Комиссия с розыгрыша #{giveaway_id}"
            )
        
        # Отправляем сообщение о завершении
        await self._send_winners_message(giveaway_id, winners, final_prize)
        
        # Завершаем розыгрыш
        await self.db.finish_giveaway(giveaway_id)
        del self.active_giveaways[giveaway_id]
        
        logger.info(f"Розыгрыш #{giveaway_id} завершен, победителей: {len(winners)}")
    
    async def _select_winners(self, giveaway_id: int, participants: List[int]) -> List[int]:
        """Выбор победителей по стратегии"""
        giveaway = self.active_giveaways[giveaway_id]
        winners_count = min(giveaway['winners_count'], len(participants))
        
        if giveaway['strategy'] == 'random':
            # Случайный выбор
            return random.sample(participants, winners_count)
        
        elif giveaway['strategy'] == 'first':
            # Первые участники
            participants_with_time = await self.db.get_participants_with_time(giveaway_id)
            participants_with_time.sort(key=lambda x: x['joined_at'])
            return [p['user_id'] for p in participants_with_time[:winners_count]]
        
        elif giveaway['strategy'] == 'active':
            # Самые активные (по количеству участий)
            participants_data = []
            for user_id in participants:
                user = await self.db.get_user(user_id)
                participants_data.append({
                    'user_id': user_id,
                    'activity': user['giveaways_participated']
                })
            
            participants_data.sort(key=lambda x: x['activity'], reverse=True)
            return [p['user_id'] for p in participants_data[:winners_count]]
        
        else:
            # По умолчанию случайный
            return random.sample(participants, winners_count)
    
    async def _send_winners_message(self, giveaway_id: int, winners: List[int], prize_per_winner: float):
        """Отправка сообщения о победителях"""
        giveaway = self.active_giveaways.get(giveaway_id)
        if not giveaway:
            return
        
        winners_text = []
        for winner_id in winners:
            try:
                user = await self.bot.get_chat(winner_id)
                username = f"@{user.username}" if user.username else f"ID: {winner_id}"
                winners_text.append(username)
            except:
                winners_text.append(f"ID: {winner_id}")
        
        text = (
            f"🎊 <b>РОЗЫГРЫШ ЗАВЕРШЕН</b> 🎊\n\n"
            f"🏆 <b>Победители:</b>\n"
            f"{chr(10).join('🥇 ' + w for w in winners_text)}\n\n"
            f"💰 <b>Каждый получил:</b> {prize_per_winner:.2f} {giveaway['currency']}\n\n"
            f"Поздравляем победителей! 🎉"
        )
        
        try:
            await self.bot.send_message(
                chat_id=giveaway['target_id'],
                text=text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о победителях: {e}")
    
    async def _send_no_winners_message(self, giveaway_id: int):
        """Сообщение при отсутствии участников"""
        giveaway = self.active_giveaways.get(giveaway_id)
        if not giveaway:
            return
        
        text = (
            f"😔 <b>РОЗЫГРЫШ ЗАВЕРШЕН</b>\n\n"
            f"К сожалению, не было ни одного участника.\n"
            f"Розыгрыш отменен."
        )
        
        try:
            await self.bot.send_message(
                chat_id=giveaway['target_id'],
                text=text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об отсутствии победителей: {e}")
    
    async def _check_subscription(self, user_id: int, chat_id: str) -> bool:
        """Проверка подписки пользователя"""
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Ошибка проверки подписки: {e}")
            return False
    
    async def _get_commission(self, target_type: str, target_id: str) -> Dict:
        """Получение комиссии для цели"""
        if target_type == 'channel':
            channel = await self.db.get_channel(target_id)
            if channel:
                return {
                    'value': channel['commission'],
                    'type': channel['commission_type']
                }
        elif target_type == 'chat':
            chat_comm = await self.db.get_chat_commission(target_id)
            if chat_comm:
                return {
                    'value': chat_comm['value'],
                    'type': chat_comm['commission_type']
                }
        
        # По умолчанию 5%
        return {'value': 5.0, 'type': 'percent'}
    
    def _calculate_commission(self, amount: float, commission_info: Dict) -> float:
        """Расчет комиссии"""
        if commission_info['type'] == 'percent':
            return amount * (commission_info['value'] / 100)
        else:
            return commission_info['value']
    
    def _format_time_left(self, end_time: datetime) -> str:
        """Форматирование оставшегося времени"""
        delta = end_time - datetime.now()
        
        if delta.total_seconds() <= 0:
            return "Завершен"
        
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0:
            parts.append(f"{minutes}м")
        
        return " ".join(parts) if parts else "< 1м"
    
    def _get_strategy_name(self, strategy: str) -> str:
        """Название стратегии"""
        strategies = {
            'random': '🎲 Случайный выбор',
            'first': '⚡️ Первые участники',
            'active': '🔥 Самые активные'
        }
        return strategies.get(strategy, strategy)
    
    async def cancel_giveaway(self, giveaway_id: int, reason: str = "Отменен создателем") -> bool:
        """Отмена розыгрыша"""
        if giveaway_id not in self.active_giveaways:
            return False
        
        giveaway = self.active_giveaways[giveaway_id]
        
        # Останавливаем таймер
        if giveaway_id in self.giveaway_tasks:
            self.giveaway_tasks[giveaway_id].cancel()
            del self.giveaway_tasks[giveaway_id]
        
        # Уведомляем в канале/чате
        text = (
            f"❌ <b>РОЗЫГРЫШ ОТМЕНЕН</b>\n\n"
            f"Причина: {reason}\n\n"
            f"Приносим извинения за неудобства."
        )
        
        try:
            await self.bot.send_message(
                chat_id=giveaway['target_id'],
                text=text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об отмене: {e}")
        
        # Помечаем как отмененный в БД
        await self.db.cancel_giveaway(giveaway_id, reason)
        
        # Удаляем из активных
        del self.active_giveaways[giveaway_id]
        
        logger.info(f"Розыгрыш #{giveaway_id} отменен: {reason}")
        return True
    
    def get_active_giveaway(self, giveaway_id: int) -> Optional[Dict]:
        """Получить информацию об активном розыгрыше"""
        return self.active_giveaways.get(giveaway_id)
    
    def get_all_active_giveaways(self) -> List[Dict]:
        """Получить все активные розыгрыши"""
        return list(self.active_giveaways.values())