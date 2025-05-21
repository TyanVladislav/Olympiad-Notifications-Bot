import struct

tests = []


def what(file, h=None):
    """Определяет тип картинки по начальным байтам."""
    if h is None:
        h = file.read(32)
        file.seek(0)
    for tf in tests:
        res = tf(h, file)
        if res:
            return res


def test_jpeg(h, f):
    return h.startswith(b'\377\330\377')


def test_png(h, f):
    return h.startswith(b'\211PNG\r\n\032\n')


tests = [test_jpeg, test_png]
