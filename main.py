import asyncio
import logging
import random
import string
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, PhotoSize
from aiogram.utils.markdown import hbold, hitalic, hcode, hunderline, hblockquote

import config
from database import Database
import keyboards as kb
from states.forms import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()

# Баннер
BANNER_URL = "https://i.ibb.co/XfbYk9Vc/IMG-1254.jpg"

# Тексты на разных языках
TEXTS = {
    'ru': {
        'welcome': "Добро пожаловать в GGSel! 🚀\n\nВаш надёжный P2P-гарант:\n1. Автоматические сделки с NFT и валютами\n2. Полная защита обеих сторон\n3. Реферальная программа — 50% от комиссии\n4. Передача товаров через менеджера: @GGselSupp",
        'requisites': "Ваши реквизиты:\n{requisites}",
        'no_requisites': "У вас пока нет реквизитов. Добавьте их.",
        'enter_requisites': "Введите текст ваших реквизитов (например, номер карты или кошелька):",
        'requisites_saved': "Реквизиты успешно сохранены!",
        'choose_currency': "Выберите валюту оплаты:",
        'enter_amount': "Введите сумму сделки:",
        'enter_description': "Введите описание товара:",
        'enter_nft_link': "Введите ссылку на NFT (или другой товар):",
        'deal_created': "Сделка создана!\n\nКод сделки: {memo}\nСсылка для приглашения: https://t.me/{bot_username}?start=deal_{memo}\n\nОжидайте, пока партнер присоединится.",
        'balance': "Ваш баланс: {balance} TON\n\nУспешных сделок: {successful_deals}",
        'withdraw_info': "Для вывода необходимо завершить минимум 2 сделки. У вас: {successful_deals}",
        'enter_withdraw_amount': "Введите сумму для вывода (в TON):",
        'withdraw_request_sent': "Заявка на вывод отправлена администратору.",
        'not_enough_deals': "У вас недостаточно завершенных сделок для вывода. Требуется: 2",
        'referral_info': "Ваша реферальная ссылка:\nhttps://t.me/{bot_username}?start=ref_{user_id}\n\nЗа каждого приглашенного вы получаете бонус 1 TON после его первой успешной сделки.",
        'support': "Напишите ваше сообщение в поддержку. Мы ответим вам как можно скорее.",
        'support_sent': "Ваше сообщение отправлено в поддержку.",
        'language_changed': "Язык изменен на русский.",
        'back': "Назад",
        'my_deals': "Ваши сделки:\n{deals_list}",
        'no_deals': "У вас нет сделок.",
        'deal_status_pending': "Ожидание партнера",
        'deal_status_active': "Активна (ожидает оплаты)",
        'deal_status_paid': "Оплачена",
        'deal_status_completed': "Завершена",
        'deal_status_cancelled': "Отменена",
        'admin_panel': "Админ-панель",
        'admin_help': "Команды администратора:\n/chat @username текст - ответить пользователю\n/hostlebuy memo - отметить оплату\n/ref deal_id - отправить уведомление о подарке\n/boost_success user_id count - накрутить успешные сделки\n/add_balance user_id amount - добавить баланс\n/gtteam - показать справку",
        'enter_username': "Введите @username пользователя для ответа:",
        'enter_reply_message': "Введите текст ответа:",
        'reply_sent': "Ответ отправлен.",
        'enter_memo': "Введите код сделки (memo) для отметки оплаты:",
        'payment_marked': "Сделка {memo} отмечена как оплаченная.",
        'enter_deal_id_for_ref': "Введите ID сделки для отправки уведомления о подарке:",
        'ref_sent': "Уведомление отправлено обоим участникам.",
        'enter_user_id_boost': "Введите ID пользователя для накрутки:",
        'enter_boost_count': "Введите количество сделок для накрутки:",
        'boost_success': "Успешные сделки пользователя {user_id} увеличены на {count}.",
        'enter_user_id_add_balance': "Введите ID пользователя для добавления баланса:",
        'enter_amount_add_balance': "Введите сумму для добавления:",
        'balance_added': "Баланс пользователя {user_id} увеличен на {amount}.",
        'withdraw_requests': "Заявки на вывод:\n{requests}",
        'no_withdraw_requests': "Нет заявок на вывод.",
        'admin_chat_instruction': "Используйте команду /chat @username текст для ответа.",
    },
    'en': {
        'welcome': "Welcome to GGSel! 🚀\n\nYour reliable P2P guarantor:\n1. Automatic deals with NFT and currencies\n2. Full protection of both parties\n3. Referral program — 50% of commission\n4. Transfer of goods via manager: @GGselSupp",
        'requisites': "Your requisites:\n{requisites}",
        'no_requisites': "You have no requisites yet. Add them.",
        'enter_requisites': "Enter your requisites (e.g., card number or wallet):",
        'requisites_saved': "Requisites saved successfully!",
        'choose_currency': "Choose payment currency:",
        'enter_amount': "Enter deal amount:",
        'enter_description': "Enter product description:",
        'enter_nft_link': "Enter NFT link (or other product):",
        'deal_created': "Deal created!\n\nDeal code: {memo}\nInvitation link: https://t.me/{bot_username}?start=deal_{memo}\n\nWait for partner to join.",
        'balance': "Your balance: {balance} TON\n\nSuccessful deals: {successful_deals}",
        'withdraw_info': "You need at least 2 completed deals to withdraw. You have: {successful_deals}",
        'enter_withdraw_amount': "Enter amount to withdraw (in TON):",
        'withdraw_request_sent': "Withdrawal request sent to admin.",
        'not_enough_deals': "You don't have enough completed deals to withdraw. Required: 2",
        'referral_info': "Your referral link:\nhttps://t.me/{bot_username}?start=ref_{user_id}\n\nFor each invited user you get 1 TON bonus after their first successful deal.",
        'support': "Write your message to support. We will reply as soon as possible.",
        'support_sent': "Your message has been sent to support.",
        'language_changed': "Language changed to English.",
        'back': "Back",
        'my_deals': "Your deals:\n{deals_list}",
        'no_deals': "You have no deals.",
        'deal_status_pending': "Waiting for partner",
        'deal_status_active': "Active (awaiting payment)",
        'deal_status_paid': "Paid",
        'deal_status_completed': "Completed",
        'deal_status_cancelled': "Cancelled",
        'admin_panel': "Admin panel",
        'admin_help': "Admin commands:\n/chat @username text - reply to user\n/hostlebuy memo - mark payment\n/ref deal_id - send gift notification\n/boost_success user_id count - boost successful deals\n/add_balance user_id amount - add balance\n/gtteam - show help",
        'enter_username': "Enter @username of user to reply:",
        'enter_reply_message': "Enter reply text:",
        'reply_sent': "Reply sent.",
        'enter_memo': "Enter deal memo to mark as paid:",
        'payment_marked': "Deal {memo} marked as paid.",
        'enter_deal_id_for_ref': "Enter deal ID to send gift notification:",
        'ref_sent': "Notification sent to both participants.",
        'enter_user_id_boost': "Enter user ID to boost:",
        'enter_boost_count': "Enter number of deals to boost:",
        'boost_success': "Successful deals for user {user_id} increased by {count}.",
        'enter_user_id_add_balance': "Enter user ID to add balance:",
        'enter_amount_add_balance': "Enter amount to add:",
        'balance_added': "Balance for user {user_id} increased by {amount}.",
        'withdraw_requests': "Withdrawal requests:\n{requests}",
        'no_withdraw_requests': "No withdrawal requests.",
        'admin_chat_instruction': "Use command /chat @username text to reply.",
    }
}

