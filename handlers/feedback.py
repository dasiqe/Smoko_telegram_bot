# handlers/feedback.py

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.dispatcher.filters.state import State, StatesGroup

from bot import dp
from db import cursor, db

class FSMFeedback(StatesGroup):
    product = State()       
    feedback_text = State() 

@dp.callback_query_handler(text="feedback", state=None)
async def feedback_initiate(callback_query: types.CallbackQuery):
    """
    Обработка нажатия кнопки 'feedback'.
    Формируется клавиатура с перечнем товаров, по которым можно оставить отзыв.
    """
    kb = InlineKeyboardMarkup(row_width=1)
    # Пример: получение списка товаров пользователя из базы.
    product_list = cursor.execute('SELECT product FROM id WHERE users=?', (str(callback_query.from_user.id),)).fetchone()[0]
    for product in product_list.split(',')[:-1]:
        kb.insert(InlineKeyboardButton(product, callback_data='fb_' + product))
    kb.add(InlineKeyboardButton('Назад', callback_data='backin'))
    await callback_query.message.edit_text('Выберите товар для отзыва')
    await callback_query.message.edit_reply_markup(kb)
    await FSMFeedback.product.set()

@dp.callback_query_handler(state=FSMFeedback.product)
async def feedback_product(callback_query: types.CallbackQuery, state: FSMContext):
    """
    После выбора товара сохраняется выбранный товар,
    затем пользователю предлагается ввести текст отзыва.
    """
    async with state.proxy() as data:
        data['product'] = callback_query.data[len("fb_"):]  # Обрезаем префикс 'fb_'
    await callback_query.message.edit_text('Можете написать свой отзыв на товар:\n' + callback_query.data[len("fb_"):])
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton('Назад', callback_data='backin'))
    await callback_query.message.edit_reply_markup(kb)
    await FSMFeedback.next()

@dp.message_handler(state=FSMFeedback.feedback_text)
async def feedback_text(message: types.Message, state: FSMContext):
    """
    После ввода текста отзыв сохраняется в базе и пользователю отправляется сообщение 'Спасибо за отзыв!'
    """
    async with state.proxy() as data:
        # Здесь сохраняем отзыв в таблицу feedbacks
        cursor.execute('INSERT INTO feedbacks(chat, message, product) VALUES (?,?,?)',
                        (message.chat.id, message.message_id, data['product']))
    db.commit()
    await message.answer('Спасибо за отзыв!')
    await state.finish()
