# handlers/cart.py

"""Модуль для работы с корзиной покупок: отображение, изменение количества и оформление заказа.

Реализованы функции для обновления отображения корзины, навигации между товарами,
изменения количества товаров и финального оформления заказа с уведомлением администраторов.
"""

from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import dp, bot
from db import cursor, db, decrypt_code, get_table_name

async def update_cart_display(callback_query: types.CallbackQuery):
    """
    Обновляет и отображает содержимое корзины с информацией о товаре, цене и кнопками навигации.
    
    Применяет скидки в зависимости от статуса пользователя, а также выводит изображение товара с описанием.
    
    Примечания:
        - Расшифровка кодов товара производится с помощью функции decrypt_code.
        - Индекс текущего товара извлекается из callback_data, которая имеет формат "cart<number>".
    """
    try:
        kb = InlineKeyboardMarkup(row_width=4)
        cart_items = cursor.execute('SELECT * FROM {} '.format(f'"{callback_query.from_user.id}"')).fetchall()
        index = int(callback_query.data[4:]) - 1  # Извлечение номера элемента корзины из строки типа "cart<number>"
        cart_item = cart_items[index]
        main_taste = decrypt_code(cart_item[0])
        taste_prev = decrypt_code('_'.join(cart_item[0].split('_')[:-1]))
        taste_prev2 = decrypt_code('_'.join(cart_item[0].split('_')[:-2]))
        # Получаем данные для отображения фотографии товара
        photo_data = cursor.execute('SELECT * FROM photos WHERE names == ?', ('_'.join(cart_item[0].split('_')[:-1]),)).fetchone()
        price = int(cart_item[1][:-1])
        # Применяем скидку 10% для первого заказа
        if cursor.execute('SELECT first_pressed FROM id WHERE users = ?', (str(callback_query.from_user.id),)).fetchone()[0] == 1:
            price = int(price * 0.9)
        # Применяем скидку 5% для пользователей, потративших более 5000₽
        if cursor.execute('SELECT spend FROM id WHERE users = ?', (str(callback_query.from_user.id),)).fetchone()[0] >= 5000:
            price = int(price * 0.95)
        kb.add(InlineKeyboardButton(f'{price}*{cart_item[2]}={price * int(cart_item[2])}₽', callback_data='rubles'))
        cart_decrypted = [decrypt_code(item[0])
                            for item in cursor.execute("SELECT cart FROM {} ".format(f'"{callback_query.from_user.id}"')).fetchall()]
        kb.add(
            InlineKeyboardButton('🗑️', callback_data=f'delCart{cart_item[0]}'),
            InlineKeyboardButton('🔽', callback_data='dec' + cart_item[0]),
            InlineKeyboardButton(cart_item[2], callback_data='quantity'),
            InlineKeyboardButton('🔼', callback_data='inc' + cart_item[0])
        )
        kb.add(
            InlineKeyboardButton('◀️', callback_data='moveLeft' + cart_item[0]),
            InlineKeyboardButton(f'{int(cart_decrypted.index(main_taste)) + 1} из {len(cart_decrypted)}', callback_data='position'),
            InlineKeyboardButton('▶️', callback_data='moveRight' + cart_item[0])
        )
        total_price = 0
        for item in cursor.execute('SELECT * FROM {} '.format(f'"{callback_query.from_user.id}"')).fetchall():
            total_price += int(item[1][:-1]) * int(item[2])
        # Применение скидок к общей сумме заказа
        if cursor.execute('SELECT first_pressed FROM id WHERE users = ?', (str(callback_query.from_user.id),)).fetchone()[0] == 1:
            total_price = int(total_price * 0.9)
        if cursor.execute('SELECT spend FROM id WHERE users = ?', (str(callback_query.from_user.id),)).fetchone()[0] >= 5000:
            total_price = int(total_price * 0.95)
        kb.add(InlineKeyboardButton(f'Оформить заказ - {total_price}₽', callback_data=f'orderConfirm{total_price}'))
        kb.add(InlineKeyboardButton('Меню', callback_data='back'))
        price_photo = int(photo_data[-1][:-1])
        # Применяем аналогичные скидки к цене товара на фото
        if cursor.execute('SELECT first_pressed FROM id WHERE users = ?', (str(callback_query.from_user.id),)).fetchone()[0] == 1:
            price_photo = int(price_photo * 0.9)
        if cursor.execute('SELECT spend FROM id WHERE users = ?', (str(callback_query.from_user.id),)).fetchone()[0] >= 5000:
            price_photo = int(price_photo * 0.95)
        await callback_query.message.edit_text(
            f'[​]({photo_data[1]})*{taste_prev2} {taste_prev} {main_taste}*\n*Описание:*\n{photo_data[2]}\n*Цена:*{price_photo}₽',
            parse_mode='Markdown'
        )
        await callback_query.message.edit_reply_markup(reply_markup=kb)
        await callback_query.answer()
    except Exception:
        await callback_query.answer('Товар в вашей корзине закончился.', show_alert=True)
        # Здесь можно добавить возврат в главное меню при отсутствии товара

