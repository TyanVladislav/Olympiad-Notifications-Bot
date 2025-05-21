# parser/events_parser.py

import re
import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def parse_event_detail(event_url: str, session: requests.Session):
    """
    Парсит страницу отдельного события, чтобы:
      - извлечь дату из itemprop="startDate" (формат DD.MM.YYYY)
      - найти внешнюю ссылку на регистрацию (div.ecwd-url → a[href])
    Возвращает кортеж (event_date_str, external_link) или (None, None).
    """
    event_date = None
    external_link = None

    try:
        resp = session.get(event_url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Не удалось загрузить детали события {event_url}: {e}")
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1) Попытка взять дату из атрибута content у span.ecwd-event-date[itemprop=startDate]
    date_meta = soup.find('span', class_='ecwd-event-date', itemprop='startDate')
    if date_meta and date_meta.has_attr('content'):
        try:
            iso = date_meta['content']            # пример: "2025-03-02T10:00"
            dt = datetime.fromisoformat(iso)
            event_date = dt.strftime("%d.%m.%Y")
        except Exception:
            pass

    # 2) Фолбэк: искать все вхождения DD.MM.YYYY в тексте страницы
    if not event_date:
        text = soup.get_text(" ")
        dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", text)
        if len(dates) >= 2:
            # если два, считаем, что это диапазон
            event_date = f"{dates[0]}-{dates[1]}"
        elif dates:
            event_date = dates[0]

    # 3) Ищем внешнюю ссылку в блоке <div class="ecwd-url">
    url_block = soup.find('div', class_='ecwd-url')
    if url_block:
        a = url_block.find('a', href=True)
        if a and a['href'].startswith(("http://", "https://")):
            external_link = a['href']

    # 4) Фолбэк: первая подходящая внешняя ссылка на странице
    if not external_link:
        for a in soup.find_all('a', href=True):
            href = a['href']
            if not href.startswith(("http://", "https://")):
                continue
            # пропускаем внутренние и соцсети
            if any(domain in href for domain in ["postypashki.ru", "vk.com", "youtube.com", "t.me", "wordpress.org"]):
                continue
            external_link = href
            break

    return event_date, external_link


def parse_events(months_back: int = 2, months_forward: int = 2):
    """
    Парсит список событий в режиме 'list' за диапазон месяцев:
      от текущего - months_back до текущего + months_forward.
    Возвращает список кортежей:
      (name, date_str, subject, level, organizer, link)
    """
    base_url = "https://postypashki.ru/ecwd_calendar/calendar/"
    now = datetime.now()
    session = requests.Session()
    events = []

    for offset in range(-months_back, months_forward + 1):
        target = now + relativedelta(months=offset)
        date_param = f"{target.year}-{target.month}-1"
        page = 1

        while True:
            url = f"{base_url}?date={date_param}&t=list"
            if page > 1:
                url += f"&cpage={page}"

            try:
                resp = session.get(url, timeout=10)
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"Ошибка при запросе {url}: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            container = soup.find('ul', class_='ecwd_list')
            if not container:
                break

            items = container.find_all('li', class_='ecwd-no-image')
            if not items:
                break

            for li in items:
                title_tag = li.find('h3', class_='event-title')
                if not title_tag or not title_tag.a:
                    continue

                full_name = title_tag.get_text(strip=True)
                detail_url = title_tag.a['href']

                # 1) Дата из списка
                date_div = li.find('div', class_='ecwd-date')
                list_date = date_div.get_text(strip=True) if date_div else None

                # 2) Парсим детали страницы
                detail_date, detail_link = parse_event_detail(detail_url, session)
                final_date = list_date or detail_date
                link       = detail_link or detail_url

                # 3) Разбор названия full_name → name, subject, level, organizer
                name = full_name
                subject = None
                level   = None
                organizer = None

                # Выделяем предмет, если в скобках
                m = re.search(r"\(([^)]+)\)", name)
                if m:
                    subject = m.group(1).strip()
                    name = name[:m.start()].strip()

                # Разделяем по " - "
                if " - " in name:
                    left, right = name.split(" - ", 1)
                    # организатор — всё после слова "Олимпиада" в левой части
                    if left.lower().startswith("олимпиада"):
                        organizer = left[len("олимпиада"):].strip()
                    else:
                        organizer = left.strip()
                    level = right.strip()
                else:
                    # если дефиса нет, пытаемся убрать слово "Олимпиада"
                    if name.lower().startswith("олимпиада"):
                        organizer = name[len("олимпиада"):].strip()
                    else:
                        organizer = None
                    level = None

                events.append((name, final_date, subject, level, organizer, link))

            # пагинация: ищем ссылку на следующую страницу
            pag = soup.find('div', class_='ecwd-pagination')
            next_page = pag.find('a', class_='cpage', string=str(page+1)) if pag else None
            if next_page:
                page += 1
                continue
            break

    session.close()
    logger.info(f"parse_events: собрано {len(events)} событий")
    return events


if __name__ == "__main__":
    evs = parse_events()
    logger.info(f"Найдено событий: {len(evs)}")
    for name, date_str, subject, level, organizer, link in evs:
        logger.info(f"{date_str} | {name} | subj={subject} lvl={level} org={organizer} → {link}")
