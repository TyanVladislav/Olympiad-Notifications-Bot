import hashlib


def hash_phone(phone: str) -> str:
    """Возвращает SHA-256 хеш для заданной строки телефонного номера."""
    return hashlib.sha256(phone.encode('utf-8')).hexdigest()
