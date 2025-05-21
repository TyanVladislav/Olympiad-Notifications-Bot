from parser.events_parser import parse_events


def main():
    events = parse_events()
    print(f"Найдено {len(events)} событий:")
    for name, date, link in events:
        print(f"{date} — {name} → {link}")


if __name__ == "__main__":
    main()
