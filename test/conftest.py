# tests/conftest.py

import os
import sys


# Добавляем корень проекта в PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot import bot
from aiogram import Bot

# Устанавливаем текущий бот
Bot.set_current(bot)
