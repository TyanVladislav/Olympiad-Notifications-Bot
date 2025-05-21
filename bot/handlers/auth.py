# handlers/auth.py

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import CallbackContext

import config
from database.db import get_user, add_user
from utils.hash import hash_phone

# Главное меню после регистрации
MAIN_MENU = [
    ["📅 Ближайшие", "📌 Все олимпиады"],
    ["🔔 Подписки", "⚙️ Фильтры"],
    ["📖 История", "❓ Помощь"]
]


def start(update: Update, context: CallbackContext) -> None:
    """
    /start — если пользователь уже есть в БД, просто приветствуем и показываем меню,
    иначе — просим поделиться номером.
    """
    user_id = update.effective_user.id

    # Если уже зарегистрирован — выводим главное меню
    if get_user(user_id):
        update.message.reply_text(
            "👋 Снова здравствуйте! Вы уже зарегистрированы.\n"
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU, resize_keyboard=True, one_time_keyboard=False
            )
        )
        return

    # Иначе — запрашиваем контакт
    contact_button = KeyboardButton(
        text="📱 Отправить номер телефона",
        request_contact=True
    )
    update.message.reply_text(
        "Добро пожаловать! Чтобы зарегистрироваться, нажмите кнопку и поделитесь своим номером.",
        reply_markup=ReplyKeyboardMarkup(
            [[contact_button]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )


def handle_contact(update: Update, context: CallbackContext) -> None:
    """
    Обработка контакта: хешируем номер, сохраняем юзера и показываем главное меню.
    """
    contact = update.message.contact
    user_id = update.effective_user.id

    # Убедимся, что контакт действительно от этого же пользователя
    if not contact or contact.user_id != user_id:
        update.message.reply_text(
            "⚠️ Пожалуйста, нажмите именно кнопку и отправьте свой номер телефона."
        )
        return

    # Сохраняем нового пользователя
    phone_hash = hash_phone(contact.phone_number)
    add_user(user_id, phone_hash, config.DEFAULT_NOTIFY_DAYS)

    # Убираем клавиатуру запроса контакта и показываем главное меню
    update.message.reply_text(
        "✅ Вы успешно зарегистрированы!\n"
        "Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(
            MAIN_MENU, resize_keyboard=True, one_time_keyboard=False
        )
    )
