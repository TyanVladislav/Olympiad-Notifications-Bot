from telegram import Update
from telegram.ext import (
    ConversationHandler, CommandHandler,
    MessageHandler, Filters, CallbackContext
)
import database.db as db
import re

ASK_MARK = 0         # ждём номера олимпиад

def attended_start(update: Update, context: CallbackContext) -> int:
    """Показывает ближайшие 20 олимпиад для отметки участия."""
    events = db.get_upcoming_events(limit=20)

    if not events:
        update.message.reply_text("😔 Список олимпиад пуст.")
        return ConversationHandler.END

    context.user_data["attend_ids"] = [ev[0] for ev in events]

    lines = ["✅ *Отметить участие*: выберите номера олимпиад:"]
    for i, (_, name, date, *_ ) in enumerate(events, start=1):
        lines.append(f"{i}. {date} — {name}")
    lines.append("\nОтправьте номера через запятую (или `0` — отмена).")

    update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    return ASK_MARK


def attended_save(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip()
    if text == "0":
        update.message.reply_text("❌ Отмена.")
        return ConversationHandler.END

    if not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", text):
        update.message.reply_text("❗ Введите номера через запятую или 0 для отмены.")
        return ASK_MARK

    ids = context.user_data.get("attend_ids", [])
    to_add = []
    for part in text.split(","):
        idx = int(part.strip()) - 1
        if 0 <= idx < len(ids):
            to_add.append(ids[idx])

    for ev_id in to_add:
        db.add_participation(update.effective_user.id, ev_id)

    update.message.reply_text("🥳 Участие сохранено! Посмотреть: /history")
    return ConversationHandler.END


attended_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("attended", attended_start),
        MessageHandler(Filters.regex(r'^✅ Участвовал$'), attended_start),
    ],
    states={
        ASK_MARK: [MessageHandler(Filters.text & ~Filters.command, attended_save)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("❌") or ConversationHandler.END)],
)
