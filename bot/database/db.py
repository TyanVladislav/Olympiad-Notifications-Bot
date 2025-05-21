import sqlite3
from datetime import datetime
import config

DB_PATH = config.DB_PATH


# ─────────────────────── ИНИЦИАЛИЗАЦИЯ ────────────────────────
def init_db() -> None:
    """Создаёт все необходимые таблицы и удаляет дубликаты ссылок."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Пользователи ───────────────────────────────────────────
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            user_id          INTEGER PRIMARY KEY,
            phone_hash       TEXT,
            notify_days      INTEGER DEFAULT {config.DEFAULT_NOTIFY_DAYS},
            filter_subject   TEXT,
            filter_level     TEXT,
            filter_organizer TEXT
        )
    """)

    # ── Олимпиады ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT,
            date      TEXT,
            subject   TEXT,
            level     TEXT,
            organizer TEXT,
            link      TEXT
        )
    """)

    # ── Подписки ───────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id  INTEGER,
            event_id INTEGER,
            PRIMARY KEY (user_id, event_id)
        )
    """)

    # ── История участия ────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS participation (
            user_id         INTEGER,
            event_id        INTEGER,
            participated_on TEXT,
            PRIMARY KEY (user_id, event_id)
        )
    """)

    # ── Удаляем дубликаты ссылок и ставим уникальный индекс ────
    cur.execute("""
        DELETE FROM events
        WHERE id NOT IN (
            SELECT MIN(id) FROM events GROUP BY link
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_link ON events(link)")

    conn.commit()
    conn.close()


# ───────────────────────—  СОБЫТИЯ  —──────────────────────────
def clear_events() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM events")


def add_event(name: str,
              date: str,
              subject: str | None = None,
              level: str | None = None,
              organizer: str | None = None,
              link: str | None = None) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO events (name, date, subject, level, organizer, link) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, date, subject, level, organizer, link)
        )


def upsert_event(name: str,
                 date: str,
                 link: str,
                 subject: str | None = None,
                 level: str | None = None,
                 organizer: str | None = None) -> None:
    """Обновляет запись по уникальной ссылке или вставляет новую."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO events (id, name, date, subject, level, organizer, link)
            VALUES (
                COALESCE((SELECT id FROM events WHERE link = ?), NULL),
                ?, ?, ?, ?, ?, ?
            )
        """, (link, name, date, subject, level, organizer, link))


def delete_missing_events(current_links: list[str]) -> None:
    if not current_links:
        return
    placeholders = ",".join("?" for _ in current_links)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"DELETE FROM events WHERE link NOT IN ({placeholders})", current_links)


def get_event(event_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT name, date, subject, level, organizer, link "
            "FROM events WHERE id = ? LIMIT 1",
            (event_id,)
        ).fetchone()


def get_events():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT id, name, date, subject, level, organizer, link FROM events"
        ).fetchall()


def get_upcoming_events(limit: int = 10):
    """Ближайшие события (date ≥ сегодня) в формате DD.MM.YYYY."""
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT id, name, date, subject, level, organizer, link
            FROM events
            WHERE substr(date,7,4)||'-'||substr(date,4,2)||'-'||substr(date,1,2) >= date('now')
            ORDER BY substr(date,7,4)||'-'||substr(date,4,2)||'-'||substr(date,1,2)
            LIMIT ?
        """, (limit,)).fetchall()


# ───────────────────────—  ПОЛЬЗОВАТЕЛИ  —──────────────────────
def get_user(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT user_id, phone_hash, notify_days, filter_subject, filter_level, filter_organizer "
            "FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()


def add_user(user_id: int,
             phone_hash: str | None = None,
             notify_days: int | None = None) -> None:
    """Создаёт пользователя, если ещё нет. phone_hash можно передать None."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, phone_hash, notify_days) VALUES (?, ?, ?)",
            (user_id, phone_hash, notify_days or config.DEFAULT_NOTIFY_DAYS)
        )


def get_all_users():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT user_id, notify_days, filter_subject, filter_level, filter_organizer FROM users"
        ).fetchall()


def update_notify_days(user_id: int, days: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET notify_days = ? WHERE user_id = ?", (days, user_id))


def set_user_filter(user_id: int,
                    subject: str | None = None,
                    level: str | None = None,
                    organizer: str | None = None) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute(
            "UPDATE users SET filter_subject = ?, filter_level = ?, filter_organizer = ? "
            "WHERE user_id = ?",
            (subject, level, organizer, user_id)
        )


def clear_user_filter(user_id: int) -> None:
    set_user_filter(user_id, None, None, None)


# ───────────────────────—  ПОДПИСКИ  —──────────────────────────
def subscribe_user(user_id: int, event_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO subscriptions (user_id, event_id) VALUES (?, ?)",
            (user_id, event_id)
        )


def unsubscribe_user(user_id: int, event_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM subscriptions WHERE user_id = ? AND event_id = ?",
            (user_id, event_id)
        )


def get_user_subscriptions(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT e.id, e.name, e.date
            FROM events e
            JOIN subscriptions s ON e.id = s.event_id
            WHERE s.user_id = ?
            ORDER BY e.date
        """, (user_id,)).fetchall()


# ───────────────────────—  УЧАСТИЯ  —───────────────────────────
def add_participation(user_id: int, event_id: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO participation (user_id, event_id, participated_on) "
            "VALUES (?, ?, ?)",
            (user_id, event_id, now)
        )


def remove_participation(user_id: int, event_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM participation WHERE user_id = ? AND event_id = ?",
            (user_id, event_id)
        )


def get_user_history(user_id: int):
    """Возвращает [(event_id, name, date), …] по возрастанию даты."""
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT e.id, e.name, e.date
            FROM participation p
            JOIN events e ON e.id = p.event_id
            WHERE p.user_id = ?
            ORDER BY e.date
        """, (user_id,)).fetchall()


# ───────────────────────—  СПРАВОЧНЫЕ  —────────────────────────
def get_subjects_list():
    with sqlite3.connect(DB_PATH) as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT subject FROM events WHERE subject IS NOT NULL"
        ).fetchall()]


def get_levels_list():
    with sqlite3.connect(DB_PATH) as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT level FROM events WHERE level IS NOT NULL"
        ).fetchall()]


def get_organizers_list():
    with sqlite3.connect(DB_PATH) as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT organizer FROM events WHERE organizer IS NOT NULL"
        ).fetchall()]
