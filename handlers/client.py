# handlers/client.py

"""Модуль для обработки клиентских запросов: навигация по меню, работа с отзывами и акциями.

Здесь реализованы обработчики для:
    - Возврата в главное меню.
    - Модерации отзывов и комментариев.
    - Отображения и обработки акций, бонусов и истории заказов.
    - Контакта с менеджером и оформления оптовых заказов.
"""

import random
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from bot import dp, bot
from db import cursor, db
from config import ADMIN_IDS
from handlers.start import start

btn_back = InlineKeyboardButton('Меню', callback_data='back')
btn_back_in = InlineKeyboardButton('Назад в меню', callback_data='backin')

@dp.message_handler(text='Меню', state="*")
async def handle_menu_message(message: types.Message, state: FSMContext):
    """
    Возвращает пользователя в главное меню при получении сообщения "Меню".
    
    Завершает активное состояние (если есть) перед возвратом в меню.
    """
    current_state = await state.get_state()
    if current_state is None:
        await start(message)
    else:
        await state.finish()
        await start(message)

@dp.callback_query_handler(text='backin', state="*")
async def back_in_menu(callback: types.CallbackQuery, state: FSMContext):
    """
    Завершает текущее состояние и возвращает в главное меню в inline-режиме.
    """
    await state.finish()
    await start(callback, inline=True)
    await callback.answer()

@dp.callback_query_handler(text='back')
async def handle_back(callback: types.CallbackQuery):
    """
    Возвращает в главное меню в inline-режиме.
    """
    await start(callback, inline=True)
    await callback.answer()

@dp.callback_query_handler(text='otz')
async def handle_otz_callback(callback_query: types.CallbackQuery):
    """
    Пересылает все отзывы из таблицы "otz" пользователю.
    
    Для каждого отзыва отправляет сначала имя автора, затем пересылает само сообщение.
    """
    for item in cursor.execute('SELECT * FROM otz').fetchall():
        # item[2] - текст отзыва, item[0] и item[1] - идентификаторы для пересылки сообщения
        await bot.send_message(callback_query.from_user.id, item[2] + ":")
        await bot.forward_message(callback_query.from_user.id, item[0], item[1])
    await start(callback_query, inline=True)

@dp.callback_query_handler(text='Отзывы')
async def handle_feedbacks_callback(callback_query: types.CallbackQuery):
    """
    Отображает новые отзывы для модерации с кнопками "Запостить", "Удалить" и "Заблокировать".
    
    Если нет новых отзывов, выводится соответствующее сообщение.
    """
    try:
        for item in cursor.execute('SELECT * FROM feedbacks').fetchall():
            kb = InlineKeyboardMarkup(row_width=2)
            await bot.forward_message(callback_query.from_user.id, item[0], item[1])
            # Формируем кнопки для обработки отзыва
            await bot.send_message(
                callback_query.from_user.id,
                '|\n' + item[2],
                reply_markup=kb.add(
                    InlineKeyboardButton('Запостить', callback_data=f'feedback_add|{item[0]}|{item[1]}|{item[2]}'),
                    InlineKeyboardButton('Удалить', callback_data=f'feedback_del|{item[0]}|{item[1]}'),
                    InlineKeyboardButton('Заблокировать', callback_data=f'feedback_ban{item[0]}')
                )
            )
    except Exception:
        await callback_query.answer('Нет новых отзывов.', show_alert=True)
    await start(callback_query, inline=True)

@dp.callback_query_handler(Text(startswith='feedback_add'))
async def handle_feedback_add(callback_query: types.CallbackQuery):
    """
    Переносит отзыв из очереди ожидания в опубликованные отзывы и удаляет его из очереди.
    
    Разбивает callback_data по разделителю '|' для получения необходимых идентификаторов.
    """
    data = callback_query.data.split('|')
    cursor.execute('INSERT INTO otz VALUES (?,?,?)', (int(data[1]), int(data[2]), data[3]))
    cursor.execute('DELETE FROM feedbacks WHERE chat=? AND message=?', (int(data[1]), int(data[2])))
    db.commit()
    await callback_query.answer('Отзыв запостен', show_alert=True)

@dp.callback_query_handler(Text(startswith='feedback_del'))
async def handle_feedback_delete(callback_query: types.CallbackQuery):
    """
    Удаляет отзыв из очереди ожидания.
    
    Использует идентификаторы, извлечённые из callback_data.
    """
    data = callback_query.data.split('|')
    cursor.execute('DELETE FROM feedbacks WHERE chat=? AND message=?', (int(data[1]), int(data[2])))
    db.commit()
    await callback_query.answer('Отзыв удалён', show_alert=True)

