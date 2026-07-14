import asyncio
import logging
import random
import string
import sqlite3
import os
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.utils.markdown import hbold, hitalic, hcode, hblockquote

# ---------- Конфигурация ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8494220705:AAH68tF-kA6yqoxFDr0QSUZ3LlkadxZPSJw")
ADMIN_ID = int(os.getenv("ADMIN_ID", 8400055743))
BANNER_URL = "https://i.ibb.co/XfbYk9Vc/IMG-1254.jpg"
PORT = int(os.getenv("PORT", 8080))

# ---------- База данных ----------
class Database:
    def __init__(self, db_file="bot.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                requisites TEXT,
                referral_id INTEGER,
                language TEXT DEFAULT 'ru',
                successful_deals INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                creator_id INTEGER,
                partner_id INTEGER,
                currency TEXT,
                amount REAL,
                description TEXT,
                nft_link TEXT,
                status TEXT DEFAULT 'pending',
                memo TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                requisites TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                admin_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                from_user_id INTEGER,
                deal_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def create_user(self, user_id, username, first_name, referral_id=None):
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, referral_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, referral_id))
        self.conn.commit()

    def update_user(self, user_id, **kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()

    def get_user_balance(self, user_id):
        self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def add_balance(self, user_id, amount):
        self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def get_user_requisites(self, user_id):
        self.cursor.execute("SELECT requisites FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def set_requisites(self, user_id, requisites):
        self.cursor.execute("UPDATE users SET requisites = ? WHERE user_id = ?", (requisites, user_id))
        self.conn.commit()

    def create_deal(self, deal_id, creator_id, currency, amount, description, nft_link, memo):
        self.cursor.execute("""
            INSERT INTO deals (deal_id, creator_id, currency, amount, description, nft_link, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (deal_id, creator_id, currency, amount, description, nft_link, memo))
        self.conn.commit()
        return deal_id

    def get_deal(self, deal_id):
        self.cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        return self.cursor.fetchone()

    def get_deal_by_memo(self, memo):
        self.cursor.execute("SELECT * FROM deals WHERE memo = ?", (memo,))
        return self.cursor.fetchone()

    def update_deal(self, deal_id, **kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE deals SET {key} = ? WHERE deal_id = ?", (value, deal_id))
        self.conn.commit()

    def get_user_deals(self, user_id):
        self.cursor.execute("""
            SELECT * FROM deals WHERE creator_id = ? OR partner_id = ?
            ORDER BY created_at DESC
        """, (user_id, user_id))
        return self.cursor.fetchall()

    def get_successful_deals_count(self, user_id):
        self.cursor.execute("SELECT successful_deals FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def increment_successful_deals(self, user_id, count=1):
        self.cursor.execute("UPDATE users SET successful_deals = successful_deals + ? WHERE user_id = ?", (count, user_id))
        self.conn.commit()

    def create_withdraw_request(self, user_id, amount, requisites):
        self.cursor.execute("""
            INSERT INTO withdraw_requests (user_id, amount, requisites)
            VALUES (?, ?, ?)
        """, (user_id, amount, requisites))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_withdraw_requests(self, user_id=None, status=None):
        if user_id:
            self.cursor.execute("SELECT * FROM withdraw_requests WHERE user_id = ?", (user_id,))
        elif status:
            self.cursor.execute("SELECT * FROM withdraw_requests WHERE status = ?", (status,))
        else:
            self.cursor.execute("SELECT * FROM withdraw_requests")
        return self.cursor.fetchall()

    def update_withdraw_request(self, req_id, status):
        self.cursor.execute("UPDATE withdraw_requests SET status = ? WHERE id = ?", (status, req_id))
        self.conn.commit()

    def create_support_ticket(self, user_id, message):
        self.cursor.execute("""
            INSERT INTO support_tickets (user_id, message)
            VALUES (?, ?)
        """, (user_id, message))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_tickets(self, user_id=None, resolved=False):
        if user_id:
            self.cursor.execute("SELECT * FROM support_tickets WHERE user_id = ? AND resolved = ?", (user_id, resolved))
        else:
            self.cursor.execute("SELECT * FROM support_tickets WHERE resolved = ?", (resolved,))
        return self.cursor.fetchall()

    def resolve_ticket(self, ticket_id, admin_reply):
        self.cursor.execute("UPDATE support_tickets SET resolved = 1, admin_reply = ? WHERE id = ?", (admin_reply, ticket_id))
        self.conn.commit()

    def get_referral_bonuses(self, user_id):
        self.cursor.execute("SELECT * FROM referral_bonuses WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    def add_referral_bonus(self, user_id, amount, from_user_id, deal_id):
        self.cursor.execute("""
            INSERT INTO referral_bonuses (user_id, amount, from_user_id, deal_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, amount, from_user_id, deal_id))
        self.conn.commit()

    def close(self):
        self.conn.close()

# ---------- Состояния FSM ----------
class DealCreation(StatesGroup):
    currency = State()
    amount = State()
    description = State()
    nft_link = State()

class RequisitesEdit(StatesGroup):
    text = State()

class Withdraw(StatesGroup):
    amount = State()

class HostleBuyAdmin(StatesGroup):
    memo = State()

class RefAdmin(StatesGroup):
    deal_id = State()

class BoostSuccessAdmin(StatesGroup):
    user_id = State()
    count = State()

class AddBalanceAdmin(StatesGroup):
    user_id = State()
    amount = State()

class CompleteDealAdmin(StatesGroup):
    memo = State()

# ---------- Клавиатуры ----------
def main_menu(lang='ru'):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Мои реквизиты", callback_data="requisites"),
         InlineKeyboardButton(text="➕ Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
         InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
         InlineKeyboardButton(text="🌐 Язык", callback_data="language")],
        [InlineKeyboardButton(text="🛠 Техподдержка", callback_data="support")]
    ])
    return builder

