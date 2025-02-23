# Smoko Telegram Bot

Этот репозиторий содержит телеграм-бота для управления ассортиментом, корзиной, акциями и отзывами.

## Установка

1. Клонируйте репозиторий:

    ```bash
    git clone https://github.com/username/smoko_telegram_bot.git
    ```

2. Перейдите в директорию проекта:

    ```bash
    cd smoko_telegram_bot
    ```

3. Установите зависимости:

    ```bash
    pip install -r requirements.txt
    ```

4. Создайте файл `.env` (или используйте переменные окружения) с токеном бота:

    ```env
    BOT_TOKEN="ТВОЙ_ТОКЕН"
    ADMIN_IDS="TELEGRAM_ID_1,TELEGRAM_ID_2"
    ```

    *Файл `.env` не попадает в репозиторий, чтобы не светить секреты.*

5. При необходимости настройте `config.py` или другую конфигурацию.

## Запуск бота

```bash
python main.py