@dp.callback_query_handler(Text(startswith='feedback_ban'))
async def handle_feedback_ban(callback_query: types.CallbackQuery):
    """
    Блокирует пользователя, основываясь на отзыве, и удаляет все его ожидающие отзывы.
    
    Из callback_data извлекается идентификатор пользователя.
    """
    user_id = callback_query.data[len("feedback_ban"):]
    cursor.execute('UPDATE id SET ban = 1 WHERE users=?', (str(user_id),))
    cursor.execute('DELETE FROM feedbacks WHERE chat=?', (int(user_id),))
    db.commit()
    await callback_query.answer('Пользователь заблокирован', show_alert=True)

@dp.callback_query_handler(text='sales')
async def handle_sales_callback(callback_query: types.CallbackQuery):
    """
    Отображает текущие акции и бонусы, а также дополнительные опции для администраторов.
    
    Если пользователь впервые, добавляется бонус "Приветственный бонус".
    """
    kb = InlineKeyboardMarkup(row_width=1)
    if cursor.execute('SELECT first_client FROM id WHERE users=?', (str(callback_query.from_user.id),)).fetchone()[0] == 1:
        kb.insert(InlineKeyboardButton('Приветственный бонус', callback_data='first_buy'))
    for item in cursor.execute('SELECT * FROM sales').fetchall():
        kb.insert(InlineKeyboardButton(item[0], callback_data=f'sale{item[2]}'))
    await callback_query.message.edit_text('Актуальные акции🎁')
    if callback_query.from_user.id in ADMIN_IDS:
        kb.add(
            InlineKeyboardButton('Добавить', callback_data='Добавитьакцию'),
            InlineKeyboardButton('Удалить', callback_data='Удалитьакцию')
        )
    kb.add(btn_back_in)
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()

@dp.callback_query_handler(Text(startswith='sale'))
async def handle_sale_detail(callback_query: types.CallbackQuery):
    """
    Показывает подробное описание выбранной акции.
    
    Извлекает идентификатор акции из callback_data.
    """
    sale_id = callback_query.data[4:]  # Извлекаем идентификатор, начиная с 5-го символа
    desc = cursor.execute('SELECT desc FROM sales WHERE id=?', (sale_id,)).fetchone()[0]
    await callback_query.message.edit_text(desc)
    await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(row_width=1).add(btn_back_in))
    await callback_query.answer()

@dp.callback_query_handler(text="first_buy")
async def handle_first_buy(callback_query: types.CallbackQuery):
    """
    Применяет скидку на первый заказ и обновляет статус пользователя.
    """
    cursor.execute('UPDATE id SET first_pressed=1 WHERE users=?', (str(callback_query.from_user.id),))
    cursor.execute('UPDATE id SET first_client=0 WHERE users=?', (str(callback_query.from_user.id),))
    db.commit()
    await callback_query.message.edit_text('Цена на первый заказ снижена на 10%.')
    await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(row_width=1).add(btn_back_in))
    await callback_query.answer()

@dp.callback_query_handler(text="history")
async def handle_history_callback(callback_query: types.CallbackQuery):
    """
    Отображает историю покупок пользователя.
    """
    history = cursor.execute('SELECT history FROM id WHERE users=?', (str(callback_query.from_user.id),)).fetchone()[0]
    await callback_query.message.edit_text(history)
    await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(row_width=1).add(btn_back_in))
    await callback_query.answer()

### Обработка связи с менеджером и оптовых заказов

@dp.callback_query_handler(Text('Связь с менеджером👨‍💻'))
async def handle_contact_manager(callback_query: types.CallbackQuery):
    """
    Предоставляет пользователю варианты для связи с менеджером или оформления оптового заказа.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    btn_trouble = InlineKeyboardButton("Проблема с проданной единицей⛔️", callback_data='trouble')
    btn_invite = InlineKeyboardButton("Предложения сотрудничества🤝", callback_data='Предложения сотрудничества🤝')
    btn_bulk = InlineKeyboardButton("Заказать оптом📦", callback_data='opt')
    markup.add(btn_trouble)
    markup.add(btn_invite)
    markup.add(btn_bulk, btn_back)
    await callback_query.message.edit_text("Выберите интересующий вопрос")
    await callback_query.message.edit_reply_markup(markup)
    await callback_query.answer()

@dp.callback_query_handler(Text('opt'))
async def handle_bulk_order(callback_query: types.CallbackQuery):
    """
    Отображает информацию об условиях оптовых заказов и предоставляет вариант связи с менеджером.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    btn_manager = InlineKeyboardButton("Обратиться к менеджеру👨‍💻", callback_data='Обратиться к менеджеру👨‍💻')
    markup.add(btn_manager)
    markup.add(btn_back)
    await callback_query.message.edit_text(
        "1. Минимальная сумма заказа 5000₽ \n\n"
        "2. Условия доставки: отправляем СДЭКом. Стоимость зависит от веса и объёмов.\n\n"
        "3. Оплата: полная сумма на карту Сбербанк.\n\n"
        "4. Оформление заказа: ФИО, адрес, контактные данные, индекс.\n\n"
        "5. Состав заказа: наименование, вкус - количество.\n\n"
        "6. После оплаты заказ собирается и отправляется в течение 1-3 дней.\n\n"
        "Важно: фабричный брак не возвращается!"
    )
    await callback_query.message.edit_reply_markup(markup)
    await callback_query.answer()