def admin_panel():
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Ответить пользователю", callback_data="admin_chat"),
         InlineKeyboardButton(text="✅ Отметить оплату", callback_data="admin_hostlebuy")],
        [InlineKeyboardButton(text="❌ Уведомить о подарке", callback_data="admin_ref"),
         InlineKeyboardButton(text="⬆️ Накрутить сделки", callback_data="admin_boost")],
        [InlineKeyboardButton(text="➕ Добавить баланс", callback_data="admin_add_balance"),
         InlineKeyboardButton(text="📊 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="✅ Завершить сделку", callback_data="admin_complete_deal")],
        [InlineKeyboardButton(text="📖 Справка", callback_data="admin_help")]
    ])
    return builder

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def requisites_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Добавить/Изменить", callback_data="add_requisites")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

# ---------- Тексты с форматированием ----------
TEXTS = {
    'ru': {
        'welcome': "Добро пожаловать в GGSel! 🚀\n\n"
                   "Ваш надёжный P2P-гарант:\n"
                   "1. Автоматические сделки с NFT и валютами\n"
                   "2. Полная защита обеих сторон\n"
                   "3. Реферальная программа — 50% от комиссии\n"
                   "4. Передача товаров происходит напрямую между участниками сделки.\n"
                   "   В случае возникновения вопросов обращайтесь в техподдержку.",
        'requisites': "Ваши реквизиты:\n{requisites}",
        'no_requisites': "У вас пока нет реквизитов. Добавьте их.",
        'enter_requisites': "Введите текст ваших реквизитов (например, номер карты или кошелька):",
        'requisites_saved': "Реквизиты успешно сохранены!",
        'choose_currency': "Выберите валюту оплаты:",
        'enter_amount': "Введите сумму сделки:",
        'enter_description': "Введите описание товара:",
        'enter_nft_link': "Введите ссылку на NFT (или другой товар):",
        'deal_created': "✅ <b>Сделка создана!</b>\n\n"
                        f"{hblockquote('Код сделки: {memo}')}\n"
                        f"{hblockquote('Ссылка для приглашения:')}\n"
                        "https://t.me/{bot_username}?start=deal_{memo}\n\n"
                        "<i>Ожидайте, пока партнер присоединится.</i>",
        'deal_joined': "✅ <b>Вы присоединились к сделке!</b>\n\n"
                       f"{hblockquote('Важно: передача товара осуществляется продавцом покупателю после подтверждения оплаты.')}\n"
                       "<i>Ожидайте, пока администратор отметит оплату и завершит сделку.</i>",
        'balance': "💰 <b>Ваш баланс:</b> {balance} TON\n\n"
                   "✅ <b>Успешных сделок:</b> {successful_deals}",
        'withdraw_info': "Для вывода необходимо завершить минимум 2 сделки. У вас: {successful_deals}",
        'enter_withdraw_amount': "Введите сумму для вывода (в TON):",
        'withdraw_request_sent': "Заявка на вывод отправлена администратору.",
        'not_enough_deals': "❌ У вас недостаточно завершенных сделок для вывода. Требуется: 2",
        'referral_info': "🔗 <b>Ваша реферальная ссылка:</b>\n"
                         "https://t.me/{bot_username}?start=ref_{user_id}\n\n"
                         "За каждого приглашенного вы получаете <b>1 TON</b> бонуса после его первой успешной сделки.",
        'support': "Напишите ваше сообщение в поддержку. Мы ответим вам как можно скорее.",
        'support_sent': "✅ Ваше сообщение отправлено в поддержку.",
        'language_changed': "🌐 Язык изменен на русский.",
        'my_deals': "📋 <b>Ваши сделки:</b>\n{deals_list}",
        'no_deals': "У вас нет сделок.",
        'deal_status_pending': "⏳ Ожидание партнера",
        'deal_status_active': "🔄 Активна (ожидает оплаты)",
        'deal_status_paid': "💳 Оплачена",
        'deal_status_completed': "✅ Завершена",
        'deal_status_cancelled': "❌ Отменена",
        'admin_panel': "⚙️ <b>Админ-панель</b>",
        'admin_help': "📖 <b>Команды администратора:</b>\n\n"
                      "/chat @username текст — ответить пользователю\n"
                      "/hostlebuy memo — отметить оплату\n"
                      "/ref deal_id — уведомление о подарке\n"
                      "/boost_success user_id count — накрутить успешные сделки\n"
                      "/add_balance user_id amount — добавить баланс\n"
                      "/complete_deal memo — завершить сделку\n"
                      "/gtteam — показать эту справку",
        'enter_username': "Введите @username пользователя для ответа:",
        'enter_reply_message': "Введите текст ответа:",
        'reply_sent': "✅ Ответ отправлен.",
        'enter_memo': "Введите код сделки (memo) для отметки оплаты:",
        'payment_marked': "✅ Сделка {memo} отмечена как оплаченная.",
        'enter_deal_id_for_ref': "Введите ID сделки для отправки уведомления о подарке:",
        'ref_sent': "✅ Уведомление отправлено обоим участникам.",
        'enter_user_id_boost': "Введите ID пользователя для накрутки:",
        'enter_boost_count': "Введите количество сделок для накрутки:",
        'boost_success': "✅ Успешные сделки пользователя {user_id} увеличены на {count}.",
        'enter_user_id_add_balance': "Введите ID пользователя для добавления баланса:",
        'enter_amount_add_balance': "Введите сумму для добавления:",
        'balance_added': "✅ Баланс пользователя {user_id} увеличен на {amount}.",
        'balance_notification': "💎 <b>Ваш баланс пополнен!</b>\n\n"
                                f"{hblockquote('Сумма: {amount} TON')}\n"
                                "<i>Текущий баланс можно проверить в разделе «Баланс».</i>",
        'withdraw_requests': "📊 <b>Заявки на вывод:</b>\n{requests}",
        'no_withdraw_requests': "Нет заявок на вывод.",
        'admin_chat_instruction': "Используйте команду /chat @username текст для ответа.",
        'enter_memo_complete': "Введите код сделки (memo) для завершения:",
        'deal_completed': "✅ Сделка {memo} успешно завершена!",
        'deal_not_found': "❌ Сделка не найдена.",
        'deal_not_active': "❌ Сделка неактивна.",
        'not_enough_balance': "❌ У покупателя недостаточно средств на балансе.",
        'support_reply': "✉️ <b>Ответ поддержки:</b>\n\n{reply}",
        'deal_completed_user': "✅ <b>Сделка {memo} успешно завершена!</b>\n\n"
                               f"{hblockquote('Средства зачислены на ваш баланс.')}\n"
                               "<i>Спасибо, что пользуетесь GGSel!</i>",
        'deal_completed_buyer': "✅ <b>Сделка {memo} успешно завершена!</b>\n\n"
                                f"{hblockquote('Товар передан продавцом. Спасибо за покупку!')}\n"
                                "<i>Если у вас возникли вопросы, обратитесь в техподдержку.</i>",
    },
    'en': {
        'welcome': "Welcome to GGSel! 🚀\n\n"
                   "Your reliable P2P guarantor:\n"
                   "1. Automatic deals with NFT and currencies\n"
                   "2. Full protection of both parties\n"
                   "3. Referral program — 50% of commission\n"
                   "4. Goods are transferred directly between deal participants.\n"
                   "   If you have any questions, contact support.",
        'requisites': "Your requisites:\n{requisites}",
        'no_requisites': "You have no requisites yet. Add them.",
        'enter_requisites': "Enter your requisites (e.g., card number or wallet):",
        'requisites_saved': "Requisites saved successfully!",
        'choose_currency': "Choose payment currency:",
        'enter_amount': "Enter deal amount:",
        'enter_description': "Enter product description:",
        'enter_nft_link': "Enter NFT link (or other product):",
        'deal_created': "✅ <b>Deal created!</b>\n\n"
                        f"{hblockquote('Deal code: {memo}')}\n"
                        f"{hblockquote('Invitation link:')}\n"
                        "https://t.me/{bot_username}?start=deal_{memo}\n\n"
                        "<i>Wait for partner to join.</i>",
        'deal_joined': "✅ <b>You joined the deal!</b>\n\n"
                       f"{hblockquote('Important: goods are transferred by the seller to the buyer after payment confirmation.')}\n"
                       "<i>Wait for admin to mark payment and complete the deal.</i>",
        'balance': "💰 <b>Your balance:</b> {balance} TON\n\n"
                   "✅ <b>Successful deals:</b> {successful_deals}",
        'withdraw_info': "You need at least 2 completed deals to withdraw. You have: {successful_deals}",
        'enter_withdraw_amount': "Enter amount to withdraw (in TON):",
        'withdraw_request_sent': "Withdrawal request sent to admin.",
        'not_enough_deals': "❌ You don't have enough completed deals to withdraw. Required: 2",
        'referral_info': "🔗 <b>Your referral link:</b>\n"
                         "https://t.me/{bot_username}?start=ref_{user_id}\n\n"
                         "For each invited user you get <b>1 TON</b> bonus after their first successful deal.",
        'support': "Write your message to support. We will reply as soon as possible.",
        'support_sent': "✅ Your message has been sent to support.",
        'language_changed': "🌐 Language changed to English.",
        'my_deals': "📋 <b>Your deals:</b>\n{deals_list}",
        'no_deals': "You have no deals.",
        'deal_status_pending': "⏳ Waiting for partner",
        'deal_status_active': "🔄 Active (awaiting payment)",
        'deal_status_paid': "💳 Paid",
        'deal_status_completed': "✅ Completed",
        'deal_status_cancelled': "❌ Cancelled",
        'admin_panel': "⚙️ <b>Admin panel</b>",
        'admin_help': "📖 <b>Admin commands:</b>\n\n"
                      "/chat @username text — reply to user\n"
                      "/hostlebuy memo — mark payment\n"
                      "/ref deal_id — gift notification\n"
                      "/boost_success user_id count — boost successful deals\n"
                      "/add_balance user_id amount — add balance\n"
                      "/complete_deal memo — complete deal\n"
                      "/gtteam — show this help",
        'enter_username': "Enter @username of user to reply:",
        'enter_reply_message': "Enter reply text:",
        'reply_sent': "✅ Reply sent.",
        'enter_memo': "Enter deal memo to mark as paid:",
        'payment_marked': "✅ Deal {memo} marked as paid.",
        'enter_deal_id_for_ref': "Enter deal ID to send gift notification:",
        'ref_sent': "✅ Notification sent to both participants.",
        'enter_user_id_boost': "Enter user ID to boost:",
        'enter_boost_count': "Enter number of deals to boost:",
        'boost_success': "✅ Successful deals for user {user_id} increased by {count}.",
        'enter_user_id_add_balance': "Enter user ID to add balance:",
        'enter_amount_add_balance': "Enter amount to add:",
        'balance_added': "✅ Balance for user {user_id} increased by {amount}.",
        'balance_notification': "💎 <b>Your balance has been replenished!</b>\n\n"
                                f"{hblockquote('Amount: {amount} TON')}\n"
                                "<i>You can check your current balance in the «Balance» section.</i>",
        'withdraw_requests': "📊 <b>Withdrawal requests:</b>\n{requests}",
        'no_withdraw_requests': "No withdrawal requests.",
        'admin_chat_instruction': "Use command /chat @username text to reply.",
        'enter_memo_complete': "Enter deal memo to complete:",
        'deal_completed': "✅ Deal {memo} completed successfully!",
        'deal_not_found': "❌ Deal not found.",
        'deal_not_active': "❌ Deal is not active.",
        'not_enough_balance': "❌ Buyer has insufficient balance.",
        'support_reply': "✉️ <b>Support reply:</b>\n\n{reply}",
        'deal_completed_user': "✅ <b>Deal {memo} completed successfully!</b>\n\n"
                               f"{hblockquote('Funds have been credited to your balance.')}\n"
                               "<i>Thank you for using GGSel!</i>",
        'deal_completed_buyer': "✅ <b>Deal {memo} completed successfully!</b>\n\n"
                                f"{hblockquote('The goods have been transferred by the seller. Thanks for your purchase!')}\n"
                                "<i>If you have any questions, contact support.</i>",
    }
}

