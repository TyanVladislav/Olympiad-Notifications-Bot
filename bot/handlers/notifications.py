from datetime import datetime, timedelta
from html import escape
from telegram.ext import CallbackContext
import config
from database import db


def send_notifications(context: CallbackContext) -> None:
    """
    Ежедневно вызывается JobQueue:
    — Для каждого пользователя вычисляем target_date = today + notify_days
    — Берём из БД все события на эту дату
    — Фильтруем их по подпискам и фильтрам
    — И отправляем каждому подходящие
    """
    today = datetime.now().date()
    users = db.get_all_users()
    for user_id, notify_days, filter_subject, filter_level, filter_organizer in users:
        target = today + timedelta(days=notify_days)
        # Получаем события на target дату
        events = db.get_events_on_date(target.strftime('%d.%m.%Y'))
        # Подписки пользователя
        subscribed = {ev_id for ev_id, *_ in db.get_user_subscriptions(user_id)}
        for ev in events:
            ev_id, name, date_str, subj, lvl, organizer, link = ev
            # Если есть подписки — отправляем только по ним
            if subscribed and ev_id not in subscribed:
                continue
            # Применяем фильтры
            if filter_subject and (not subj or subj.lower() not in filter_subject.lower()):
                continue
            if filter_level and (not lvl or lvl.lower() not in filter_level.lower()):
                continue
            if filter_organizer and (not organizer or organizer.lower() not in filter_organizer.lower()):
                continue
            # Если нет ни подписок, ни фильтров — пропускаем
            if not subscribed and not filter_subject and not filter_level and not filter_organizer:
                continue
            safe_name = escape(name)
            safe_link = escape(link)
            days_word = "дней" if notify_days != 1 else "день"
            text = (
                f"🔔 Напоминание: <a href=\"{safe_link}\">{safe_name}</a>\n"
                f"Дата: {date_str} (через {notify_days} {days_word})."
            )
            context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
