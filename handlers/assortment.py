# handlers/assortment.py

"""Модуль для работы с ассортиментом товаров.

Обрабатывает:
    1. Отображение главного меню "Ассортимент🗂".
    2. Выбор конкретного ассортимента и бренда.
    3. Отображение деталей товара.
    4. Добавление выбранного варианта (вкуса) товара в корзину.
"""

from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import dp, bot
from db import cursor, db, decrypt_code, get_table_name

btn_back = InlineKeyboardButton('Меню', callback_data='back')

@dp.callback_query_handler(Text('Ассортимент🗂'))
async def handle_assortment_menu(callback_query: types.CallbackQuery):
    """
    Отображает главное меню ассортимента.
    
    Формирует клавиатуру, в которой каждая кнопка соответствует элементу ассортимента.
    
    Аргументы:
        callback_query (types.CallbackQuery): Callback-запрос от пользователя.
    """
    kb = InlineKeyboardMarkup(row_width=2)
    # Извлекаем все элементы ассортимента из таблицы "Ассортимент🗂"
    for item in cursor.execute('SELECT * FROM "Ассортимент🗂"').fetchall():
        # item[0] – название, item[1] – идентификатор ассортимента
        kb.insert(InlineKeyboardButton(item[0], callback_data=f'assort_{item[1]}'))
    kb.add(btn_back)
    await callback_query.message.edit_text('Ассортимент🗂')
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()

@dp.callback_query_handler(Text(startswith='assort_'))
async def handle_assortment_selection(callback_query: types.CallbackQuery):
    """
    Обрабатывает выбор конкретного ассортимента.
    
    Формирует клавиатуру с брендами, относящимися к выбранному ассортименту.
    
    Аргументы:
        callback_query (types.CallbackQuery): Callback-запрос с данными вида "assort_{id}".
    """
    assortment_id = callback_query.data[len("assort_"):]
    kb = InlineKeyboardMarkup(row_width=2)
    # Извлекаем бренды из таблицы с именем, соответствующим assortment_id
    for item in cursor.execute(f'SELECT * FROM "{assortment_id}"').fetchall():
        # item[0] – название бренда, item[1] – идентификатор бренда
        kb.insert(InlineKeyboardButton(item[0], callback_data=f'brand_{assortment_id}_{item[1]}'))
    kb.add(InlineKeyboardButton('<<Назад', callback_data='Ассортимент🗂'))
    # Получаем описание выбранного ассортимента
    text = cursor.execute('SELECT tastes FROM "Ассортимент🗂" WHERE id=?', (assortment_id,)).fetchone()[0]
    await callback_query.message.edit_text(text)
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()

@dp.callback_query_handler(Text(startswith='brand_'))
async def handle_assortment_brand_selection(callback_query: types.CallbackQuery):
    """
    Обрабатывает выбор бренда в рамках выбранного ассортимента.
    
    Формирует клавиатуру с товарами данного бренда.
    
    Аргументы:
        callback_query (types.CallbackQuery): Callback-запрос с данными вида "brand_{assortment_id}_{brand_id}".
    """
    data = callback_query.data[len("brand_"):]
    kb = InlineKeyboardMarkup(row_width=2)
    # Извлекаем товары из таблицы с именем, соответствующим полученным данным
    for item in cursor.execute(f'SELECT * FROM "{data}"').fetchall():
        # item[0] – название товара, item[1] – идентификатор товара
        kb.insert(InlineKeyboardButton(item[0], callback_data=f'product_{data}_{item[1]}'))
    # Кнопка возврата к выбору ассортимента
    kb.add(InlineKeyboardButton('<<Назад', callback_data=f'assort_{data.split("_")[0]}'))
    # Получаем описание бренда или ассортимента для отображения
    text = cursor.execute('SELECT tastes FROM "{}" WHERE id=?'.format(data.split("_")[0]), (data.split('_')[1],)).fetchone()[0]
    await callback_query.message.edit_text(text)
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()

