# handlers/broadcast.py

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import dp, bot
from db import cursor, db
from config import ADMIN_IDS

from handlers.start import start 

# Кнопка "Назад в меню"
btn_back_in = InlineKeyboardButton('Назад в меню', callback_data='backin')

# Определение состояний для рассылки
class FSMBroadcast(StatesGroup):
    broadcast_message = State() 

# Хендлер для инициализации рассылки
@dp.callback_query_handler(text='Рассылка')
async def handle_broadcast_initiate(callback_query: types.CallbackQuery):
    """
    Устанавливает состояние для рассылки и просит ввести сообщение, которое нужно разослать.
    """
    await FSMBroadcast.broadcast_message.set()
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(btn_back_in)
    await callback_query.message.edit_text('Что отправить?')
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()

# Хендлер для получения текста рассылки и отправки его всем пользователям
@dp.message_handler(state=FSMBroadcast.broadcast_message)
async def handle_broadcast_message(message: types.Message, state: FSMContext):
    """
    Отправляет введённое сообщение всем пользователям, полученным из таблицы id,
    уведомляет админов о количестве отправленных сообщений и возвращает пользователя в главное меню.
    """
    sent_count = 0
    for v in cursor.execute('SELECT * FROM id').fetchall():
        try:
            await bot.send_message(v[0], message.text)
            sent_count += 1
        except Exception:
            continue
    try:
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f'Отправлено {sent_count} пользователям')
    except Exception:
        pass
    await state.finish()
    await start(message)