def get_text(user_id, key, **kwargs):
    lang = db.get_user(user_id)
    if lang:
        lang = lang[6]  # language column index
    else:
        lang = 'ru'
    text = TEXTS.get(lang, TEXTS['ru']).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text

def generate_memo():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# Обработчик команды /start
@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Проверяем, есть ли реферальный параметр
    args = message.text.split()
    ref_id = None
    if len(args) > 1:
        param = args[1]
        if param.startswith('ref_'):
            ref_id = int(param.split('_')[1])
        elif param.startswith('deal_'):
            # Это вступление в сделку
            memo = param.split('_')[1]
            deal = db.get_deal_by_memo(memo)
            if deal:
                # Проверяем, что пользователь не создатель и партнер еще не назначен
                if deal[1] != user_id and deal[2] is None:
                    db.update_deal(deal[0], partner_id=user_id, status='active')
                    await message.answer("Вы присоединились к сделке! Ожидайте подтверждения оплаты.")
                else:
                    await message.answer("Эта сделка уже недоступна.")
            else:
                await message.answer("Сделка не найдена.")
            return

    # Регистрация пользователя
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id, username, first_name, ref_id)
        if ref_id:
            # Начисляем бонус рефереру
            db.add_balance(ref_id, 1)  # бонус 1 TON
            db.add_referral_bonus(ref_id, 1, user_id, None)
    else:
        # Обновляем username
        db.update_user(user_id, username=username, first_name=first_name)

    # Отправка приветствия с баннером
    text = get_text(user_id, 'welcome')
    await message.answer_photo(photo=BANNER_URL, caption=text, reply_markup=kb.main_menu(get_text(user_id, 'lang')))

