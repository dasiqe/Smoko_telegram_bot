# db.py

import sqlite3
from config import DB_NAME

# Подключение к базе. Опция check_same_thread=False помогает при использовании одного соединения в разных частях бота.
db = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = db.cursor()

def init_db():
    # Создаем таблицы, если их нет
    cursor.execute('CREATE TABLE IF NOT EXISTS "Ассортимент🗂" (tastes TEXT, id INTEGER PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS photos (names TEXT, photos TEXT, desc TEXT, price TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS sales (positions TEXT, desc TEXT, id INTEGER PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedbacks (chat INTEGER, message INTEGER, product TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS otz (chat INTEGER, message INTEGER, product TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER, history TEXT DEFAULT NULL, first_client INTEGER DEFAULT 1, first_pressed INTEGER DEFAULT 0, spend INTEGER DEFAULT 0, start INTEGER DEFAULT NULL, product TEXT DEFAULT NULL, ban INTEGER DEFAULT 0)')
    db.commit()

# Вызываем инициализацию при импорте этого модуля
init_db()

# db.py (дополнительно)
def get_table_name(code: str) -> str:
    return '_'.join(code.split('_')[:-1])

def decrypt_code(code: str) -> str:
    base_code = get_table_name(code)
    code_id = code.split('_')[-1]
    return cursor.execute(
        'SELECT tastes FROM "{}" WHERE id=?'.format(base_code),
        (code_id,)
    ).fetchone()[0]
