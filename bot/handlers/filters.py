from handlers.subscriptions import subscribe_save
from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    CommandHandler,
    Filters,
)
import database.db as db
import re

ASK_SUBJ, ASK_LVL, ASK_ORG, ASK_NUMBERS = range(4)


# ─────────────────────── ШАГ 1. ПРЕДМЕТЫ ───────────────────────
def start_filter(update: Update, context: CallbackContext) -> int:
    context.user_data['in_filter'] = True

    subjects = db.get_subjects_list()
    if subjects:
        example = ", ".join(subjects[:5]) + ("..." if len(subjects) > 5 else "")
        update.message.reply_text(
            "🛠 *Настройка фильтров*\n\n"
            "Шаг 1. Введите через запятую предметы, по которым хотите получать уведомления\n"
            "(или `0` — чтобы пропустить).\n\n"
            f"_Доступные (пример):_ {example}",
            parse_mode="Markdown"
        )
    else:
        update.message.reply_text(
            "Шаг 1. Введите через запятую предметы (или `0` — пропустить)."
        )

    return ASK_SUBJ


def ask_levels(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip().lower()
    subjects = [s.lower() for s in db.get_subjects_list()]   # регистр → lower

    if text == "0":
        context.user_data["filter_subject"] = None
    else:
        chosen = [s.strip().lower() for s in text.split(",")]
        invalid = [s for s in chosen if s not in subjects]
        if invalid:
            update.message.reply_text(
                f"❌ Неизвестные предметы: {', '.join(invalid)}.\n"
                f"Попробуйте снова, используя варианты из списка."
            )
            return ASK_SUBJ

        context.user_data["filter_subject"] = chosen

    # ───── переходим к уровням
    levels = db.get_levels_list()
    if levels:
        example = ", ".join(levels[:5]) + ("..." if len(levels) > 5 else "")
        update.message.reply_text(
            "Шаг 2. Введите через запятую уровни (например: школьный, региональный)\n"
            "(или `0` — пропустить).\n\n"
            f"_Доступные (пример):_ {example}",
            parse_mode="Markdown"
        )
    else:
        update.message.reply_text(
            "Шаг 2. Введите через запятую уровни (или `0` — пропустить)."
        )
    return ASK_LVL


# ─────────────────────── ШАГ 2. УРОВНИ ───────────────────────
def ask_organizers(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip().lower()
    levels = [l.lower() for l in db.get_levels_list()]

    if text == "0":
        context.user_data["filter_level"] = None
    else:
        chosen = [s.strip().lower() for s in text.split(",")]
        invalid = [s for s in chosen if s not in levels]
        if invalid:
            update.message.reply_text(
                f"❌ Неизвестные уровни: {', '.join(invalid)}.\n"
                f"Попробуйте снова, используя варианты из списка."
            )
            return ASK_LVL

        context.user_data["filter_level"] = chosen

    # ───── переходим к организаторам
    orgs = db.get_organizers_list()
    if orgs:
        example = ", ".join(orgs[:5]) + ("..." if len(orgs) > 5 else "")
        update.message.reply_text(
            "Шаг 3. Введите через запятую организаторов (например: ИТМО, СПбГУ)\n"
            "(или `0` — пропустить).\n\n"
            f"_Доступные (пример):_ {example}",
            parse_mode="Markdown"
        )
    else:
        update.message.reply_text(
            "Шаг 3. Введите через запятую организаторов (или `0` — пропустить)."
        )
    return ASK_ORG


# ────────────────────── ШАГ 3. ОРГАНИЗАТОРЫ ────────────────────
def save_filters(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip().lower()
    orgs = [o.lower() for o in db.get_organizers_list()]

    if text == "0":
        context.user_data["filter_organizer"] = None
    else:
        chosen = [s.strip().lower() for s in text.split(",")]
        invalid = [s for s in chosen if s not in orgs]
        if invalid:
            update.message.reply_text(
                f"❌ Неизвестные организаторы: {', '.join(invalid)}.\n"
                f"Попробуйте снова, используя варианты из списка."
            )
            return ASK_ORG
        context.user_data["filter_organizer"] = chosen

    # ───── сохраняем фильтр пользователя
    user_id = update.effective_user.id
    subj = context.user_data.get("filter_subject")
    lvl  = context.user_data.get("filter_level")
    org  = context.user_data.get("filter_organizer")

    db.set_user_filter(
        user_id,
        ",".join(subj) if subj else None,
        ",".join(lvl)  if lvl  else None,
        ",".join(org)  if org  else None
    )

    update.message.reply_text("✅ Фильтры сохранены!\n")
    # сразу покажем, что найдено
    return show_filtered_events(update, context)


# ──────────────────── ПОКАЗ ОТФИЛЬТРОВАННОГО ────────────────────
def show_filtered_events(update: Update, context: CallbackContext) -> int:
    context.user_data.pop('in_filter', None)

    user_id = update.effective_user.id
    row = db.get_user(user_id) or (None,)*5
    _, _, _, subj_csv, lvl_csv, org_csv = row

    subj = [s.lower() for s in subj_csv.split(",")] if subj_csv else None
    lvl  = [l.lower() for l in lvl_csv.split(",")]  if lvl_csv  else None
    org  = [o.lower() for o in org_csv.split(",")]  if org_csv  else None

    all_events = db.get_upcoming_events(limit=100)
    filtered = [
        ev for ev in all_events
        if (subj is None or (ev[3] or "").lower() in subj)
        and (lvl is None or (ev[4] or "").lower() in lvl)
        and (org is None or (ev[5] or "").lower() in org)
    ]

    if not filtered:
        update.message.reply_text("❕ По вашим фильтрам ничего не найдено.")
        return ConversationHandler.END

    context.user_data["subs_candidates"] = [ev[0] for ev in filtered]

    lines = ["📑 *Отфильтрованные события:*"]
    for i, (_, name, date, *_ ) in enumerate(filtered, start=1):
        lines.append(f"{i}. {date} — {name}")
    lines.append("\nВведите номера через запятую для подписки (или `0` — отмена):")

    update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    return ASK_NUMBERS


# ───────────────── ConversationHandler ─────────────────
filter_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("setfilter", start_filter),
        MessageHandler(Filters.regex(r'^⚙️ Фильтры$'), start_filter),
    ],
    states={
        ASK_SUBJ: [MessageHandler(Filters.text & ~Filters.command, ask_levels)],
        ASK_LVL:  [MessageHandler(Filters.text & ~Filters.command, ask_organizers)],
        ASK_ORG:  [MessageHandler(Filters.text & ~Filters.command, save_filters)],
        ASK_NUMBERS: [MessageHandler(
            Filters.regex(r'^\d+(?:\s*,\s*\d+)*$'), subscribe_save)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("❌ Настройка фильтров отменена.") or ConversationHandler.END)],
    allow_reentry=True,
)
