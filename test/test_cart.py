# tests/test_cart.py

import pytest
from aiogram.types import CallbackQuery, Message, Chat
from handlers.assortment import handle_add_to_cart
from db import cursor, db

@pytest.mark.asyncio
async def test_add_new_item_to_cart():
    """
    Проверяем, что при первом добавлении товара
    запись появляется в таблице корзины с count=1.
    """
    user_id = 123456
    cursor.execute(f'CREATE TABLE IF NOT EXISTS "{user_id}" (cart TEXT, price TEXT, count INTEGER)')
    db.commit()

    # Добавляем запись в photos
    cursor.execute(
        'INSERT OR IGNORE INTO photos (names, photos, desc, price) VALUES (?, ?, ?, ?)',
        ("2_1_1", "без фото", "Test product", "100₽")
    )
    db.commit()

    # Создаем фиктивный запрос
    dummy_callback_data = {
        "id": "test_cb_id",
        "from": {"id": user_id, "is_bot": False, "first_name": "TestUser"},
        "message": {
            "message_id": 1,
            "date": 1633036800,  # валидный timestamp
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "TestUser"}
        },
        "data": "addCart_2_1_1_2"
    }
    callback_query = CallbackQuery(**dummy_callback_data)
    
    await handle_add_to_cart(callback_query)

    # Проверяем, что товар добавлен в корзину
    item = cursor.execute(
        f'SELECT cart, price, count FROM "{user_id}" WHERE cart=?',
        ("2_1_1_2",)
    ).fetchone()
    assert item is not None, "Товар не добавился в корзину"
    assert item[0] == "2_1_1_2", "Некорректный код товара в корзине"
    assert item[1] == "100₽", "Некорректная цена товара"
    assert item[2] == 1, "Количество должно быть 1 при первом добавлении"

@pytest.mark.asyncio
async def test_add_existing_item_to_cart():
    """
    Проверяем, что при повторном добавлении того же товара
    увеличивается поле count.
    """
    user_id = 123456
    dummy_callback_data = {
        "id": "test_cb_id_2",
        "from": {"id": user_id, "is_bot": False, "first_name": "TestUser"},
        "message": {
            "message_id": 2,
            "date": 1633036800,
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "TestUser"}
        },
        "data": "addCart_2_1_1_2"
    }
    callback_query = CallbackQuery(**dummy_callback_data)
    
    await handle_add_to_cart(callback_query)

    item = cursor.execute(
        f'SELECT cart, price, count FROM "{user_id}" WHERE cart=?',
        ("2_1_1_2",)
    ).fetchone()
    assert item is not None, "Товар должен существовать"
    assert item[2] == 2, f"Ожидали count=2, а получили {item[2]}"
