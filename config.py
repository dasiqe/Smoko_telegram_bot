# config.py

import os
from dotenv import load_dotenv

load_dotenv()  # Читает файл .env

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = set(map(int, os.getenv('ADMIN_IDS').split(',')))
DB_NAME = 'Products.db'