from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
import database.db as db
import re

# состояния разговора
ASK_SUB, ASK_UNSUB = range(2)   # 0 и 1


# ─────────────────── ПОДПИСКИ ПОЛЬЗОВАТЕЛЯ ────────────────────
def show_subscriptions(update: Update, context: CallbackContext) -> int:
    """Выводит текущие подписки и просит ввести номера для отписки."""
    user_id = update.effective_user.id
    subs = db.get_user_subscriptions(user_id)

    if not subs:
        update.message.reply_text("❕ Вы не подписаны ни на одну олимпиаду.")
        return ConversationHandler.END

    lines = ["🔖 *Ваши подписки:*"]
    for i, (ev_id, name, date) in enumerate(subs, start=1):
        lines.append(f"{i}. {date} — {name}")
    lines.append("\nВведите номера через запятую (или 0 — отмена):")

    update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    context.user_data["subs_list"] = [ev_id for ev_id, *_ in subs]
    return ASK_UNSUB


def unsubscribe_save(update: Update, context: CallbackContext) -> int:
    """Обрабатывает введённые номера, выполняет отписку."""
    text = update.message.text.strip()

    if text == "0":
        update.message.reply_text("❌ Отмена.")
        return ConversationHandler.END

    if not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", text):
        update.message.reply_text("❗ Введите номера через запятую.")
        return ASK_UNSUB

    subs_ids = context.user_data.get("subs_list", [])
    to_unsub = []
    for part in text.split(","):
        idx = int(part.strip()) - 1
        if 0 <= idx < len(subs_ids):
            to_unsub.append(subs_ids[idx])
        else:
            update.message.reply_text("❗ Нет такого номера.")
            return ASK_UNSUB

    for ev_id in to_unsub:
        db.unsubscribe_user(update.effective_user.id, ev_id)

    update.message.reply_text("✅ Вы отписались от выбранных олимпиад.")
    return ConversationHandler.END


# ───────────────────── СПИСОК ДОСТУПНЫХ ОЛИМПИАД ─────────────────────
def subscribe_prompt(update: Update, context: CallbackContext) -> int:
    """Показывает события, на которые можно подписаться."""
    events = db.get_upcoming_events(limit=100)

    lines = ["✨ *Доступные олимпиады:*"]
    for i, (ev_id, name, date, *_rest) in enumerate(events, start=1):
        lines.append(f"{i}. {date} — {name}")
    lines.append("\nВведите номера через запятую (или 0 — отмена):")

    update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    context.user_data["subs_candidates"] = [ev[0] for ev in events]
    return ASK_SUB


def subscribe_save(update: Update, context: CallbackContext) -> int:
    """Обрабатывает подписку на выбранные номера."""
    text = update.message.text.strip()

    if text == "0":
        update.message.reply_text("❌ Отмена.")
        return ConversationHandler.END

    if not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", text):
        update.message.reply_text("❗ Введите номера через запятую.")
        return ASK_SUB

    candidates = context.user_data.get("subs_candidates", [])
    to_sub = []
    for part in text.split(","):
        idx = int(part.strip()) - 1
        if 0 <= idx < len(candidates):
            to_sub.append(candidates[idx])
        else:
            update.message.reply_text("❗ Нет такого номера.")
            return ASK_SUB

    for ev_id in to_sub:
        db.subscribe_user(update.effective_user.id, ev_id)

    update.message.reply_text("✅ Подписка оформлена.")
    return ConversationHandler.END


# ───────────────────────── FALLBACK ────────────────────────────
def cancel_subscription(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END


# ───────────────────── ConversationHandlers ────────────────────
unsubscribe_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("unsubscribe", show_subscriptions),
        MessageHandler(Filters.regex(r'^🔔 Подписки$'), show_subscriptions),
    ],
    states={
        ASK_UNSUB: [
            MessageHandler(Filters.regex(r'^\d+(?:\s*,\s*\d+)*$'), unsubscribe_save)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_subscription)],
    allow_reentry=True,
)

subscribe_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("subscribe", subscribe_prompt),
        MessageHandler(Filters.regex(r'^📌 Все олимпиады$'), subscribe_prompt),
    ],
    states={
        ASK_SUB: [
            MessageHandler(Filters.regex(r'^\d+(?:\s*,\s*\d+)*$'), subscribe_save)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_subscription)],
    allow_reentry=True,
)
