import os

# Токен Telegram-бота (читается из переменной окружения BOT_TOKEN)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Количество дней до события, за которое отправляется уведомление по умолчанию
DEFAULT_NOTIFY_DAYS: int = int(os.getenv("DEFAULT_NOTIFY_DAYS", 3))

# Путь к файлу базы данных SQLite
DB_PATH: str = os.getenv("DB_PATH", "database/events.db")