# Главное меню (по callback)
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    text = get_text(user_id, 'welcome')
    await callback.message.edit_caption(caption=text, reply_markup=kb.main_menu(get_text(user_id, 'lang')))
    await callback.answer()

# Обработчик "Мои реквизиты"
@dp.callback_query(F.data == "requisites")
async def requisites_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    req = db.get_user_requisites(user_id)
    if req:
        text = get_text(user_id, 'requisites', requisites=hblockquote(req))
        await callback.message.edit_caption(caption=text, reply_markup=kb.back_button())
    else:
        text = get_text(user_id, 'no_requisites')
        await callback.message.edit_caption(caption=text, reply_markup=kb.back_button())
    await callback.answer()

# Кнопка "Добавить реквизиты" (из меню) - но у нас нет отдельной кнопки, можно сделать inline
# Я добавлю кнопку в меню реквизитов
@dp.callback_query(F.data == "add_requisites")
async def add_requisites(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RequisitesEdit.text)
    await callback.message.edit_caption(caption=get_text(callback.from_user.id, 'enter_requisites'))
    await callback.answer()

# Обработка ввода реквизитов
@dp.message(StateFilter(RequisitesEdit.text))
async def requisites_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    db.set_requisites(user_id, text)
    await state.clear()
    await message.answer(get_text(user_id, 'requisites_saved'), reply_markup=kb.main_menu(get_text(user_id, 'lang')))

# Обработчик "Создать сделку"
@dp.callback_query(F.data == "create_deal")
async def create_deal_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealCreation.currency)
    # Предложим выбор валюты
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TON", callback_data="currency_ton"),
         InlineKeyboardButton(text="USDT", callback_data="currency_usdt")],
        [InlineKeyboardButton(text="RUB", callback_data="currency_rub")],
        [InlineKeyboardButton(text=get_text(callback.from_user.id, 'back'), callback_data="back_to_menu")]
    ])
    await callback.message.edit_caption(caption=get_text(callback.from_user.id, 'choose_currency'), reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("currency_"))
async def currency_chosen(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[1].upper()
    await state.update_data(currency=currency)
    await state.set_state(DealCreation.amount)
    await callback.message.edit_caption(caption=get_text(callback.from_user.id, 'enter_amount'))
    await callback.answer()

@dp.message(StateFilter(DealCreation.amount))
async def amount_entered(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(amount=amount)
    await state.set_state(DealCreation.description)
    await message.answer(get_text(message.from_user.id, 'enter_description'))

@dp.message(StateFilter(DealCreation.description))
async def description_entered(message: Message, state: FSMContext):
    description = message.text
    await state.update_data(description=description)
    await state.set_state(DealCreation.nft_link)
    await message.answer(get_text(message.from_user.id, 'enter_nft_link'))

@dp.message(StateFilter(DealCreation.nft_link))
async def nft_link_entered(message: Message, state: FSMContext):
    nft_link = message.text
    user_id = message.from_user.id
    data = await state.get_data()
    currency = data['currency']
    amount = data['amount']
    description = data['description']
    deal_id = generate_memo()  # уникальный ID
    memo = deal_id
    db.create_deal(deal_id, user_id, currency, amount, description, nft_link, memo)
    await state.clear()
    bot_username = (await bot.me()).username
    text = get_text(user_id, 'deal_created', memo=memo, bot_username=bot_username)
    await message.answer(text, reply_markup=kb.main_menu(get_text(user_id, 'lang')))

# Обработчик "Баланс"
@dp.callback_query(F.data == "balance")
async def balance_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = db.get_user_balance(user_id)
    successful_deals = db.get_successful_deals_count(user_id)
    text = get_text(user_id, 'balance', balance=balance, successful_deals=successful_deals)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit"),
         InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw")],
        [InlineKeyboardButton(text=get_text(user_id, 'back'), callback_data="back_to_menu")]
    ])
    await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    await callback.answer()

