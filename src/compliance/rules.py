from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Set

def parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    return date.fromisoformat(date_str)

class SchengenComplianceEngine:
    def __init__(self, history: List[Dict]):
        """
        Initialize the compliance engine with the traveler's historical logs.
        Each log entry contains: city, country, region, arrival_date, departure_date.
        """
        self.history = history

    def get_schengen_days_on_date(self, ref_date: date) -> Tuple[int, Set[date]]:
        """
        Calculate the number of Schengen days in the rolling 180-day window ending on ref_date.
        Returns the count of days and the set of date objects representing Schengen presence.
        """
        start_window = ref_date - timedelta(days=179)  # 180-day window: [ref_date - 179, ref_date]
        schengen_dates = set()

        for entry in self.history:
            if entry.get("region") != "Schengen":
                continue

            arrival = parse_date(entry.get("arrival_date"))
            departure = parse_date(entry.get("departure_date"))

            # If the trip is ongoing (departure is None), cap it at the reference date
            if departure is None:
                # If the reference date is before the arrival date, this trip hasn't started yet relative to ref_date
                if ref_date < arrival:
                    continue
                departure = ref_date
            else:
                # If the entire trip is in the future relative to ref_date, ignore it
                if arrival > ref_date:
                    continue
                # If the trip extends past ref_date, cap it at ref_date
                if departure > ref_date:
                    departure = ref_date

            # Iterate through the trip dates and add them if they fall within the 180-day window
            current = arrival
            while current <= departure:
                if start_window <= current <= ref_date:
                    schengen_dates.add(current)
                current += timedelta(days=1)

        return len(schengen_dates), schengen_dates

    def check_compliance(self, ref_date: date) -> Dict:
        """
        Check compliance as of a specific reference date.
        Returns:
            - days_spent: Days spent in Schengen in the last 180 days.
            - days_remaining: Days left to stay before hitting the 90-day limit.
            - is_compliant: Boolean indicating if they are under or equal to 90 days.
            - overstay_date: The date they will hit 90 days if they stay continuously.
        """
        days_spent, _ = self.get_schengen_days_on_date(ref_date)
        is_compliant = days_spent <= 90
        days_remaining = max(0, 90 - days_spent)

        # Check if the traveler is currently in Schengen on the reference date
        is_currently_in_schengen = False
        for entry in self.history:
            if entry.get("region") == "Schengen":
                arrival = parse_date(entry.get("arrival_date"))
                departure = parse_date(entry.get("departure_date"))
                if arrival <= ref_date and (departure is None or departure >= ref_date):
                    is_currently_in_schengen = True
                    break

        overstay_date = None
        if is_currently_in_schengen and is_compliant:
            # Project forward day by day to see when they will hit 90 days.
            # We simulate staying continuously in Schengen from ref_date onwards.
            temp_history = [dict(entry) for entry in self.history]
            
            # Find the active ongoing trip and make it extend indefinitely for projection
            for entry in temp_history:
                if entry.get("region") == "Schengen":
                    arrival = parse_date(entry.get("arrival_date"))
                    departure = parse_date(entry.get("departure_date"))
                    if arrival <= ref_date and (departure is None or departure >= ref_date):
                        entry["departure_date"] = None

            projected_engine = SchengenComplianceEngine(temp_history)
            projected_date = ref_date
            
            # Project up to 180 days in the future (the max limit of the rolling window)
            for _ in range(180):
                projected_date += timedelta(days=1)
                proj_spent, _ = projected_engine.get_schengen_days_on_date(projected_date)
                if proj_spent > 90:
                    overstay_date = projected_date - timedelta(days=1)
                    break
            
            # If they don't hit it in 180 days (e.g., they have zero prior stays),
            # they can stay 90 days starting from arrival or ref_date.
            if overstay_date is None:
                overstay_date = ref_date + timedelta(days=days_remaining - 1)

        return {
            "reference_date": ref_date.isoformat(),
            "days_spent": days_spent,
            "days_remaining": days_remaining,
            "is_compliant": is_compliant,
            "is_in_schengen": is_currently_in_schengen,
            "overstay_date": overstay_date.isoformat() if overstay_date else None
        }
