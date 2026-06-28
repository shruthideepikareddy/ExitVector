from datetime import date
from src.compliance.rules import SchengenComplianceEngine

def test_single_short_stay():
    # 30 days stay in Schengen
    history = [
        {
            "city": "Paris",
            "country": "France",
            "region": "Schengen",
            "arrival_date": "2026-01-01",
            "departure_date": "2026-01-30"
        }
    ]
    engine = SchengenComplianceEngine(history)
    
    # Check compliance right after the trip
    res = engine.check_compliance(date(2026, 2, 1))
    assert res["is_compliant"] is True
    assert res["days_spent"] == 30
    assert res["days_remaining"] == 60

def test_schengen_near_limit():
    # 85 days stay in Schengen
    history = [
        {
            "city": "Rome",
            "country": "Italy",
            "region": "Schengen",
            "arrival_date": "2026-01-01",
            "departure_date": "2026-03-26" # 85 days
        }
    ]
    engine = SchengenComplianceEngine(history)
    res = engine.check_compliance(date(2026, 3, 27))
    assert res["is_compliant"] is True
    assert res["days_spent"] == 85
    assert res["days_remaining"] == 5

def test_schengen_exceeds_limit():
    # 95 days stay in Schengen
    history = [
        {
            "city": "Rome",
            "country": "Italy",
            "region": "Schengen",
            "arrival_date": "2026-01-01",
            "departure_date": "2026-04-05" # 95 days
        }
    ]
    engine = SchengenComplianceEngine(history)
    res = engine.check_compliance(date(2026, 4, 6))
    assert res["is_compliant"] is False
    assert res["days_spent"] == 95
    assert res["days_remaining"] == 0

def test_rolling_window_drop_off():
    # Traveler stays 50 days, leaves for 150 days, then stays 45 days.
    # Total stays = 95 days, but since the first stay falls outside the rolling 180-day window
    # from the evaluation date, they should be fully compliant.
    history = [
        {
            "city": "Paris",
            "country": "France",
            "region": "Schengen",
            "arrival_date": "2025-01-01",
            "departure_date": "2025-02-19" # 50 days
        },
        {
            "city": "Berlin",
            "country": "Germany",
            "region": "Schengen",
            "arrival_date": "2025-07-20",
            "departure_date": "2025-09-02" # 45 days
        }
    ]
    engine = SchengenComplianceEngine(history)
    
    # Evaluate at the end of the second trip (2025-09-02)
    # The 180-day window starts on 2025-03-07.
    # The first trip (Jan-Feb 2025) is completely outside this window.
    # So days spent should be only 45, and they are compliant!
    res = engine.check_compliance(date(2025, 9, 2))
    assert res["is_compliant"] is True
    assert res["days_spent"] == 45
    assert res["days_remaining"] == 45