# ---------- Вспомогательные функции ----------
db = Database()
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_text(user_id, key, **kwargs):
    user = db.get_user(user_id)
    lang = user[6] if user else 'ru'
    text = TEXTS.get(lang, TEXTS['ru']).get(key, key)
    return text.format(**kwargs) if kwargs else text

def generate_memo():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

async def send_banner_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    await bot.send_photo(chat_id, photo=BANNER_URL, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)

# ---------- Обработчики ----------

# /start
@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    args = message.text.split()
    ref_id = None
    if len(args) > 1:
        param = args[1]
        if param.startswith('ref_'):
            ref_id = int(param.split('_')[1])
        elif param.startswith('deal_'):
            memo = param.split('_')[1]
            deal = db.get_deal_by_memo(memo)
            if deal:
                if deal[1] != user_id and deal[2] is None:
                    if db.get_user_balance(user_id) < deal[4]:
                        await message.answer(get_text(user_id, 'not_enough_balance'))
                        return
                    db.update_deal(deal[0], partner_id=user_id, status='active')
                    # Отправляем красивое сообщение о присоединении
                    await send_banner_message(user_id, get_text(user_id, 'deal_joined'), reply_markup=main_menu(get_text(user_id, 'lang')))
                else:
                    await message.answer("❌ Эта сделка уже недоступна.")
            else:
                await message.answer("❌ Сделка не найдена.")
            return

    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id, username, first_name, ref_id)
        if ref_id:
            db.add_balance(ref_id, 1)
            db.add_referral_bonus(ref_id, 1, user_id, None)
    else:
        db.update_user(user_id, username=username, first_name=first_name)

    text = get_text(user_id, 'welcome')
    await send_banner_message(user_id, text, reply_markup=main_menu(get_text(user_id, 'lang')))