# Пополнение - показать адрес кошелька
@dp.callback_query(F.data == "deposit")
async def deposit_handler(callback: CallbackQuery):
    # Для простоты покажем фиксированный адрес и попросить отправить с комментарием user_id
    # В реальности нужен генератор адресов
    user_id = callback.from_user.id
    text = "Для пополнения баланса переведите TON на следующий кошелек:\n\n`UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`\n\nВ комментарии укажите ваш ID: `{}`\n\nПосле зачисления средства будут добавлены вручную администратором.".format(user_id)
    await callback.message.edit_caption(caption=text, reply_markup=kb.back_button())
    await callback.answer()

# Вывод средств
@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    successful_deals = db.get_successful_deals_count(user_id)
    if successful_deals < 2:
        await callback.message.edit_caption(caption=get_text(user_id, 'not_enough_deals'), reply_markup=kb.back_button())
        await callback.answer()
        return
    await state.set_state(Withdraw.amount)
    await callback.message.edit_caption(caption=get_text(user_id, 'enter_withdraw_amount'))
    await callback.answer()

@dp.message(StateFilter(Withdraw.amount))
async def withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Введите число.")
        return
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)
    if amount > balance:
        await message.answer("Недостаточно средств.")
        return
    # Создаем заявку
    requisites = db.get_user_requisites(user_id)
    if not requisites:
        await message.answer("У вас не добавлены реквизиты для вывода. Сначала добавьте их в разделе 'Мои реквизиты'.")
        return
    db.create_withdraw_request(user_id, amount, requisites)
    await state.clear()
    await message.answer(get_text(user_id, 'withdraw_request_sent'), reply_markup=kb.main_menu(get_text(user_id, 'lang')))

# Обработчик "Мои сделки"
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
            lines.append(f"<b>{deal[0]}</b> - {deal[3]} {deal[4]} - {status}")
        text = get_text(user_id, 'my_deals', deals_list='\n'.join(lines))
    await callback.message.edit_caption(caption=text, reply_markup=kb.back_button())
    await callback.answer()

# Обработчик "Рефералы"
@dp.callback_query(F.data == "referrals")
async def referrals_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await bot.me()).username
    text = get_text(user_id, 'referral_info', bot_username=bot_username, user_id=user_id)
    await callback.message.edit_caption(caption=text, reply_markup=kb.back_button())
    await callback.answer()

