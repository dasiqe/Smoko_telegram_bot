# handlers/admin.py

"""Модуль для административных операций.

Содержит обработчики для:
    - Добавления нового продукта.
    - Удаления продуктов и брендов.
    - Работа с акциями.
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup

from bot import dp, bot
from db import cursor, db, decrypt_code, get_table_name
from config import ADMIN_IDS

btn_back = InlineKeyboardButton('Меню', callback_data='back')


class FSMAdmin(StatesGroup):
    category = State()
    brand = State()
    product_name = State()
    description = State()
    display_price = State()
    photo_url = State()
    price_options = State()


class FSMDelete(StatesGroup):
    category = State()
    product_name = State()
    surname = State()
    extra = State()


class FSMSale(StatesGroup):
    sale_name = State()
    sale_description = State()


@dp.callback_query_handler(text='Добавить', state=None)
async def handle_add_initiate(callback_query: types.CallbackQuery):
    """
    Инициализирует процесс добавления нового продукта.
    
    Отправляет сообщение с выбором или вводом названия ассортимента.
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    try:
        for item in cursor.execute('SELECT * FROM "Ассортимент🗂"').fetchall():
            kb.insert(item[0])
    except Exception:
        pass
    kb.add(btn_back)
    await callback_query.message.answer(
        'Введите название нового ассортимента или выберите существующий',
        reply_markup=kb
    )
    await FSMAdmin.category.set()
    await callback_query.answer()


@dp.message_handler(state=FSMAdmin.category)
async def handle_admin_category(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод ассортимента.
    
    Сохраняет введённый ассортимент и предлагает выбрать или ввести новый бренд.
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    async with state.proxy() as data:
        data['category'] = message.text
        try:
            code = str(cursor.execute(
                'SELECT id FROM "Ассортимент🗂" WHERE tastes== ?', (data["category"],)
            ).fetchone()[0])
            for item in cursor.execute(f'SELECT * FROM "{code}"').fetchall():
                kb.insert(item[0])
        except Exception:
            pass
    kb.add(btn_back)
    await message.answer('Введите название нового бренда или выберите существующий', reply_markup=kb)
    await FSMAdmin.next()


@dp.message_handler(state=FSMAdmin.brand)
async def handle_admin_brand(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод бренда.
    
    Сохраняет введённый бренд и предлагает ввести название линейки товаров.
    """
    async with state.proxy() as data:
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        data['brand'] = message.text
        try:
            code = str(cursor.execute(
                'SELECT id FROM "Ассортимент🗂" WHERE tastes== ?', (data["category"],)
            ).fetchone()[0])
            brand_code = code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(code), (data["brand"],)
            ).fetchone()[0])
            for item in cursor.execute(f'SELECT * FROM "{brand_code}"').fetchall():
                kb.insert(item[0])
        except Exception:
            pass
    kb.add(btn_back)
    await FSMAdmin.next()
    await message.answer('Введите название линейки товаров', reply_markup=kb)


@dp.message_handler(state=FSMAdmin.product_name)
async def handle_admin_product_name(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод названия продукта.
    
    Сохраняет название продукта и, если описание уже существует, предлагает оставить его без изменений.
    """
    async with state.proxy() as data:
        data['product_name'] = message.text
        try:
            code = str(cursor.execute(
                'SELECT id FROM "Ассортимент🗂" WHERE tastes== ?', (data["category"],)
            ).fetchone()[0])
            brand_code = code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(code), (data["brand"],)
            ).fetchone()[0])
            product_code = brand_code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(brand_code), (data["product_name"],)
            ).fetchone()[0])
            if cursor.execute(
                'SELECT count(*) FROM photos WHERE names = ?', (product_code,)
            ).fetchone()[0] != 0:
                current_desc = cursor.execute(
                    'SELECT desc FROM photos WHERE names=?', (product_code,)
                ).fetchone()[0]
                kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add('без изменений', btn_back)
                await message.answer('Текущее описание:\n' + current_desc, reply_markup=kb)
            else:
                await message.answer('Введите описание', reply_markup=ReplyKeyboardMarkup(
                    resize_keyboard=True, row_width=2
                ).add(btn_back))
        except Exception:
            await message.answer('Введите описание', reply_markup=ReplyKeyboardMarkup(
                resize_keyboard=True, row_width=2
            ).add(btn_back))
    await FSMAdmin.next()