# Назад в меню
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    text = get_text(user_id, 'welcome')
    await callback.message.delete()
    await send_banner_message(user_id, text, reply_markup=main_menu(get_text(user_id, 'lang')))
    await callback.answer()

# Мои реквизиты
@dp.callback_query(F.data == "requisites")
async def requisites_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    req = db.get_user_requisites(user_id)
    if req:
        text = get_text(user_id, 'requisites', requisites=hblockquote(req))
    else:
        text = get_text(user_id, 'no_requisites')
    await callback.message.delete()
    await send_banner_message(user_id, text, reply_markup=requisites_menu())
    await callback.answer()

@dp.callback_query(F.data == "add_requisites")
async def add_requisites(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RequisitesEdit.text)
    await callback.message.delete()
    await send_banner_message(callback.from_user.id, get_text(callback.from_user.id, 'enter_requisites'))
    await callback.answer()

@dp.message(StateFilter(RequisitesEdit.text))
async def requisites_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    db.set_requisites(user_id, message.text)
    await state.clear()
    await send_banner_message(user_id, get_text(user_id, 'requisites_saved'), reply_markup=main_menu(get_text(user_id, 'lang')))

# Создать сделку
@dp.callback_query(F.data == "create_deal")
async def create_deal_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealCreation.currency)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TON", callback_data="currency_ton"),
         InlineKeyboardButton(text="USDT", callback_data="currency_usdt")],
        [InlineKeyboardButton(text="RUB", callback_data="currency_rub")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await callback.message.delete()
    await send_banner_message(callback.from_user.id, get_text(callback.from_user.id, 'choose_currency'), reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("currency_"))
async def currency_chosen(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[1].upper()
    await state.update_data(currency=currency)
    await state.set_state(DealCreation.amount)
    await callback.message.delete()
    await send_banner_message(callback.from_user.id, get_text(callback.from_user.id, 'enter_amount'))
    await callback.answer()

@dp.message(StateFilter(DealCreation.amount))
async def amount_entered(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    await state.update_data(amount=amount)
    await state.set_state(DealCreation.description)
    await send_banner_message(message.from_user.id, get_text(message.from_user.id, 'enter_description'))

@dp.message(StateFilter(DealCreation.description))
async def description_entered(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(DealCreation.nft_link)
    await send_banner_message(message.from_user.id, get_text(message.from_user.id, 'enter_nft_link'))

@dp.message(StateFilter(DealCreation.nft_link))
async def nft_link_entered(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    deal_id = generate_memo()
    db.create_deal(deal_id, user_id, data['currency'], data['amount'], data['description'], message.text, deal_id)
    await state.clear()
    bot_username = (await bot.me()).username
    text = get_text(user_id, 'deal_created', memo=deal_id, bot_username=bot_username)
    await send_banner_message(user_id, text, reply_markup=main_menu(get_text(user_id, 'lang')))

# Баланс
@dp.callback_query(F.data == "balance")
async def balance_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = db.get_user_balance(user_id)
    successful_deals = db.get_successful_deals_count(user_id)
    text = get_text(user_id, 'balance', balance=balance, successful_deals=successful_deals)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit"),
         InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await callback.message.delete()
    await send_banner_message(user_id, text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "deposit")
async def deposit_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    text = f"💳 <b>Пополнение баланса</b>\n\nПереведите TON на кошелек:\n<code>UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA</code>\n\nВ комментарии укажите ваш ID: <b>{user_id}</b>\n\nПосле зачисления средства будут добавлены вручную администратором."
    await callback.message.delete()
    await send_banner_message(user_id, text, reply_markup=back_button())
    await callback.answer()

@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    successful_deals = db.get_successful_deals_count(user_id)
    if successful_deals < 2:
        await callback.message.delete()
        await send_banner_message(user_id, get_text(user_id, 'not_enough_deals'), reply_markup=back_button())
        await callback.answer()
        return
    await state.set_state(Withdraw.amount)
    await callback.message.delete()
    await send_banner_message(user_id, get_text(user_id, 'enter_withdraw_amount'))
    await callback.answer()

@dp.message(StateFilter(Withdraw.amount))
async def withdraw_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    balance = db.get_user_balance(user_id)
    if amount > balance:
        await message.answer("❌ Недостаточно средств.")
        return
    requisites = db.get_user_requisites(user_id)
    if not requisites:
        await message.answer("❌ У вас не добавлены реквизиты для вывода. Сначала добавьте их в разделе 'Мои реквизиты'.")
        return
    db.create_withdraw_request(user_id, amount, requisites)
    await state.clear()
    await send_banner_message(user_id, get_text(user_id, 'withdraw_request_sent'), reply_markup=main_menu(get_text(user_id, 'lang')))

# Мои сделки
@dp.callback_query(F.data == "my_deals")
async def my_deals_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    deals = db.get_user_deals(user_id)
    if not deals:
        text = get_text(user_id, 'no_deals')
    else:
        lines = []
        for deal in deals:
            status_map = {
                'pending': get_text(user_id, 'deal_status_pending'),
                'active': get_text(user_id, 'deal_status_active'),
                'paid': get_text(user_id, 'deal_status_paid'),
                'completed': get_text(user_id, 'deal_status_completed'),
                'cancelled': get_text(user_id, 'deal_status_cancelled'),
            }
            status = status_map.get(deal[6], deal[6])
            lines.append(f"<b>{deal[0]}</b> — {deal[3]} {deal[4]} — {status}")
        text = get_text(user_id, 'my_deals', deals_list='\n'.join(lines))
    await callback.message.delete()
    await send_banner_message(user_id, text, reply_markup=back_button())
    await callback.answer()

# Рефералы
@dp.callback_query(F.data == "referrals")
async def referrals_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await bot.me()).username
    text = get_text(user_id, 'referral_info', bot_username=bot_username, user_id=user_id)
    await callback.message.delete()
    await send_banner_message(user_id, text, reply_markup=back_button())
    await callback.answer()

# Язык
@dp.callback_query(F.data == "language")
async def language_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await callback.message.delete()
    await send_banner_message(user_id, "🌐 Выберите язык / Choose language:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("lang_"))
async def lang_chosen(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    db.update_user(user_id, language=lang)
    text = get_text(user_id, 'language_changed')
    await callback.message.delete()
    await send_banner_message(user_id, text, reply_markup=main_menu(lang))
    await callback.answer()

# Техподдержка
@dp.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state("support_message")
    await callback.message.delete()
    await send_banner_message(callback.from_user.id, get_text(callback.from_user.id, 'support'), reply_markup=back_button())
    await callback.answer()

@dp.message(StateFilter("support_message"))
async def support_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    db.create_support_ticket(user_id, text)
    await bot.send_message(ADMIN_ID, f"📩 Новое обращение от {user_id} (@{message.from_user.username}):\n\n{text}")
    await state.clear()
    await send_banner_message(user_id, get_text(user_id, 'support_sent'), reply_markup=main_menu(get_text(user_id, 'lang')))

# ---------- Админ-панель ----------
@dp.message(Command("wrteam"))
async def admin_panel_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.delete()
    await send_banner_message(message.from_user.id, get_text(ADMIN_ID, 'admin_panel'), reply_markup=admin_panel())

@dp.callback_query(F.data == "admin_help")
async def admin_help(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'admin_help'), reply_markup=back_button())
    await callback.answer()

@dp.callback_query(F.data == "admin_chat")
async def admin_chat_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'admin_chat_instruction'), reply_markup=back_button())
    await callback.answer()

@dp.message(Command("chat"))
async def chat_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Использование: /chat @username текст")
        return
    username = parts[1].lstrip('@')
    text = parts[2]
    try:
        chat = await bot.get_chat(username)
        user_id = chat.id
        tickets = db.get_tickets(user_id, resolved=False)
        if tickets:
            ticket = tickets[-1]
            db.resolve_ticket(ticket[0], text)
        await bot.send_message(user_id, get_text(user_id, 'support_reply', reply=text))
        await message.answer("✅ Сообщение отправлено.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# hostlebuy
@dp.callback_query(F.data == "admin_hostlebuy")
async def admin_hostlebuy_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(HostleBuyAdmin.memo)
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'enter_memo'))
    await callback.answer()

@dp.message(StateFilter(HostleBuyAdmin.memo))
async def hostlebuy_memo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    memo = message.text.strip()
    deal = db.get_deal_by_memo(memo)
    if not deal:
        await message.answer(get_text(ADMIN_ID, 'deal_not_found'))
        return
    if deal[6] not in ('active', 'pending'):
        await message.answer(get_text(ADMIN_ID, 'deal_not_active'))
        return
    db.update_deal(deal[0], status='paid')
    creator_id, partner_id = deal[1], deal[2]
    if creator_id:
        await bot.send_message(creator_id, f"✅ Ваша сделка {memo} отмечена как оплаченная. Ожидайте завершения.")
    if partner_id:
        await bot.send_message(partner_id, f"✅ Сделка {memo} отмечена как оплаченная. Подтвердите получение товара.")
    await message.answer(get_text(ADMIN_ID, 'payment_marked', memo=memo))
    await state.clear()

# ref
@dp.callback_query(F.data == "admin_ref")
async def admin_ref_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(RefAdmin.deal_id)
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'enter_deal_id_for_ref'))
    await callback.answer()

