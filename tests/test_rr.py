import pytest

def calculate_rr(entry: float, stop_loss: float, take_profit: float) -> float:
    risk = abs(entry - stop_loss)
    if risk == 0:
        raise ZeroDivisionError("Risk cannot be zero")
    reward = abs(take_profit - entry)
    return round(reward / risk, 2)

def test_rr_calculation_standard():
    rr = calculate_rr(entry=100.0, stop_loss=95.0, take_profit=110.0)
    assert rr == 2.0

def test_rr_minimum_threshold():
    rr = calculate_rr(entry=100.0, stop_loss=95.0, take_profit=115.0)
    assert rr >= 2.0

def test_rr_invalidation_handling():
    rr_short = calculate_rr(entry=100.0, stop_loss=105.0, take_profit=85.0)
    assert rr_short == 3.0

def test_rr_target_scaling():
    rr_tp1 = calculate_rr(100.0, 95.0, 110.0)
    rr_tp2 = calculate_rr(100.0, 95.0, 120.0)
    assert rr_tp2 > rr_tp1

def test_zero_division_guard():
    with pytest.raises(ZeroDivisionError):
        calculate_rr(100.0, 100.0, 110.0)
