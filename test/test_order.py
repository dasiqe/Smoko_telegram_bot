# tests/test_order.py

import pytest
from aiogram.types import CallbackQuery, Message, Chat
from handlers.cart import handle_order_confirmation
from db import cursor, db

# Создаем необходимые таблицы для дешифровки кода
cursor.execute('CREATE TABLE IF NOT EXISTS "2" (tastes TEXT, id INTEGER PRIMARY KEY)')
cursor.execute('INSERT OR IGNORE INTO "2" (tastes, id) VALUES (?, ?)', ("MainTaste", 1))
cursor.execute('CREATE TABLE IF NOT EXISTS "2_1" (tastes TEXT, id INTEGER PRIMARY KEY)')
cursor.execute('INSERT OR IGNORE INTO "2_1" (tastes, id) VALUES (?, ?)', ("SecondaryTaste", 1))
cursor.execute('CREATE TABLE IF NOT EXISTS "2_1_1" (tastes TEXT, id INTEGER PRIMARY KEY)')
cursor.execute('INSERT OR IGNORE INTO "2_1_1" (tastes, id) VALUES (?, ?)', ("FullTaste", 2))
db.commit()


@pytest.mark.asyncio
async def test_order_confirmation():
    """
    Проверяем, что при оформлении заказа:
        - Корзина очищается и таблица пересоздаётся.
        - Поля history и spend обновляются.
    """
    user_id = 234567

    # Создаем запись в таблице id если нет
    cursor.execute(
        'INSERT OR IGNORE INTO id (users, history, spend) VALUES (?, ?, ?)',
        (str(user_id), "None", 0)
    )
    db.commit()

    # Создаем таблицу корзины и добавляем в неё товар
    cursor.execute(f'CREATE TABLE IF NOT EXISTS "{user_id}" (cart TEXT, price TEXT, count INTEGER)')
    db.commit()
    cursor.execute(
        f'INSERT INTO "{user_id}" (cart, price, count) VALUES (?, ?, ?)',
        ("2_1_1_2", "100₽", 3)
    )
    db.commit()

    dummy_callback_data = {
        "id": "test_order_cb",
        "from": {"id": user_id, "is_bot": False, "first_name": "OrderUser"},
        "message": {
            "message_id": 2,
            "date": 1633036800,
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "OrderUser"}
        },
        "data": "orderConfirm300"
    }
    callback_query = CallbackQuery(**dummy_callback_data)

    await handle_order_confirmation(callback_query)

    # Проверяем, что таблица корзины пересоздана
    result = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (str(user_id),)
    ).fetchone()
    assert result is not None, "Таблица корзины не пересоздана"

    # Проверяем, что корзина очищена
    item = cursor.execute(f'SELECT * FROM "{user_id}"').fetchone()
    assert item is None, "Корзина не очищена после заказа"

    # Проверяем, что spend обновился
    spend = cursor.execute('SELECT spend FROM id WHERE users=?', (str(user_id),)).fetchone()[0]
    assert spend == 300, f"Неверное значение spend, ожидалось 300, получили {spend}"

    # Проверяем, что history обновилось
    history = cursor.execute('SELECT history FROM id WHERE users=?', (str(user_id),)).fetchone()[0]
    assert history != "None", "Поле history не обновилось"
    assert "2_1_1_2" in history, "В history не добавился код товара"
    assert "На сумму: 300₽" in history, "В history нет итоговой суммы"