@dp.message(StateFilter(RefAdmin.deal_id))
async def ref_deal_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    deal_id = message.text.strip()
    deal = db.get_deal(deal_id)
    if not deal:
        await message.answer(get_text(ADMIN_ID, 'deal_not_found'))
        return
    creator_id, partner_id = deal[1], deal[2]
    if creator_id:
        await bot.send_message(creator_id, f"❌ Менеджер @GGselSupp не обнаружил подарок по сделке {deal_id}. Обратитесь в поддержку.")
    if partner_id:
        await bot.send_message(partner_id, f"❌ Менеджер @GGselSupp не обнаружил подарок по сделке {deal_id}. Обратитесь в поддержку.")
    await message.answer(get_text(ADMIN_ID, 'ref_sent'))
    await state.clear()

# boost_success
@dp.callback_query(F.data == "admin_boost")
async def admin_boost_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(BoostSuccessAdmin.user_id)
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'enter_user_id_boost'))
    await callback.answer()

@dp.message(StateFilter(BoostSuccessAdmin.user_id))
async def boost_user_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Введите корректный ID.")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(BoostSuccessAdmin.count)
    await message.answer(get_text(ADMIN_ID, 'enter_boost_count'))

@dp.message(StateFilter(BoostSuccessAdmin.count))
async def boost_count(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        count = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    data = await state.get_data()
    user_id = data['user_id']
    db.increment_successful_deals(user_id, count)
    await message.answer(get_text(ADMIN_ID, 'boost_success', user_id=user_id, count=count))
    await state.clear()

# add_balance (исправлено: добавлено уведомление пользователю)
@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(AddBalanceAdmin.user_id)
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'enter_user_id_add_balance'))
    await callback.answer()

