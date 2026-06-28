import random
from datetime import date
from typing import List
from src.flight_search.amadeus_client import FlightOffer

class MockAmadeusClient:
    def __init__(self):
        # Local mapping of common cities to IATA codes
        self.city_mapping = {
            "london": "LON",
            "paris": "PAR",
            "rome": "FCO",
            "berlin": "BER",
            "istanbul": "IST",
            "tirana": "TIA",
            "dublin": "DUB",
            "edinburgh": "EDI",
            "athens": "ATH",
            "madrid": "MAD",
            "barcelona": "BCN",
            "amsterdam": "AMS"
        }
        self.airlines = ["FR", "U2", "W6", "LH", "BA", "TK", "TO"]

    def get_destination_code(self, city_name: str) -> str:
        name_lower = city_name.lower().strip()
        # Fallback to a synthetic 3-letter uppercase string if city is unknown
        return self.city_mapping.get(name_lower, name_lower[:3].upper())

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date,
        is_direct: bool = True
    ) -> List[FlightOffer]:
        """Generate realistic mock flight offers."""
        # Seeding random based on origin/destination to make it consistent across calls
        random.seed(hash(origin + destination + str(departure_date)))
        
        # Decide base price based on distance estimate (mocked)
        # Schengen to non-Schengen (e.g. LON, TIA, IST)
        if destination in ["LON", "LHR", "LGW"]:
            base_price = 45.0
            airline = "FR" # Ryanair
        elif destination in ["TIA"]:
            base_price = 55.0
            airline = "W6" # Wizz Air
        elif destination in ["IST"]:
            base_price = 110.0
            airline = "TK" # Turkish Airlines
        else:
            base_price = 30.0 + random.randint(10, 80)
            airline = random.choice(self.airlines)

        offers = []
        # Generate 3 flight options with varying prices and stops
        for i in range(3):
            multiplier = 1.0 + (i * 0.15)
            stops = 0 if is_direct else random.randint(1, 2)
            
            offers.append(
                FlightOffer(
                    origin=origin,
                    destination=destination,
                    price=round(base_price * multiplier, 2),
                    departure_date=departure_date.isoformat(),
                    return_date=return_date.isoformat(),
                    stops=stops,
                    airline=airline if i == 0 else random.choice(self.airlines)
                )
            )

        # Sort by price ascending
        offers.sort(key=lambda x: x.price)
        return offers
