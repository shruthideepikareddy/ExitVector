from datetime import date, timedelta
from typing import Dict, List

from src import config
from src.compliance.rules import SchengenComplianceEngine, parse_date
from src.ai_parser.rules_extractor import VisaRulesExtractor
from src.flight_search.amadeus_client import AmadeusClient
from src.flight_search.mock_client import MockAmadeusClient

class TravelAdvisoryEngine:
    def __init__(self):
        # Choose flight search client based on configuration
        if config.is_amadeus_mocked():
            print("[Info] Amadeus credentials missing or placeholder. Running in MOCK flight search mode.")
            self.flight_client = MockAmadeusClient()
        else:
            self.flight_client = AmadeusClient()

        self.rules_extractor = VisaRulesExtractor()

    def generate_advisory(self, traveler_history_data: Dict, reference_date: date) -> Dict:
        """
        Evaluate traveler history, calculate visa status, and recommend cheap flight escapes
        if they are nearing stay limits.
        """
        history = traveler_history_data.get("history", [])
        passport = traveler_history_data.get("passport_nationality", "US")
        
        # 1. Run compliance calculation
        compliance_engine = SchengenComplianceEngine(history)
        status = compliance_engine.check_compliance(reference_date)

        days_remaining = status["days_remaining"]
        is_in_schengen = status["is_in_schengen"]
        overstay_date_str = status["overstay_date"]

        # Action required if they are in Schengen and have less than 15 days left
        requires_action = is_in_schengen and days_remaining <= 15

        recommendations = []

        if requires_action and overstay_date_str:
            overstay_date = parse_date(overstay_date_str)
            
            # Find the user's current city (last entry in history where they are currently staying)
            current_city = "Berlin" # Default fallback
            current_iata = "BER"
            for entry in reversed(history):
                if entry.get("region") == "Schengen" and entry.get("departure_date") is None:
                    current_city = entry.get("city", "Berlin")
                    current_iata = self.flight_client.get_destination_code(current_city)
                    break

            # Define escape non-Schengen destinations
            escape_destinations = [
                {"city": "London", "country": "United Kingdom", "iata": "LON"},
                {"city": "Istanbul", "country": "Turkey", "iata": "IST"},
                {"city": "Tirana", "country": "Albania", "iata": "TIA"}
            ]

            # We search for flights departing 3 days before their overstay limit
            flight_dep_date = overstay_date - timedelta(days=3)
            # Round trip of 30 days
            flight_ret_date = flight_dep_date + timedelta(days=30)

            print(f"[Warning] Schengen overstay date is {overstay_date}. Searching flights leaving {current_city} ({current_iata}) around {flight_dep_date}...")

            for dest in escape_destinations:
                dest_city = dest["city"]
                dest_country = dest["country"]
                dest_iata = dest["iata"]

                # A. Retrieve Visa allowance for destination country using AI Extractor
                visa_rule = self.rules_extractor.get_visa_rule(passport, dest_country)

                # B. Search cheapest flights
                offers = self.flight_client.search_flights(
                    origin=current_iata,
                    destination=dest_iata,
                    departure_date=flight_dep_date,
                    return_date=flight_ret_date,
                    is_direct=True
                )

                cheapest_offer = offers[0] if offers else None

                recommendations.append({
                    "destination_city": dest_city,
                    "destination_country": dest_country,
                    "destination_iata": dest_iata,
                    "visa_max_stay_days": visa_rule.max_days,
                    "visa_description": visa_rule.description,
                    "flight_found": cheapest_offer is not None,
                    "flight_details": cheapest_offer.model_dump() if cheapest_offer else None
                })

        return {
            "traveler_name": traveler_history_data.get("traveler_name", "Traveler"),
            "passport_nationality": passport,
            "status": status,
            "requires_action": requires_action,
            "escape_recommendations": recommendations
        }