@dp.message(StateFilter(AddBalanceAdmin.user_id))
async def add_balance_user_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Введите корректный ID.")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(AddBalanceAdmin.amount)
    await message.answer(get_text(ADMIN_ID, 'enter_amount_add_balance'))

@dp.message(StateFilter(AddBalanceAdmin.amount))
async def add_balance_amount(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    data = await state.get_data()
    user_id = data['user_id']
    db.add_balance(user_id, amount)
    # Отправляем уведомление пользователю
    user_text = get_text(user_id, 'balance_notification', amount=amount)
    await bot.send_message(user_id, user_text, parse_mode='HTML')
    await message.answer(get_text(ADMIN_ID, 'balance_added', user_id=user_id, amount=amount))
    await state.clear()

# complete_deal (исправлено: улучшены уведомления)
@dp.callback_query(F.data == "admin_complete_deal")
async def admin_complete_deal_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(CompleteDealAdmin.memo)
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'enter_memo_complete'))
    await callback.answer()

@dp.message(StateFilter(CompleteDealAdmin.memo))
async def complete_deal_memo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    memo = message.text.strip()
    deal = db.get_deal_by_memo(memo)
    if not deal:
        await message.answer(get_text(ADMIN_ID, 'deal_not_found'))
        return
    if deal[6] != 'paid':
        await message.answer("❌ Сделка должна быть сначала отмечена как оплаченная (/hostlebuy).")
        return

    creator_id = deal[1]
    partner_id = deal[2]
    amount = deal[4]

    if partner_id and db.get_user_balance(partner_id) < amount:
        await message.answer(get_text(ADMIN_ID, 'not_enough_balance'))
        return

    # Списание с покупателя и зачисление продавцу
    if partner_id:
        db.add_balance(partner_id, -amount)
    if creator_id:
        db.add_balance(creator_id, amount)

    # Увеличиваем счетчик успешных сделок
    if creator_id:
        db.increment_successful_deals(creator_id)
    if partner_id:
        db.increment_successful_deals(partner_id)

    # Реферальный бонус (50% от комиссии 5%)
    commission_rate = 0.05
    ref_bonus_rate = 0.5
    bonus = amount * commission_rate * ref_bonus_rate
    if creator_id:
        creator = db.get_user(creator_id)
        if creator and creator[4]:
            referrer_id = creator[4]
            db.add_balance(referrer_id, bonus)
            db.add_referral_bonus(referrer_id, bonus, creator_id, deal[0])

    db.update_deal(deal[0], status='completed', completed_at=datetime.now().isoformat())
    await message.answer(get_text(ADMIN_ID, 'deal_completed', memo=memo))

    # Уведомления участникам (красиво оформленные)
    if creator_id:
        await bot.send_message(creator_id, get_text(creator_id, 'deal_completed_user', memo=memo), parse_mode='HTML')
    if partner_id:
        await bot.send_message(partner_id, get_text(partner_id, 'deal_completed_buyer', memo=memo), parse_mode='HTML')
    await state.clear()

