from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove, ParseMode
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    Filters,
)

from handlers.auth import MAIN_MENU, start
import database.db as db
import re
import math

EVENTS_PER_PAGE = 10
NAV_BACK, NAV_HOME, NAV_NEXT = "⬅️ Назад", "🏠 На главную", "➡️ Вперед"
BROWSE = 0      # состояние ConversationHandler


def _send_events_page(update: Update, context: CallbackContext, page: int) -> None:
    """Формирует и отправляет страницу с олимпиадами + навигацию."""
    user_id = update.effective_user.id

    # при первом показе сохраняем весь список в user_data
    if "all_events" not in context.user_data:
        context.user_data["all_events"] = db.get_upcoming_events(limit=9999)

    events = context.user_data["all_events"]
    total_pages = math.ceil(len(events) / EVENTS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    context.user_data["events_page"] = page

    start_idx = page * EVENTS_PER_PAGE
    slice_ = events[start_idx:start_idx + EVENTS_PER_PAGE]
    context.user_data["events_slice"] = [ev[0] for ev in slice_]      # id-шники страницы

    lines = [f"📌 *Все олимпиады*  (стр. {page+1}/{total_pages})",
             "Напишите номера через запятую, чтобы подписаться:"]
    subs_now = {ev_id for ev_id, *_ in db.get_user_subscriptions(user_id)}

    for i, (ev_id, name, date, *_rest) in enumerate(slice_, start=1):
        star = "⭐ " if ev_id in subs_now else ""
        lines.append(f"{i}. {date} — {star}{name}")

    # строим временную клавиатуру навигации
    nav_row = [b for b in (
        NAV_BACK if page else None,
        NAV_HOME,
        NAV_NEXT if page < total_pages - 1 else None
    ) if b]

    reply_markup = ReplyKeyboardMarkup([nav_row], resize_keyboard=True, one_time_keyboard=False)
    text = "\n".join(lines)

    # показываем как новое сообщение (проще, чем редактировать)
    update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


def all_events_start(update: Update, context: CallbackContext) -> int:
    """Точка входа – команда /events или кнопка «📌 Все олимпиады»."""
    # очищаем возможные остатки старого просмотра
    for key in ("all_events", "events_page", "events_slice"):
        context.user_data.pop(key, None)

    _send_events_page(update, context, page=0)
    return BROWSE


def all_events_handle(update: Update, context: CallbackContext) -> int:
    """Обрабатывает либо ввод номеров, либо навигационные кнопки."""
    text = update.message.text.strip()

    # --- НАВИГАЦИЯ ----------------------------------------------------------
    if text == NAV_BACK:
        _send_events_page(update, context, context.user_data["events_page"] - 1)
        return BROWSE

    if text == NAV_NEXT:
        _send_events_page(update, context, context.user_data["events_page"] + 1)
        return BROWSE

    if text == NAV_HOME:
        # возвращаем главное меню
        update.message.reply_text(
            "🏠 Главное меню",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
        )
        return ConversationHandler.END

    # --- ПОДПИСКА ПО НОМЕРАМ -----------------------------------------------
    if not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", text):
        update.message.reply_text("❗ Введите номера через запятую или воспользуйтесь кнопками.")
        return BROWSE

    user_id = update.effective_user.id
    slice_ids = context.user_data.get("events_slice", [])
    to_sub = []

    for part in text.split(","):
        idx = int(part.strip()) - 1
        if 0 <= idx < len(slice_ids):
            to_sub.append(slice_ids[idx])
        else:
            update.message.reply_text("❗ Нет такого номера на этой странице.")
            return BROWSE

    for ev_id in to_sub:
        db.subscribe_user(user_id, ev_id)

    update.message.reply_text("✅ Подписка оформлена.")
    # остаёмся на той же странице, чтобы пользователь мог продолжать
    _send_events_page(update, context, context.user_data["events_page"])
    return BROWSE


def all_events_cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "❌ Просмотр олимпиад завершён.",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# ConversationHandler, который мы экспортируем в main.py
events_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("events", all_events_start),
        MessageHandler(Filters.regex(r'^📌 Все олимпиады$'), all_events_start),
    ],
    states={
        BROWSE: [MessageHandler(Filters.text & ~Filters.command, all_events_handle)],
    },
    fallbacks=[CommandHandler("cancel", all_events_cancel)],
    allow_reentry=True,
)


def show_events(update: Update, context: CallbackContext) -> None:
    """Показывает 5 ближайших олимпиад коротким списком."""
    user_id = update.effective_user.id
    events = db.get_upcoming_events(limit=5)          # берём ближайшие 5
    subs = {ev_id for ev_id, *_ in db.get_user_subscriptions(user_id)}

    lines = ["📅 *Ближайшие олимпиады*:"]
    for ev_id, name, date, *_ in events:
        star = "⭐️ " if ev_id in subs else ""
        lines.append(f"{date} — {star}{name}")

    update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