# Обработчик "Язык"
@dp.callback_query(F.data == "language")
async def language_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_lang = db.get_user(user_id)[6] if db.get_user(user_id) else 'ru'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text=get_text(user_id, 'back'), callback_data="back_to_menu")]
    ])
    await callback.message.edit_caption(caption="Выберите язык / Choose language:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("lang_"))
async def lang_chosen(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    db.update_user(user_id, language=lang)
    text = get_text(user_id, 'language_changed')
    await callback.message.edit_caption(caption=text, reply_markup=kb.main_menu(lang))
    await callback.answer()

# Обработчик "Техподдержка"
@dp.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state("support_message")
    await callback.message.edit_caption(caption=get_text(callback.from_user.id, 'support'), reply_markup=kb.back_button())
    await callback.answer()

@dp.message(StateFilter("support_message"))
async def support_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    # Сохраняем обращение
    db.create_support_ticket(user_id, text)
    # Отправляем админу
    admin_id = config.ADMIN_ID
    await bot.send_message(admin_id, f"Новое обращение от пользователя {user_id} (@{message.from_user.username}):\n\n{text}")
    await state.clear()
    await message.answer(get_text(user_id, 'support_sent'), reply_markup=kb.main_menu(get_text(user_id, 'lang')))

# ----- АДМИН-ПАНЕЛЬ -----

@dp.message(Command("wrteam"))
async def admin_panel_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("У вас нет доступа.")
        return
    text = get_text(config.ADMIN_ID, 'admin_panel')
    await message.answer(text, reply_markup=kb.admin_panel())

@dp.callback_query(F.data == "admin_help")
async def admin_help(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    text = get_text(config.ADMIN_ID, 'admin_help')
    await callback.message.edit_caption(caption=text, reply_markup=kb.back_button())
    await callback.answer()

# Обработчик команды /chat
@dp.message(Command("chat"))
async def chat_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    # Формат: /chat @username текст
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /chat @username текст")
        return
    username = parts[1].lstrip('@')
    text = parts[2]
    # Ищем пользователя по username
    # Можно через db, но у нас нет индекса по username, пройдемся по всем
    # В реальности лучше хранить username и искать
    # Для упрощения: попробуем отправить сообщение, если пользователь с таким username есть в боте
    try:
        # Пытаемся получить user_id по username через get_chat
        chat = await bot.get_chat(username)
        user_id = chat.id
        await bot.send_message(user_id, f"Ответ поддержки:\n\n{text}")
        await message.answer("Сообщение отправлено.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# Обработчик /hostlebuy
@dp.message(Command("hostlebuy"))
async def hostlebuy_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /hostlebuy memo")
        return
    memo = parts[1]
    deal = db.get_deal_by_memo(memo)
    if not deal:
        await message.answer("Сделка не найдена.")
        return
    if deal[6] != 'active' and deal[6] != 'pending':
        await message.answer("Сделка уже не активна.")
        return
    db.update_deal(deal[0], status='paid')
    # Уведомления участникам
    creator_id = deal[1]
    partner_id = deal[2]
    if creator_id:
        await bot.send_message(creator_id, f"Ваша сделка {memo} отмечена как оплаченная. Ожидайте завершения.")
    if partner_id:
        await bot.send_message(partner_id, f"Сделка {memo} отмечена как оплаченная. Подтвердите получение товара.")
    await message.answer(f"Сделка {memo} отмечена как оплаченная.")

# Обработчик /ref
@dp.message(Command("ref"))
async def ref_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /ref ID сделки")
        return
    deal_id = parts[1]
    deal = db.get_deal(deal_id)
    if not deal:
        await message.answer("Сделка не найдена.")
        return
    # Отправить уведомление обоим участникам
    creator_id = deal[1]
    partner_id = deal[2]
    if creator_id:
        await bot.send_message(creator_id, f"Менеджер @GGselSupp не обнаружил подарок по сделке {deal_id}. Обратитесь в поддержку.")
    if partner_id:
        await bot.send_message(partner_id, f"Менеджер @GGselSupp не обнаружил подарок по сделке {deal_id}. Обратитесь в поддержку.")
    await message.answer("Уведомления отправлены.")

# Обработчик /boost_success
@dp.message(Command("boost_success"))
async def boost_success_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /boost_success user_id count")
        return
    try:
        user_id = int(parts[1])
        count = int(parts[2])
    except ValueError:
        await message.answer("ID и количество должны быть числами.")
        return
    db.increment_successful_deals(user_id, count)
    await message.answer(f"Успешные сделки пользователя {user_id} увеличены на {count}.")

# Обработчик /add_balance (дополнительная команда для админа)
@dp.message(Command("add_balance"))
async def add_balance_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /add_balance user_id amount")
        return
    try:
        user_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer("ID и сумма должны быть числами.")
        return
    db.add_balance(user_id, amount)
    await message.answer(f"Баланс пользователя {user_id} увеличен на {amount}.")

# Обработчик /gtteam - показать справку
@dp.message(Command("gtteam"))
async def gtteam_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    text = get_text(config.ADMIN_ID, 'admin_help')
    await message.answer(text)

# ----- Остальные callback для админ-панели (для удобства) -----
@dp.callback_query(F.data == "admin_chat")
async def admin_chat_callback(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_caption(caption=get_text(config.ADMIN_ID, 'admin_chat_instruction'), reply_markup=kb.back_button())
    await callback.answer()

@dp.callback_query(F.data == "admin_hostlebuy")
async def admin_hostlebuy_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(HostleBuyAdmin.memo)
    await callback.message.edit_caption(caption=get_text(config.ADMIN_ID, 'enter_memo'))
    await callback.answer()

@dp.message(StateFilter(HostleBuyAdmin.memo))
async def hostlebuy_memo(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    memo = message.text.strip()
    deal = db.get_deal_by_memo(memo)
    if not deal:
        await message.answer("Сделка не найдена.")
        return
    if deal[6] != 'active' and deal[6] != 'pending':
        await message.answer("Сделка уже не активна.")
        return
    db.update_deal(deal[0], status='paid')
    creator_id = deal[1]
    partner_id = deal[2]
    if creator_id:
        await bot.send_message(creator_id, f"Ваша сделка {memo} отмечена как оплаченная. Ожидайте завершения.")
    if partner_id:
        await bot.send_message(partner_id, f"Сделка {memo} отмечена как оплаченная. Подтвердите получение товара.")
    await message.answer(f"Сделка {memo} отмечена как оплаченная.")
    await state.clear()

@dp.callback_query(F.data == "admin_ref")
async def admin_ref_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(RefAdmin.deal_id)
    await callback.message.edit_caption(caption=get_text(config.ADMIN_ID, 'enter_deal_id_for_ref'))
    await callback.answer()

@dp.message(StateFilter(RefAdmin.deal_id))
async def ref_deal_id(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    deal_id = message.text.strip()
    deal = db.get_deal(deal_id)
    if not deal:
        await message.answer("Сделка не найдена.")
        return
    creator_id = deal[1]
    partner_id = deal[2]
    if creator_id:
        await bot.send_message(creator_id, f"Менеджер @GGselSupp не обнаружил подарок по сделке {deal_id}. Обратитесь в поддержку.")
    if partner_id:
        await bot.send_message(partner_id, f"Менеджер @GGselSupp не обнаружил подарок по сделке {deal_id}. Обратитесь в поддержку.")
    await message.answer("Уведомления отправлены.")
    await state.clear()

@dp.callback_query(F.data == "admin_boost")
async def admin_boost_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(BoostSuccessAdmin.user_id)
    await callback.message.edit_caption(caption=get_text(config.ADMIN_ID, 'enter_user_id_boost'))
    await callback.answer()

@dp.message(StateFilter(BoostSuccessAdmin.user_id))
async def boost_user_id(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID.")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(BoostSuccessAdmin.count)
    await message.answer(get_text(config.ADMIN_ID, 'enter_boost_count'))

@dp.message(StateFilter(BoostSuccessAdmin.count))
async def boost_count(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    try:
        count = int(message.text)
    except ValueError:
        await message.answer("Введите число.")
        return
    data = await state.get_data()
    user_id = data['user_id']
    db.increment_successful_deals(user_id, count)
    await message.answer(f"Успешные сделки пользователя {user_id} увеличены на {count}.")
    await state.clear()

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AddBalanceAdmin.user_id)
    await callback.message.edit_caption(caption=get_text(config.ADMIN_ID, 'enter_user_id_add_balance'))
    await callback.answer()

@dp.message(StateFilter(AddBalanceAdmin.user_id))
async def add_balance_user_id(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID.")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(AddBalanceAdmin.amount)
    await message.answer(get_text(config.ADMIN_ID, 'enter_amount_add_balance'))

@dp.message(StateFilter(AddBalanceAdmin.amount))
async def add_balance_amount(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Введите число.")
        return
    data = await state.get_data()
    user_id = data['user_id']
    db.add_balance(user_id, amount)
    await message.answer(f"Баланс пользователя {user_id} увеличен на {amount}.")
    await state.clear()

@dp.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    requests = db.get_withdraw_requests(status='pending')
    if not requests:
        text = get_text(config.ADMIN_ID, 'no_withdraw_requests')
    else:
        lines = []
        for req in requests:
            lines.append(f"ID заявки: {req[0]}, пользователь: {req[1]}, сумма: {req[2]}, реквизиты: {req[3]}")
        text = get_text(config.ADMIN_ID, 'withdraw_requests', requests='\n'.join(lines))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="approve_withdraw"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data="reject_withdraw")],
        [InlineKeyboardButton(text=get_text(config.ADMIN_ID, 'back'), callback_data="back_to_menu")]
    ])
    await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    await callback.answer()

# Здесь нужно реализовать обработку подтверждения/отклонения заявок, но для простоты можно пропустить или сделать через команды.

# ----- Запуск бота и веб-сервера -----

async def main():
    # Запускаем бота
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