@dp.callback_query_handler(Text(startswith='cart'))
async def handle_cart_display(callback_query: types.CallbackQuery):
    """
    Проверяет корректность товаров в корзине: удаляет несуществующие позиции и обновляет отображение корзины.
    
    Используется для поддержки актуальности данных в корзине.
    """
    for item in cursor.execute('SELECT * FROM {} '.format(f'"{callback_query.from_user.id}"')).fetchall():
        try:
            # Если товар не найден в соответствующей таблице товаров, удаляем его из корзины
            if cursor.execute('SELECT count(*) FROM {} WHERE id=?'.format(f'"{get_table_name(item[0])}"'),
                                (item[0].split('_')[-1],)).fetchone()[0] != 1:
                cursor.execute('DELETE FROM {} WHERE cart=?'.format(f'"{callback_query.from_user.id}"'), (item[0],))
        except Exception:
            cursor.execute('DELETE FROM {} WHERE cart=?'.format(f'"{callback_query.from_user.id}"'), (item[0],))
        db.commit()
    await update_cart_display(callback_query)

@dp.callback_query_handler(Text('rubles'))
async def handle_total_sum_info(callback_query: types.CallbackQuery):
    """
    Показывает информацию о том, как рассчитывается общая сумма заказа.
    """
    await callback_query.answer('Общая сумма за количество')

@dp.callback_query_handler(Text(startswith='inc'))
async def handle_increase_quantity(callback_query: types.CallbackQuery):
    """
    Увеличивает количество выбранного товара в корзине и обновляет отображение.
    
    Извлекает текущий счетчик и увеличивает его на 1.
    """
    cart_list = [item[0] for item in cursor.execute("SELECT cart FROM {} ".format(f'"{callback_query.from_user.id}"')).fetchall()]
    current_count = int(cursor.execute('SELECT count FROM {} WHERE cart=?'.format(f'"{callback_query.from_user.id}"'),
                                        (callback_query.data[len("inc"):],)).fetchone()[0])
    cursor.execute('UPDATE {} SET count = ? WHERE cart=?'.format(f'"{callback_query.from_user.id}"'),
                    (str(current_count + 1), callback_query.data[len("inc"):]))
    db.commit()
    new_index = str(int(cart_list.index(callback_query.data[len("inc"):])) + 1)
    # Обновляем callback_data, чтобы отобразить следующий элемент корзины
    callback_query.data = 'cart' + new_index
    await update_cart_display(callback_query)

