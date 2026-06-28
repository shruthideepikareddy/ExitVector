import requests
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel

from src import config

class FlightOffer(BaseModel):
    origin: str
    destination: str
    price: float
    departure_date: str
    return_date: str
    stops: int
    airline: str

class AmadeusClient:
    def __init__(self):
        self.api_key = config.AMADEUS_API_KEY
        self.api_secret = config.AMADEUS_SECRET
        self.token_endpoint = "https://test.api.amadeus.com/v1/security/oauth2/token"
        self.iata_endpoint = "https://test.api.amadeus.com/v1/reference-data/locations/cities"
        self.flight_endpoint = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        self._token = None
        self._token_expires_at = 0

    def _get_new_token(self) -> str:
        header = {'Content-Type': 'application/x-www-form-urlencoded'}
        body = {
            'grant_type': 'client_credentials',
            'client_id': self.api_key,
            'client_secret': self.api_secret
        }
        try:
            response = requests.post(url=self.token_endpoint, headers=header, data=body)
            response.raise_for_status()
            data = response.json()
            return data['access_token']
        except Exception as e:
            print(f"Error fetching Amadeus Token: {e}")
            raise

    @property
    def token(self) -> str:
        if not self._token:
            self._token = self._get_new_token()
        return self._token

    def get_destination_code(self, city_name: str) -> str:
        """Resolve city name to airport IATA code."""
        headers = {"Authorization": f"Bearer {self.token}"}
        query = {
            "keyword": city_name,
            "max": "2",
            "include": "AIRPORTS",
        }
        try:
            response = requests.get(url=self.iata_endpoint, headers=headers, params=query)
            response.raise_for_status()
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0]['iataCode']
            return "N/A"
        except Exception as e:
            print(f"Error resolving IATA for {city_name}: {e}")
            return "N/A"

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date,
        is_direct: bool = True
    ) -> List[FlightOffer]:
        """Search for flights and return a list of FlightOffer objects."""
        headers = {"Authorization": f"Bearer {self.token}"}
        query = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date.strftime("%Y-%m-%d"),
            "returnDate": return_date.strftime("%Y-%m-%d"),
            "adults": 1,
            "nonStop": "true" if is_direct else "false",
            "currencyCode": "USD",
            "max": "10"
        }
        
        try:
            response = requests.get(url=self.flight_endpoint, headers=headers, params=query)
            if response.status_code != 200:
                print(f"Amadeus Flight search failed with status {response.status_code}: {response.text}")
                return []
            
            data = response.json()
            offers = []
            
            if not data.get("data"):
                return []

            for flight in data["data"]:
                try:
                    price = float(flight["price"]["grandTotal"])
                    itineraries = flight["itineraries"]
                    
                    # Outbound leg stops and airline
                    outbound_segments = itineraries[0]["segments"]
                    nr_stops = len(outbound_segments) - 1
                    carrier = outbound_segments[0]["carrierCode"]
                    
                    # Extract date strings
                    dep_str = outbound_segments[0]["departure"]["at"].split("T")[0]
                    ret_str = itineraries[1]["segments"][0]["departure"]["at"].split("T")[0]
                    
                    offers.append(
                        FlightOffer(
                            origin=origin,
                            destination=destination,
                            price=price,
                            departure_date=dep_str,
                            return_date=ret_str,
                            stops=nr_stops,
                            airline=carrier
                        )
                    )
                except (IndexError, KeyError) as e:
                    # Skip malformed flight offers
                    continue
            
            # Sort by price ascending
            offers.sort(key=lambda x: x.price)
            return offers
        except Exception as e:
            print(f"Error searching flights from {origin} to {destination}: {e}")
            return []
