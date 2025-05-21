# populate_test_db.py

import database.db as db

def main():
    # 1) Инициализируем БД и очищаем старые тестовые события
    db.init_db()
    db.clear_events()

    # 2) Собираем список тестовых событий:
    #    (name, date, subject, level, organizer, link)
    test_events = [
        # полностью заполненное (математика, школьный, СПбАстро)
        ("Олимпиада Школьная по математике",
         "05.06.2025", "математика", "школьный", "СПбАстро",
         "https://example.com/math_school"),
        # полностью заполненное (информатика, региональный, ИТМО)
        ("Региональная олимпиада по информатике",
         "10.06.2025", "информатика", "региональный", "ИТМО",
         "https://example.com/inf_regional"),
        # полный набор (физика, заключительный тур, СПбГУ)
        ("Заключительный тур по физике",
         "15.06.2025", "физика", "заключительный", "СПбГУ",
         "https://example.com/phys_final"),
        # без уровня (биология, None level, ИТМО)
        ("Биологическая олимпиада",
         "20.06.2025", "биология", None, "ИТМО",
         "https://example.com/bio_no_level"),
        # без организатора (химия, муниципальный, None organizer)
        ("Муниципальный этап по химии",
         "25.06.2025", "химия", "муниципальный", None,
         "https://example.com/chem_municipal"),
        # без предмета (None subject, всероссийский, СПбАстро)
        ("Всероссийский форум по астрономии",
         "30.06.2025", None, "всероссийский", "СПбАстро",
         "https://example.com/astro_all_russia"),
        # без ничего (None subject, None level, None organizer)
        ("Неанонсированное событие",
         "05.07.2025", None, None, None,
         "https://example.com/unknown_event"),
    ]

    # 3) Добавляем их в БД
    for name, date, subject, level, organizer, link in test_events:
        db.add_event(name, date, subject, level, organizer, link)

    print(f"В базу добавлено {len(test_events)} тестовых событий.")

if __name__ == "__main__":
    main()
