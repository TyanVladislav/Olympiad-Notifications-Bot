# handlers/settings.py
from telegram import ParseMode
from database import db


def set_days(update, context):
    """Команда /setdays N — установить, за сколько дней до события присылать уведомления."""
    user_id = update.message.from_user.id
    args = context.args

    # Проверяем аргументы
    if not args or not args[0].isdigit():
        update.message.reply_text(
            "❗️ Использование: /setdays <число дней>\n"
            "например: /setdays 3"
        )
        return

    days = int(args[0])
    if days < 1 or days > 30:
        update.message.reply_text("❗️ Введите значение от 1 до 30.")
        return

    # Проверяем, что пользователь зарегистрирован
    if not db.get_user(user_id):
        update.message.reply_text(
            "Вы ещё не зарегистрированы. Сначала отправьте /start и поделитесь номером телефона."
        )
        return

    # Обновляем настройки
    db.update_notify_days(user_id, days)
    update.message.reply_text(
        f"✅ Отлично! Я буду напоминать вам за *{days}* "
        f"{'день' if days == 1 else 'дня' if 2 <= days <= 4 else 'дней'} до события.",
        parse_mode=ParseMode.MARKDOWN
    )