# Withdraw requests (просмотр)
@dp.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    requests = db.get_withdraw_requests(status='pending')
    if not requests:
        text = get_text(ADMIN_ID, 'no_withdraw_requests')
    else:
        lines = []
        for req in requests:
            lines.append(f"<b>ID заявки:</b> {req[0]}, <b>Пользователь:</b> {req[1]}, <b>Сумма:</b> {req[2]}, <b>Реквизиты:</b> {req[3]}")
        text = get_text(ADMIN_ID, 'withdraw_requests', requests='\n'.join(lines))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="approve_withdraw"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data="reject_withdraw")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, text, reply_markup=keyboard)
    await callback.answer()

# Обработка подтверждения/отклонения заявок
@dp.callback_query(F.data == "approve_withdraw")
async def approve_withdraw(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, "Введите ID заявки для подтверждения:")
    await state.set_state("approve_withdraw_id")
    await callback.answer()

@dp.callback_query(F.data == "reject_withdraw")
async def reject_withdraw(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.delete()
    await send_banner_message(ADMIN_ID, "Введите ID заявки для отклонения:")
    await state.set_state("reject_withdraw_id")
    await callback.answer()

@dp.message(StateFilter("approve_withdraw_id"))
async def approve_withdraw_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        req_id = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    db.update_withdraw_request(req_id, 'approved')
    await message.answer(f"✅ Заявка {req_id} подтверждена.")
    await state.clear()

@dp.message(StateFilter("reject_withdraw_id"))
async def reject_withdraw_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        req_id = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    db.update_withdraw_request(req_id, 'rejected')
    await message.answer(f"❌ Заявка {req_id} отклонена.")
    await state.clear()

# /gtteam - справка
@dp.message(Command("gtteam"))
async def gtteam_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await send_banner_message(ADMIN_ID, get_text(ADMIN_ID, 'admin_help'), reply_markup=back_button())

# ---------- Веб-сервер для Render ----------
async def handle_health(request):
    return web.Response(text="Bot is running")

def start_web():
    app = web.Application()
    app.router.add_get('/', handle_health)
    web.run_app(app, host='0.0.0.0', port=PORT)

# ---------- Запуск ----------
async def main():
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.to_thread(start_web))
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