@dp.callback_query_handler(Text(startswith='dec'))
async def handle_decrease_quantity(callback_query: types.CallbackQuery):
    """
    Уменьшает количество выбранного товара в корзине, не позволяя значению опуститься ниже 1.
    
    Если количество равно 1, выводится уведомление о невозможности уменьшения.
    """
    cart_list = [item[0] for item in cursor.execute("SELECT cart FROM {} ".format(f'"{callback_query.from_user.id}"')).fetchall()]
    current_count = int(cursor.execute('SELECT count FROM {} WHERE cart=?'.format(f'"{callback_query.from_user.id}"'),
                                        (callback_query.data[len("dec"):],)).fetchone()[0])
    if current_count == 1:
        await callback_query.answer('Меньше некуда. Просто удалите позицию.', show_alert=True)
    else:
        cursor.execute('UPDATE {} SET count=? WHERE cart=?'.format(f'"{callback_query.from_user.id}"'),
                        (current_count - 1, callback_query.data[len("dec"):]))
        db.commit()
    new_index = str(int(cart_list.index(callback_query.data[len("dec"):])) + 1)
    callback_query.data = 'cart' + new_index
    await update_cart_display(callback_query)

@dp.callback_query_handler(Text(startswith='moveLeft'))
async def handle_move_left_in_cart(callback_query: types.CallbackQuery):
    """
    Перемещает отображение корзины на предыдущий товар.
    
    Извлекает индекс текущего товара и корректирует его для перехода к предыдущему элементу.
    """
    cart_list = [item[0] for item in cursor.execute("SELECT cart FROM {} ".format(f'"{callback_query.from_user.id}"')).fetchall()]
    index = cart_list.index(callback_query.data[len("moveLeft"):])
    if index + 1 == 1:
        callback_query.data = 'cart' + str(len(cart_list))
    else:
        callback_query.data = 'cart' + str(index)
    await update_cart_display(callback_query)

@dp.callback_query_handler(Text(startswith='moveRight'))
async def handle_move_right_in_cart(callback_query: types.CallbackQuery):
    """
    Перемещает отображение корзины на следующий товар.
    
    Если достигнут конец списка, переходит к первому элементу.
    """
    cart_list = [item[0] for item in cursor.execute("SELECT cart FROM {} ".format(f'"{callback_query.from_user.id}"')).fetchall()]
    index = cart_list.index(callback_query.data[len("moveRight"):])
    if index + 1 == len(cart_list):
        callback_query.data = 'cart1'
    else:
        callback_query.data = 'cart' + str(index + 2)
    await update_cart_display(callback_query)

@dp.callback_query_handler(Text('position'))
async def handle_cart_position_info(callback_query: types.CallbackQuery):
    """
    Выводит сообщение с информацией о текущей позиции товара в корзине.
    """
    await callback_query.answer('Позиция в корзине')

@dp.callback_query_handler(Text(startswith='delCart'))
async def handle_delete_from_cart(callback_query: types.CallbackQuery):
    """
    Удаляет выбранный товар из корзины и обновляет отображение.
    
    Если после удаления остаётся более одного товара – обновляется отображение, иначе выводится уведомление об пустой корзине.
    """
    cart_list = [item[0] for item in cursor.execute("SELECT cart FROM {} ".format(f'"{callback_query.from_user.id}"')).fetchall()]
    cursor.execute('DELETE FROM {} WHERE cart=?'.format(f'"{callback_query.from_user.id}"'), (callback_query.data[len("delCart"):],))
    db.commit()
    if len(cart_list) > 1:
        index = cart_list.index(callback_query.data[len("delCart"):])
        if index + 1 == len(cart_list):
            callback_query.data = 'cart1'
        else:
            callback_query.data = 'cart' + str(index + 1)
        await update_cart_display(callback_query)
    else:
        await callback_query.answer('Корзина опустела')