@dp.callback_query_handler(Text('trouble'))
async def handle_trouble_callback(callback_query: types.CallbackQuery):
    """
    Выводит правила возврата/обмена товара и предоставляет возможность связаться с менеджером.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    btn_manager = InlineKeyboardButton("Обратиться к менеджеру👨‍💻", callback_data='Обратиться к менеджеру👨‍💻')
    markup.add(btn_manager)
    markup.add(btn_back)
    await callback_query.message.edit_text(
        "Правила возврата:\nОбмен возможен при обнаружении брака в товаре. Обмен товара производится в течение 18 часов после покупки."
    )
    await callback_query.message.edit_reply_markup(markup)
    await callback_query.answer()

@dp.callback_query_handler(Text(('Обратиться к менеджеру👨‍💻', 'Предложения сотрудничества🤝')))
async def handle_contact_or_proposal(callback_query: types.CallbackQuery):
    """
    Предоставляет ссылку для связи с менеджером для получения поддержки или обсуждения сотрудничества.
    """
    await callback_query.message.edit_text('Ссылка на менеджера')
    await callback_query.message.edit_reply_markup(
        InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("Smoko_adm", url='https://t.me/Smoko_adm'),
            btn_back
        )
    )
    await callback_query.answer()

@dp.callback_query_handler(Text(startswith='askManager '))
async def handle_manager_query(callback_query: types.CallbackQuery):
    """
    Если у пользователя анонимный аккаунт, предлагает отправить номер для связи с менеджером.
    """
    user_id = callback_query.data[len("askManager "):]
    await bot.send_message(user_id,
                        'Менеджер не может с вами связаться, так как у вас анонимный аккаунт. Пожалуйста, отправьте номер, чтобы менеджер мог связаться с вами.',
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton('Отправить номер', callback_data=f'sendContact {user_id}')
                        ))
    await callback_query.answer()

@dp.callback_query_handler(Text(startswith='sendContact '))
async def handle_send_contact_prompt(callback_query: types.CallbackQuery):
    """
    Запрашивает у пользователя отправку контактной информации для связи с менеджером.
    """
    await bot.send_message(callback_query.data[len("sendContact "):],
                        'Нажмите кнопку ниже, чтобы отправить номер менеджеру.',
                        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
                            KeyboardButton('Передать контакт', request_contact=True)
                        ).add(btn_back))
    await callback_query.answer()

@dp.message_handler(content_types=['contact'])
async def handle_contact_message(message: types.Message):
    """
    Пересылает полученный контакт всем администраторам.
    """
    for admin in ADMIN_IDS:
        await bot.forward_message(admin, message.chat.id, message.message_id)
    await message.answer('Спасибо, ваш номер получен', reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(btn_back))

@dp.message_handler()
async def handle_default_message(message: types.Message):
    """
    Если сообщение не соответствует стандартным командам, возвращает пользователя в главное меню.
    В случае совпадения с определёнными ключевыми словами, отвечает случайным приколом.
    """
    if message.text.lower() not in ['скипа', 'лёха', 'леха']:
        await start(message)
    else:
        responses = [
            "блядь, что не отнять", "пивная мразь", "сын фанки бара", "перетраханный сержант, недотраханный офицер",
            "борец с солью", "рядовой отряда быстрого назначения утилизации пива", "кастрат", "сегодня вор, завтра прокурор",
            "радикальный пиздолиз", "козлиное рыло", "все свое в карты проиграл", "апофеоз дегенерации",
            "пятикратный пиздабол по району", "царь, каблук его корона", "в сраку обработанный", "по еблу покойница, по пизде разбойница",
            "пустая трата спермы", "меф-авиация", "стафилококковая шлюха", "хуй в кабаньем жиру", "кал калыч",
            "внебрачный сын тайской шлюхи", "кваршня", "рыночная мразота", "пузочёс", "премьер-министр еблании",
            "гнойная залупа", "официальный амбассадор напитков сушняк", "лох", "поперек пизды рожденный",
            "шакал с казбекской", "бубновый валет", "жидкий воздухан", "клещевидный слизняк", "гроза районских собак",
            "садовый гном", "украинский селезень", "ослиная залупа", "шпаковая шаболда", "тухлая шлюха",
            "газонюхич", "пупкин залупкин", "говномет", "мерзкая пародия на человека", "мочевоз", "шалава на ночь",
            "кокаиновая мразь", "снюсовый чупачупс", "героиновая пленница", "мефедроновая далбоебка", "солевая давалка"
        ]
        await message.answer(random.choice(responses))
