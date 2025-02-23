# handlers/start.py

"""Модуль для обработки команды /start и отображения главного меню.

Функции данного модуля создают динамическое главное меню с кнопками, зависящими от данных пользователя,
его статуса (админ или обычный пользователь) и наличия определённых записей в базе данных.
"""

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import dp, bot
from db import cursor, db
from config import ADMIN_IDS

async def start(message, inline=False):
    """
    Формирует и отправляет главное меню с динамическими кнопками.
    
    Аргументы:
        message: Сообщение или callback-запрос, инициирующий вызов.
        inline (bool): Если True, редактирует существующее сообщение; если False – отправляет новое сообщение.
    
    Примечания:
        - Кнопки добавляются в зависимости от состояния пользователя (наличие корзины, истории, скидок).
    """
    kb = InlineKeyboardMarkup(row_width=2)
    menu_btn = InlineKeyboardButton(text='Ассортимент🗂', callback_data='Ассортимент🗂')
    kb.add(menu_btn)
    
    # Если есть активные акции и пользователь не является администратором, добавляем кнопку "Акции"
    if cursor.execute('SELECT count(*) FROM sales').fetchone()[0] != 0 and (message.from_user.id not in ADMIN_IDS):
        kb.add(InlineKeyboardButton(text='Акции🎁', callback_data='sales'))
        
    kb.add(InlineKeyboardButton(text='Связь с менеджером👨‍💻', callback_data='Связь с менеджером👨‍💻'))
    
    # Проверка наличия записей в таблице корзины для данного пользователя
    if cursor.execute("SELECT count(*) FROM {} ".format(f'"{message.from_user.id}"')).fetchone()[0] != 0:
        kb.add(InlineKeyboardButton('Открыть корзину', callback_data='cart1'))
    
    # Если у пользователя есть история покупок, добавляем соответствующую кнопку
    if cursor.execute('SELECT history FROM id WHERE users = ?', (str(message.from_user.id),)).fetchone()[0] != 'None':
        kb.add(InlineKeyboardButton('История покупок 📋', callback_data='history'))
    
    # Если пользователь не новый и не заблокирован, разрешаем оставлять отзывы
    if (cursor.execute('SELECT spend FROM id WHERE users = ?', (str(message.from_user.id),)).fetchone()[0] != 0 and
        cursor.execute('SELECT ban FROM id WHERE users = ?', (str(message.from_user.id),)).fetchone()[0] != 1):
        kb.add(InlineKeyboardButton('Оставить отзыв ✍️', callback_data='feedback'))
    
    # Если есть отзывы, добавляем кнопку для их просмотра
    if cursor.execute('SELECT count(*) FROM otz').fetchone()[0] != 0:
        kb.add(InlineKeyboardButton('Наши отзывы ✅', callback_data='otz'))
    
    # Для администраторов добавляем дополнительные кнопки
    if message.from_user.id in ADMIN_IDS:
        kb.add(
            InlineKeyboardButton('Добавить', callback_data='Добавить'),
            InlineKeyboardButton('Удалить', callback_data='Удалить'),
            InlineKeyboardButton('Рассылка', callback_data='Рассылка'),
            InlineKeyboardButton(text='Акции🎁', callback_data='sales')
        )
        if cursor.execute('SELECT count(*) FROM feedbacks').fetchone()[0] != 0:
            kb.insert(InlineKeyboardButton('Новые отзывы!', callback_data='Отзывы'))
    
    # Если режим inline – редактируем предыдущее сообщение, иначе – отправляем новое
    if inline:
        await message.message.edit_text('Что вас интересует?')  # Редактирование текста сообщения
        await message.message.edit_reply_markup(reply_markup=kb)
        await message.answer()
    else:
        await message.answer('Что вас интересует?', reply_markup=kb)

@dp.message_handler(commands=['start'])
async def handle_start_command(message: types.Message):
    """
    Обрабатывает команду /start:
        - Создаёт таблицы для хранения данных пользователя и его корзины, если они ещё не существуют.
        - Регистрирует нового пользователя в таблице, пересылает стартовое сообщение администратору и отправляет приветственное сообщение.
        - Обновляет поле start, если оно отсутствует.
    
    Аргументы:
        message (types.Message): Сообщение, полученное от пользователя.
    """
    # Создание таблицы для хранения данных пользователя, если она отсутствует
    cursor.execute('CREATE TABLE IF NOT EXISTS id (users TEXT, history TEXT DEFAULT NULL, first_client INTEGER DEFAULT 1, first_pressed INTEGER DEFAULT 0, spend INTEGER DEFAULT 0, start INTEGER DEFAULT NULL, product TEXT DEFAULT NULL, ban INTEGER DEFAULT 0)')
    
    # Создание таблицы для хранения корзины конкретного пользователя
    cursor.execute('CREATE TABLE IF NOT EXISTS {} (cart TEXT, price TEXT, count INTEGER)'.format(f'"{message.from_user.id}"'))
    db.commit()
    
    # Если пользователь новый, добавляем его в таблицу id и уведомляем админа
    if cursor.execute('SELECT count(*) FROM id WHERE users = ?', (str(message.from_user.id),)).fetchone()[0] == 0:
        cursor.execute('INSERT INTO id (users, start, first_client) VALUES (?, ?, ?)', (str(message.from_user.id), message.message_id, 1))
        db.commit()
        # Пересылаем сообщение администратору для уведомления
        await bot.forward_message(1150081965, message.chat.id, message.message_id)
        await bot.send_message(1150081965, '@' + (message.from_user.username or 'unknown'))
        await message.answer('Добро пожаловать в Smoko❤️')
    
    # Обновляем поле start, если оно ещё не установлено
    if cursor.execute('SELECT start FROM id WHERE users = ?', (str(message.from_user.id),)).fetchone()[0] is None:
        cursor.execute('UPDATE id SET start=? WHERE users=?', (message.message_id, str(message.from_user.id)))
        db.commit()
        
    await start(message)