@dp.callback_query_handler(Text(startswith='orderConfirm'))
async def handle_order_confirmation(callback_query: types.CallbackQuery):
    """
    Оформляет заказ:
        - Собирает детали заказа из корзины.
        - Обновляет историю покупок и сумму, потраченную пользователем.
        - Уведомляет администраторов о новом заказе.
        - Сбрасывает корзину, создавая её заново.
    
    Дополнительные комментарии:
        - Для формирования описания заказа используется расшифровка кодов товара.
        - Если в callback_data не удалось извлечь сумму, применяется значение 0.
    """
    import datetime
    order_details = ''
    user_id = str(callback_query.from_user.id)
    
    # Формирование деталей заказа из элементов корзины
    for item in cursor.execute('SELECT * FROM {} '.format(f'"{user_id}"')).fetchall():
        # Разбиваем код товара для получения описания через функцию decrypt_code
        main_taste = decrypt_code('_'.join(item[0].split('_')[:-2]))
        secondary_taste = decrypt_code('_'.join(item[0].split('_')[:-1]))
        full_taste = decrypt_code(item[0])
        
        # Получаем текущее значение поля product из таблицы пользователя
        prod_row = cursor.execute('SELECT product FROM id WHERE users=?', (user_id,)).fetchone()
        current_product = prod_row[0] if prod_row is not None else None
        
        if current_product and current_product not in [None, '', 'None']:
            new_product = f'{main_taste} {secondary_taste} {full_taste},' + current_product
            cursor.execute('UPDATE id SET product=? WHERE users=?', (new_product, user_id))
        else:
            cursor.execute('UPDATE id SET product=? WHERE users=?', (f'{main_taste} {secondary_taste} {full_taste},', user_id))
        db.commit()
        order_details += f'{main_taste} {secondary_taste} {full_taste} - {item[-1]}шт.\n\n'
    
    # Извлечение общей суммы заказа из callback_data
    try:
        price_total = int(callback_query.data[len("orderConfirm"):])
    except Exception:
        price_total = 0
    
    # Получение стартового сообщения для дальнейшей пересылки админам
    start_row = cursor.execute('SELECT start FROM id WHERE users=?', (user_id,)).fetchone()
    msg_val = start_row[0] if start_row is not None else None
    
    # Уведомление администраторов о заказе
    if msg_val is not None:
        try:
            for admin in cursor.execute('SELECT users FROM id').fetchall():
                admin_id = admin[0]
                await bot.forward_message(admin_id, callback_query.from_user.id, msg_val)
                await bot.send_message(
                    admin_id,
                    f'|\n@{callback_query.from_user.username}:\n{order_details}На сумму: {price_total}₽',
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton('Спросить c дурака', callback_data=f'askManager {user_id}')
                    )
                )
        except Exception:
            pass
    else:
        try:
            for admin in cursor.execute('SELECT users FROM id').fetchall():
                admin_id = admin[0]
                await bot.send_message(
                    admin_id,
                    f'@{callback_query.from_user.username}:\n{order_details}На сумму: {price_total}₽',
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton('Спросить c дурака', callback_data=f'askManager {user_id}')
                    )
                )
        except Exception:
            pass

    await callback_query.answer('Спасибо за заказ, менеджер скоро свяжется с вами', show_alert=True)
    
    # Обновление истории заказов пользователя
    history_row = cursor.execute('SELECT history FROM id WHERE users=?', (user_id,)).fetchone()
    current_history = history_row[0] if history_row is not None else None
    new_history = datetime.datetime.now().strftime("%d-%m-%y") + ':\n' + order_details + f'На сумму: {price_total}₽'
    if current_history is None or current_history in ['', 'None']:
        cursor.execute('UPDATE id SET history=? WHERE users=?', (new_history, user_id))
    else:
        cursor.execute('UPDATE id SET history=? WHERE users=?', (new_history + '\n——————————————————-\n' + current_history, user_id))
    
    # Сброс флага первого заказа, если он был активирован
    first_pressed_row = cursor.execute('SELECT first_pressed FROM id WHERE users=?', (user_id,)).fetchone()
    if first_pressed_row and first_pressed_row[0] == 1:
        cursor.execute('UPDATE id SET first_pressed=0 WHERE users=?', (user_id,))
    
    # Обновляем сумму, потраченную пользователем
    cursor.execute('UPDATE id SET spend=spend+? WHERE users=?', (price_total, user_id))
    
    # Очистка корзины: удаляем таблицу корзины и создаём её заново
    cursor.execute('DROP TABLE {} '.format(f'"{user_id}"'))
    db.commit()
    cursor.execute('CREATE TABLE IF NOT EXISTS {} (cart TEXT, price TEXT, count INTEGER)'.format(f'"{user_id}"'))
    db.commit()
