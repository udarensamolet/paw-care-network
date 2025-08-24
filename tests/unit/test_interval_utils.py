from datetime import datetime

def overlaps(a_start, a_end, b_start, b_end):
    return min(a_end, b_end) > max(a_start, b_start)

def test_overlaps_true():
    a1 = datetime(2025, 1, 1, 8)
    a2 = datetime(2025, 1, 1, 12)
    b1 = datetime(2025, 1, 1, 10)
    b2 = datetime(2025, 1, 1, 13)
    assert overlaps(a1, a2, b1, b2) is True

def test_overlaps_false_touching():
    a1 = datetime(2025, 1, 1, 8)
    a2 = datetime(2025, 1, 1, 10)
    b1 = datetime(2025, 1, 1, 10)
    b2 = datetime(2025, 1, 1, 12)
    assert overlaps(a1, a2, b1, b2) is False

def test_overlaps_false_separate():
    a1 = datetime(2025, 1, 1, 8)
    a2 = datetime(2025, 1, 1, 9)
    b1 = datetime(2025, 1, 1, 10)
    b2 = datetime(2025, 1, 1, 11)
    assert overlaps(a1, a2, b1, b2) is False