@dp.message_handler(state=FSMAdmin.description)
async def handle_admin_description(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод описания продукта.
    
    Сохраняет описание и, если цена уже существует, предлагает оставить её без изменений.
    """
    async with state.proxy() as data:
        data['description'] = message.text
        try:
            code = str(cursor.execute(
                'SELECT id FROM "Ассортимент🗂" WHERE tastes== ?', (data["category"],)
            ).fetchone()[0])
            brand_code = code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(code), (data["brand"],)
            ).fetchone()[0])
            product_code = brand_code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(brand_code), (data["product_name"],)
            ).fetchone()[0])
            if cursor.execute(
                'SELECT count(*) FROM photos WHERE names = ?', (product_code,)
            ).fetchone()[0] != 0:
                current_price = cursor.execute(
                    'SELECT price FROM photos WHERE names=?', (product_code,)
                ).fetchone()[0]
                kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add('без изменений', btn_back)
                await message.answer('Текущая цена:\n' + current_price, reply_markup=kb)
            else:
                await message.answer('Введите цену', reply_markup=ReplyKeyboardMarkup(
                    resize_keyboard=True, row_width=2
                ).add(btn_back))
        except Exception:
            await message.answer('Введите цену', reply_markup=ReplyKeyboardMarkup(
                resize_keyboard=True, row_width=2
            ).add(btn_back))
    await FSMAdmin.next()


@dp.message_handler(state=FSMAdmin.display_price)
async def handle_admin_display_price(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод цены продукта.
    
    Сохраняет цену и, если изображение уже существует, предлагает оставить его без изменений.
    """
    async with state.proxy() as data:
        data['display_price'] = message.text.replace('₽', '') + '₽'
        try:
            code = str(cursor.execute(
                'SELECT id FROM "Ассортимент🗂" WHERE tastes== ?', (data["category"],)
            ).fetchone()[0])
            brand_code = code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(code), (data["brand"],)
            ).fetchone()[0])
            product_code = brand_code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(brand_code), (data["product_name"],)
            ).fetchone()[0])
            if cursor.execute(
                'SELECT count(*) FROM photos WHERE names = ?', (product_code,)
            ).fetchone()[0] != 0:
                current_photo = cursor.execute(
                    'SELECT photos FROM photos WHERE names=?', (product_code,)
                ).fetchone()[0]
                kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add('без изменений', 'без фото', btn_back)
                await message.answer(
                    f"Текущее изображение:\n{current_photo}\nСсылка на фото для {data['product_name']}\nhttps://ibb.org.ru/?lang=ru",
                    reply_markup=kb
                )
            else:
                await message.answer(
                    f"Введите ссылку на фото для {data['product_name']}\nhttps://ibb.org.ru/?lang=ru",
                    reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add('без фото', btn_back)
                )
        except Exception:
            await message.answer(
                f"Введите ссылку на фото для {data['product_name']}\nhttps://ibb.org.ru/?lang=ru",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add('без фото', btn_back)
            )
    await FSMAdmin.next()


