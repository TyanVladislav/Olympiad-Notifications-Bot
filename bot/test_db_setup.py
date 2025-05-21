from database.db import init_db, clear_events, add_event
from parser.events_parser import parse_events


def main():
    init_db()
    clear_events()
    events = parse_events()
    for name, date, link in events:
        add_event(name, date, link)
    print(f"В тестовую БД добавлено {len(events)} событий")


if __name__ == "__main__":
    main()
