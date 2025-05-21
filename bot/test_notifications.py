#!/usr/bin/env python
import datetime
from database.db import init_db, clear_events, add_event, add_user
from handlers.notifications import send_notifications
import config

# Настроим тестовую БД
init_db()
clear_events()

# Создадим тестовое событие на дату, которая совпадает с today + DEFAULT_NOTIFY_DAYS
today = datetime.date.today()
notify_days = config.DEFAULT_NOTIFY_DAYS
target = today + datetime.timedelta(days=notify_days)
date_str = target.strftime("%d.%m.%Y")

add_event("Тестовое событие", date_str, "https://example.com")

# Создадим тестового пользователя с произвольным user_id
add_user(user_id=123456789, phone_hash="fakehash", notify_days=notify_days)


# Подготовим «контекст» с «ботом», который вместо отправки сообщения печатает его
class DummyBot:
    def send_message(self, chat_id, text, parse_mode=None):
        print(f"[BOT → {chat_id}]: {text}")


class DummyContext:
    bot = DummyBot()


# Запускаем проверку уведомлений
send_notifications(DummyContext())