@dp.callback_query_handler(Text(startswith='product_'))
async def handle_product_detail(callback_query: types.CallbackQuery):
    """
    Отображает подробности выбранного товара и варианты его вкусов.
    
    Формирует клавиатуру с вариантами вкусов, отображает описание товара, фото и цену.
    
    Аргументы:
        callback_query (types.CallbackQuery): Callback-запрос с данными вида "product_{product_code}".
    """
    kb = InlineKeyboardMarkup(row_width=2)
    # Разбиваем callback_data для получения частей кода товара
    parts = callback_query.data[len("product_"):].split('_')
    # Полный код товара без отдельного идентификатора вкуса (например, "2_1_1")
    full_product_code = '_'.join(parts)
    main_taste = decrypt_code(full_product_code)  # Получаем основное название товара по коду

    # Формируем клавиатуру вариантов вкусов, извлекая данные из таблицы с именем full_product_code
    for item in cursor.execute('SELECT * FROM "{}"'.format(full_product_code)).fetchall():
        # Формируем callback_data для конкретного вкуса, добавляя идентификатор вкуса
        flavor_cb = f'{full_product_code}_{item[1]}'  # Пример: "2_1_1_2"
        try:
            # Проверяем, есть ли уже этот вариант товара в корзине пользователя
            result = cursor.execute(
                "SELECT count FROM {} WHERE cart = ?".format(f'"{callback_query.from_user.id}"'),
                (flavor_cb,)
            ).fetchone()
            count_value = result[0] if result is not None else 0
            if count_value:
                # Если вариант уже в корзине, отображаем количество рядом с названием вкуса
                kb.insert(InlineKeyboardButton(f'({count_value}){item[0]}', callback_data=f'addCart_{flavor_cb}'))
            else:
                kb.insert(InlineKeyboardButton(item[0], callback_data=f'addCart_{flavor_cb}'))
        except Exception:
            kb.insert(InlineKeyboardButton(item[0], callback_data=f'addCart_{flavor_cb}'))

    # Кнопка возврата к выбору бренда
    category_code = "_".join(parts[:-1])  # Например, если full_product_code = "2_1_1", то category_code = "2_1"
    kb.add(InlineKeyboardButton('<<Назад', callback_data=f'brand_{category_code}'))

    # Если корзина пользователя не пуста, добавляем кнопку "Открыть корзину"
    cart_count = cursor.execute("SELECT count(*) FROM {} ".format(f'"{callback_query.from_user.id}"')).fetchone()
    if cart_count and cart_count[0] != 0:
        kb.insert(InlineKeyboardButton('Открыть корзину', callback_data='cart1'))

    # Получаем данные о товаре (фото, описание, цену) из таблицы photos
    photo_data = cursor.execute('SELECT * FROM photos WHERE names==?', (full_product_code,)).fetchone()
    if photo_data is None:
        photo_data = ("", "без фото", "Описание не найдено", "0₽")
    try:
        price = int(photo_data[-1][:-1])
    except Exception:
        price = 0

    # Получаем полное название товара (например, через decrypt_code)
    product_name = decrypt_code(full_product_code)
    if photo_data[1] != 'без фото':
        text = f'[​]({photo_data[1]})*{main_taste} {product_name}*\n*Описание:*\n{photo_data[2]}\n*Цена:* {price}₽'
    else:
        text = f'*{main_taste} {product_name}*\n*Описание:*\n{photo_data[2]}\n*Цена:* {price}₽'

    await callback_query.message.edit_text(text, parse_mode='Markdown')
    await callback_query.message.edit_reply_markup(reply_markup=kb)
    await callback_query.answer()

@dp.callback_query_handler(Text(startswith='addCart_'))
async def handle_add_to_cart(callback_query: types.CallbackQuery):
    """
    Добавляет выбранный вариант товара (вкуса) в корзину.
    
    Если такой товар отсутствует в корзине, вставляет новую запись.
    Если товар уже есть, увеличивает количество.
    После обновления корзины обновляет отображение деталей товара.
    
    Аргументы:
        callback_query (types.CallbackQuery): Callback-запрос с данными вида "addCart_{flavor_code}".
    """
    # Извлекаем полный код варианта товара, например, "2_1_1_2"
    flavor_code = callback_query.data[len("addCart_"):]
    # Получаем базовый код товара без идентификатора вкуса, например, "2_1_1"
    product_code = '_'.join(flavor_code.split('_')[:-1])
    
    product_data = cursor.execute('SELECT price FROM photos WHERE names=?', (product_code,)).fetchone()
    if product_data is None:
        await callback_query.answer('Ошибка: товар не найден ❌', show_alert=True)
        return
    price = product_data[0]

    user_cart_table = f'"{callback_query.from_user.id}"'
    # Создаём таблицу корзины для пользователя, если она не существует
    cursor.execute(f'CREATE TABLE IF NOT EXISTS {user_cart_table} (cart TEXT, price TEXT, count INTEGER)')
    db.commit()

    product_count = cursor.execute(
        f'SELECT count FROM {user_cart_table} WHERE cart=?', (flavor_code,)
    ).fetchone()
    if product_count is None:
        # Вставляем новый товар в корзину
        cursor.execute(
            f'INSERT INTO {user_cart_table} (cart, price, count) VALUES (?, ?, ?)',
            (flavor_code, price, 1)
        )
    else:
        # Увеличиваем количество существующего товара
        new_count = product_count[0] + 1
        cursor.execute(
            f'UPDATE {user_cart_table} SET count=? WHERE cart=?',
            (new_count, flavor_code)
        )
    db.commit()

    await callback_query.answer('Товар добавлен в корзину ✅', show_alert=True)
    # Обновляем отображение товара: меняем callback_data на "product_" + product_code (без вкуса)
    callback_query.data = "product_" + product_code
    await handle_product_detail(callback_query)
