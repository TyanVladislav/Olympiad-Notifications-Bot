from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)
import re
from database import db

# ─────────────── состояния ConversationHandler ───────────────
ASK_DEL = 0        # ждём номера(ов) для удаления


# ────────────────── вспомогательная функция ──────────────────
def _render_history(update: Update, context: CallbackContext) -> int:
    """Отправляет список участий и возвращает состояние ASK_DEL либо END."""
    rows = db.get_user_history(update.effective_user.id)   # [(id, name, date), …]

    if not rows:
        update.message.reply_text("📭 У вас пока нет отмеченных участий.")
        return ConversationHandler.END

    # сохраняем id событий, чтобы потом удалять по номеру
    context.user_data["hist_ids"] = [ev_id for ev_id, *_ in rows]

    lines = ["📚 *История Вашего участия:*"]
    for i, (_, name, date) in enumerate(rows, start=1):
        lines.append(f"{i}. {date} — {name}")
    lines.append("\nВведите номера через запятую, чтобы удалить записи\nили `0` — выход.")

    update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    return ASK_DEL


# ──────────────────── старт просмотра истории ─────────────────
def history_start(update: Update, context: CallbackContext) -> int:
    return _render_history(update, context)


# ───────────────── удаление выбранных записей ─────────────────
def history_delete(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip()

    if text == "0":
        update.message.reply_text("✅ Готово.")
        return ConversationHandler.END

    if not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", text):
        update.message.reply_text("❗ Введите номера через запятую или 0 для выхода.")
        return ASK_DEL

    event_ids = context.user_data.get("hist_ids", [])
    for part in text.split(","):
        idx = int(part.strip()) - 1
        if 0 <= idx < len(event_ids):
            db.remove_participation(update.effective_user.id, event_ids[idx])

    update.message.reply_text("🗑 Записи удалены.")
    # перерисовываем список — если пусто, диалог закончится
    return _render_history(update, context)


# ──────────── inline-кнопка «✅ Отметить участие» ─────────────
def participate_button(update: Update, context: CallbackContext) -> None:
    """Callback-handler: добавить участие (participate_<event_id>)."""
    query = update.callback_query
    query.answer()      # чтобы убрать «часики»

    user_id = query.from_user.id
    try:
        event_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        query.answer("Ошибка данных")
        return

    db.add_participation(user_id, event_id)

    event = db.get_event(event_id)
    event_name = event[0] if event else "олимпиаде"
    query.answer(f"✅ Участие в «{event_name}» отмечено")


# ──────────────── ConversationHandler истории ────────────────
history_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("history", history_start),
        MessageHandler(Filters.regex(r'^📖 История$'), history_start),  # ← кнопка
    ],
    states={
        ASK_DEL: [MessageHandler(Filters.text & ~Filters.command, history_delete)],
    },
    fallbacks=[
        CommandHandler("cancel", lambda u, c: u.message.reply_text("❌") or ConversationHandler.END)
    ],
    allow_reentry=True,
)


# ──────────────── Регистрация callback-кнопки ─────────────────
participate_handler = CallbackQueryHandler(participate_button, pattern=r'^participate_\d+$')