@dp.message_handler(state=FSMAdmin.photo_url)
async def handle_admin_photo_url(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод ссылки на фото продукта.
    
    Сохраняет URL и выводит список вкусов, если они уже заданы, либо предлагает ввести их.
    """
    async with state.proxy() as data:
        data['photo_url'] = message.text
        try:
            code = str(cursor.execute(
                'SELECT id FROM "Ассортимент🗂" WHERE tastes== ?', (data["category"],)
            ).fetchone()[0])
            brand_code = code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(code), (data["brand"],)
            ).fetchone()[0])
            product_code = brand_code + '_' + str(cursor.execute(
                'SELECT id FROM "{}" WHERE tastes== ?'.format(brand_code), (data["product_name"],)
            ).fetchone()[0])
            tastes_str = ''
            for item in cursor.execute(f'SELECT tastes FROM "{product_code}"').fetchall():
                tastes_str += item[0] + ','
            kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            kb.add('без изменений', btn_back)
            await message.answer('Вкусы:\n' + tastes_str[:-1], reply_markup=kb)
        except Exception:
            await message.answer('Введите вкусы', reply_markup=ReplyKeyboardMarkup(
                resize_keyboard=True, row_width=2
            ).add(btn_back))
    await FSMAdmin.next()


@dp.message_handler(state=FSMAdmin.price_options)
async def handle_admin_price_options(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод вариантов цены или вкусов.
    
    В зависимости от ввода:
        - Добавляет новый ассортимент, бренд, продукт и их таблицы, если необходимо.
        - Обновляет или добавляет информацию в таблицу photos.
        - Добавляет варианты цены/вкусов в соответствующую таблицу.
    После обработки выводит итоговое сообщение с деталями созданного продукта.
    """
    async with state.proxy() as data:
        data['price_options'] = message.text
        if cursor.execute('SELECT count(*) FROM "Ассортимент🗂" WHERE tastes = ?', (data['category'],)).fetchone()[0] == 0:
            cursor.execute('INSERT INTO "Ассортимент🗂" (tastes) VALUES (?)', (data['category'],))
        code = str(cursor.execute(
            'SELECT id FROM "Ассортимент🗂" WHERE tastes== ?', (data["category"],)
        ).fetchone()[0])
        db.execute(f'CREATE TABLE IF NOT EXISTS "{code}" (tastes TEXT, id INTEGER PRIMARY KEY)')
        if cursor.execute('SELECT count(*) FROM "{}" WHERE tastes = ?'.format(code), (data['brand'],)).fetchone()[0] == 0:
            cursor.execute('INSERT INTO "{}" (tastes) VALUES (?)'.format(code), (data['brand'],))
        brand_code = code + '_' + str(cursor.execute(
            'SELECT id FROM "{}" WHERE tastes== ?'.format(code), (data["brand"],)
        ).fetchone()[0])
        db.execute(f'CREATE TABLE IF NOT EXISTS "{brand_code}" (tastes TEXT, id INTEGER PRIMARY KEY)')
        if cursor.execute('SELECT count(*) FROM "{}" WHERE tastes = ?'.format(brand_code), (data['product_name'],)).fetchone()[0] == 0:
            cursor.execute('INSERT INTO "{}" (tastes) VALUES (?)'.format(brand_code), (data['product_name'],))
        product_code = brand_code + '_' + str(cursor.execute(
            'SELECT id FROM "{}" WHERE tastes== ?'.format(brand_code), (data["product_name"],)
        ).fetchone()[0])
        db.execute(f'CREATE TABLE IF NOT EXISTS "{product_code}" (tastes TEXT, id INTEGER PRIMARY KEY)')
        if cursor.execute('SELECT count(*) FROM photos WHERE names = ?', (product_code,)).fetchone()[0] == 0:
            cursor.execute('INSERT INTO photos VALUES (?, ?, ?, ?)', (product_code, data['photo_url'], data['description'], data['display_price']))
        else:
            if data['photo_url'] != 'без изменений':
                cursor.execute('UPDATE photos SET photos=? WHERE names = ?', (data['photo_url'], product_code))
            if data['description'] != 'без изменений':
                cursor.execute('UPDATE photos SET desc=? WHERE names = ?', (data['description'], product_code))
            if data['display_price'].replace('₽', '') != 'без изменений':
                cursor.execute('UPDATE photos SET price=? WHERE names = ?', (data['display_price'], product_code))
        if data['price_options'] != 'без изменений':
            price_str = str(data['price_options']).replace(', ', ',').replace(' , ', ',').replace(' ,', ',').replace(',,', ',')
            for price_option in price_str.split(','):
                cursor.execute('INSERT INTO "{}" (tastes) VALUES (?)'.format(product_code), (price_option,))
        db.commit()
        try:
            photo_record = cursor.execute('SELECT * FROM photos WHERE names=?', (product_code,)).fetchone()
            tastes_str = ''
            for item in cursor.execute(f'SELECT tastes FROM "{photo_record[0]}"').fetchall():
                tastes_str += item[0] + ','
            await message.answer(
                f"*{data['product_name']}*\n{photo_record[2]}\n*со вкусами:* {tastes_str[:-1]}\n*ценой в* {photo_record[3]}\n*обновлен*[​]({photo_record[1]})",
                parse_mode='Markdown'
            )
        except Exception:
            if data['photo_url'] == 'без фото':
                await message.answer(
                    f"*{data['product_name']}*\n{data['description']}\n*со вкусами:* {data['price_options']}\n*ценой в* {data['display_price']}\n*создан*[​]({data['photo_url']})",
                    parse_mode='Markdown'
                )
            else:
                await message.answer(
                    f"*{data['product_name']}*\n{data['description']}\n*со вкусами:* {data['price_options']}\n*ценой в* {data['display_price']}\n*создан*",
                    parse_mode='Markdown'
                )
    await state.finish()


@dp.callback_query_handler(text='Удалить')
async def handle_delete_initiate(callback_query: types.CallbackQuery):
    """
    Инициализирует процесс удаления продуктов и брендов.
    
    Выводит клавиатуру с ассортиментом для выбора.
    """
    kb = InlineKeyboardMarkup(row_width=2)
    for item in cursor.execute('SELECT * FROM "Ассортимент🗂"').fetchall():
        kb.insert(InlineKeyboardButton(item[0], callback_data=f'delAssort_{item[1]}'))
    kb.add(btn_back)
    await callback_query.message.edit_text('Ассортимент🗂')
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()


@dp.callback_query_handler(Text(startswith='delAssort_'))
async def handle_delete_selection(callback_query: types.CallbackQuery):
    """
    Обрабатывает выбор ассортимента для удаления.
    
    Выводит список брендов в выбранном ассортименте.
    """
    assortment_id = callback_query.data[len("delAssort_"):]
    kb = InlineKeyboardMarkup(row_width=2)
    for item in cursor.execute(f'SELECT * FROM "{assortment_id}"').fetchall():
        kb.insert(InlineKeyboardButton(item[0], callback_data=f'delBrand_{assortment_id}_{item[1]}'))
    kb.add(InlineKeyboardButton('<<Назад', callback_data='Удалить'))
    text = cursor.execute('SELECT tastes FROM "Ассортимент🗂" WHERE id=?', (assortment_id,)).fetchone()[0]
    await callback_query.message.edit_text(text)
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()


@dp.callback_query_handler(Text(startswith='delBrand_'))
async def handle_delete_brand_selection(callback_query: types.CallbackQuery):
    """
    Обрабатывает выбор бренда для удаления.
    
    Выводит список товаров для выбранного бренда и опции удаления.
    """
    data = callback_query.data[len("delBrand_"):]
    kb = InlineKeyboardMarkup(row_width=2)
    query = cursor.execute(f'SELECT * FROM "{data}"')
    for item in query.fetchall():
        kb.add(InlineKeyboardButton(item[0], callback_data=f'delItem_{data}_{item[1]}'))
    kb.add(InlineKeyboardButton('Удалить ' + decrypt_code(data), callback_data='delComplete_' + data))
    kb.add(InlineKeyboardButton('<<Назад', callback_data=f'delAssort_' + "_".join(data.split("_")[:-1])))
    text = decrypt_code(data)
    await callback_query.message.edit_text(text)
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()


@dp.callback_query_handler(Text(startswith='delItem_'))
async def handle_delete_item_selection(callback_query: types.CallbackQuery):
    """
    Обрабатывает выбор конкретного товара для удаления.
    
    Выводит опции для удаления отдельного товара.
    """
    kb = InlineKeyboardMarkup(row_width=2)
    data = callback_query.data[len("delItem_"):]
    for item in cursor.execute(f'SELECT * FROM "{data}"').fetchall():
        kb.insert(InlineKeyboardButton(f'Удалить {item[0]}', callback_data=f'delSingle_{data}_{item[1]}'))
    kb.add(InlineKeyboardButton('Удалить ' + decrypt_code(data), callback_data='delAlternate_' + data))
    kb.add(InlineKeyboardButton('<<Назад', callback_data=f'delBrand_' + "_".join(data.split("_")[:-1])))
    await callback_query.message.edit_text(decrypt_code(data))
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer()


@dp.callback_query_handler(Text(startswith='delComplete_'))
async def handle_delete_complete_selection(callback_query: types.CallbackQuery):
    """
    Выполняет полное удаление бренда или линейки.
    
    Удаляет записи из таблицы photos, сбрасывает таблицы и обновляет родительскую таблицу.
    """
    data = callback_query.data[len("delComplete_"):]
    del_name = decrypt_code(data)
    history_text = cursor.execute(
        'SELECT tastes FROM "Ассортимент🗂" WHERE id=?', (data.split('_')[0],)
    ).fetchone()[0]
    await callback_query.message.edit_text(history_text)
    await callback_query.answer(del_name + ' удален')
    for item in cursor.execute(f'SELECT * FROM "{data}"').fetchall():
        cursor.execute('DELETE FROM photos WHERE names = ?', (item[0],))
        db.commit()
        cursor.execute('DROP TABLE "{}_{}"'.format(data, item[1]))
        db.commit()
    cursor.execute('DROP TABLE "{}"'.format(data))
    db.commit()
    cursor.execute('DELETE FROM "{}" WHERE tastes = ?'.format(get_table_name(data)), (del_name,))
    db.commit()
    kb = InlineKeyboardMarkup(row_width=2)
    for item in cursor.execute(f'SELECT * FROM "{get_table_name(data)}"').fetchall():
        kb.insert(InlineKeyboardButton(item[0], callback_data=f'delBrand_{data}_{item[1]}'))
    kb.add(InlineKeyboardButton('<<Назад', callback_data='Удалить'))
    await callback_query.message.edit_reply_markup(kb)


@dp.callback_query_handler(Text(startswith='delAlternate_'))
async def handle_delete_alternate(callback_query: types.CallbackQuery):
    """
    Альтернативное удаление: удаляет таблицу товара и соответствующие записи.
    """
    kb = InlineKeyboardMarkup(row_width=2)
    data = callback_query.data[len("delAlternate_"):]
    del_name = decrypt_code(data)
    cursor.execute('DELETE FROM photos WHERE names = ?', (del_name,))
    db.commit()
    cursor.execute('DROP TABLE "{}"'.format(data))
    db.commit()
    cursor.execute('DELETE FROM "{}" WHERE tastes = ?'.format(get_table_name(data)), (del_name,))
    db.commit()
    query = cursor.execute(f'SELECT * FROM "{get_table_name(data)}"')
    for item in query.fetchall():
        kb.add(InlineKeyboardButton(item[0], callback_data=f'delItem_{get_table_name(data)}_{item[1]}'))
    kb.add(InlineKeyboardButton('Удалить ' + decrypt_code(get_table_name(data)), callback_data='delComplete_' + get_table_name(data)))
    kb.add(InlineKeyboardButton('<<Назад', callback_data=f'delAssort_' + get_table_name(get_table_name(data))))
    await callback_query.answer(f'{del_name} удален')
    await callback_query.message.edit_text(decrypt_code(get_table_name(data)))
    await callback_query.message.edit_reply_markup(kb)


@dp.callback_query_handler(Text(startswith='delSingle_'))
async def handle_delete_individual_item(callback_query: types.CallbackQuery):
    """
    Выполняет индивидуальное удаление товара.
    
    Удаляет запись из таблицы, обновляет клавиатуру и уведомляет об удалении.
    """
    data = callback_query.data[len("delSingle_"):]
    del_name = decrypt_code(data)
    cursor.execute('DELETE FROM "{}" WHERE tastes = ?'.format(get_table_name(data)), (del_name,))
    db.commit()
    kb = InlineKeyboardMarkup(row_width=2)
    for item in cursor.execute(f'SELECT * FROM "{get_table_name(data)}"').fetchall():
        kb.insert(InlineKeyboardButton(f'Удалить {item[0]}', callback_data=f'delSingle_{get_table_name(data)}_{item[1]}'))
    kb.add(InlineKeyboardButton('Удалить ' + decrypt_code(get_table_name(data)), callback_data='delAlternate_' + get_table_name(data)))
    kb.add(InlineKeyboardButton('<<Назад', callback_data=f'delBrand_' + get_table_name(get_table_name(data))))
    await callback_query.message.edit_reply_markup(kb)
    await callback_query.answer(f'{del_name} удален')


@dp.callback_query_handler(text='Добавитьакцию', state=None)
async def handle_add_sale_initiate(callback_query: types.CallbackQuery):
    """
    Инициализирует процесс добавления акции.
    
    Отправляет сообщение с запросом названия акции.
    """
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(btn_back)
    await callback_query.message.edit_text('Введите название акции')
    await callback_query.message.edit_reply_markup(kb)
    await FSMSale.sale_name.set()
    await callback_query.answer()


@dp.message_handler(state=FSMSale.sale_name)
async def handle_sale_name(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод названия акции.
    
    Сохраняет название акции и переходит к вводу описания.
    """
    async with state.proxy() as data:
        data['sale_name'] = message.text
    await FSMSale.sale_description.set()
    await message.answer('Введите описание акции', reply_markup=ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=1
    ).add(btn_back))


@dp.message_handler(state=FSMSale.sale_description)
async def handle_sale_desc(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод описания акции и сохраняет данные.
    
    Добавляет акцию в базу данных и завершает процесс.
    """
    async with state.proxy() as data:
        data['sale_description'] = message.text
        cursor.execute('INSERT INTO sales (positions, desc) VALUES (?, ?)', (data['sale_name'], data['sale_description']))
    db.commit()
    await message.answer(f'Акция {data["sale_name"]} создана')
    await state.finish()
