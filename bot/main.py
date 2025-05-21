# main.py
import logging
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
)

import config
from parser.events_parser import parse_events
import database.db as db

# ───────── handlers ─────────
from handlers.auth          import start, handle_contact
from handlers.help          import help_command
from handlers.settings      import set_days
from handlers.filters       import filter_conversation, show_filtered_events
from handlers.subscriptions import (
    show_subscriptions,
    subscribe_conversation,
    unsubscribe_conversation,
)
from handlers.events        import show_events, events_conversation
from handlers.history       import history_conversation, participate_handler
from handlers.attended      import attended_conversation
from handlers.notifications import send_notifications
# ────────────────────────────


def main() -> None:
    # 1) логирование
    logging.basicConfig(
        format="%(asctime)s — %(levelname)s — %(name)s: %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    # 2) БД + парсинг
    db.init_db()
    for name, date, subject, level, organizer, link in parse_events():
        db.add_event(name, date, subject, level, organizer, link)

    # 3) бот
    updater = Updater(config.BOT_TOKEN, use_context=True)
    dp      = updater.dispatcher
    jq      = updater.job_queue

    # 4a) простые команды
    dp.add_handler(CommandHandler("start",   start))
    dp.add_handler(CommandHandler("help",    help_command))
    dp.add_handler(CommandHandler("setdays", set_days, pass_args=True))
    # history теперь ConversationHandler → регистрируем ниже
    dp.add_handler(MessageHandler(Filters.contact, handle_contact))

    # 4b) ConversationHandler фильтров
    dp.add_handler(filter_conversation, group=0)

    # 4c) меню и просмотр олимпиад
    dp.add_handler(events_conversation, group=1)   # /events и «📌 Все олимпиады»
    dp.add_handler(MessageHandler(
        Filters.regex(r'^📅 Ближайшие$'), show_events), group=1)
    dp.add_handler(MessageHandler(
        Filters.regex(r'^📂 Показать фильтр$'), show_filtered_events), group=1)
    #dp.add_handler(MessageHandler(Filters.regex(r'^🔔 Подписки$'), show_subscriptions), group=1)
    # кнопка «📖 История» просто запускает /history
    #dp.add_handler(MessageHandler(Filters.regex(r'^📖 История$'), lambda u, c: c.bot.send_message(chat_id=u.effective_chat.id, text="/history")), group=1)
    dp.add_handler(MessageHandler(
        Filters.regex(r'^❓ Помощь$'), help_command), group=1)
    # кнопка «✅ Участвовал»
    dp.add_handler(attended_conversation, group=1)

    # 4d) подписки / отписки
    dp.add_handler(subscribe_conversation,   group=1)
    dp.add_handler(unsubscribe_conversation, group=1)

    # 4e) история и отметка участия
    dp.add_handler(history_conversation)          # /history диалог
    dp.add_handler(participate_handler, group=0)  # inline «participate_<id>»

    # 5) ежедневные уведомления
    jq.run_repeating(send_notifications, interval=24 * 60 * 60, first=0)

    # 6) запуск
    updater.start_polling()
    logger.info("Bot started. Press Ctrl+C to stop.")
    updater.idle()


if __name__ == "__main__":
    main()
