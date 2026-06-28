import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define project base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TRAVELER_HISTORY_FILE = DATA_DIR / "traveler_history.json"
VISA_RULES_FILE = DATA_DIR / "visa_rules.json"

# API keys and secret retrieval
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_SECRET = os.getenv("AMADEUS_SECRET", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Determine whether we should run in mock mode
# Mock mode is active if credentials are empty, placeholders, or unset.
def is_amadeus_mocked() -> bool:
    placeholders = ["______YOUR_API_KEY_____", "your_amadeus_key", ""]
    return (
        not AMADEUS_API_KEY
        or not AMADEUS_SECRET
        or AMADEUS_API_KEY.strip() in placeholders
        or AMADEUS_SECRET.strip() in placeholders
    )

def is_gemini_mocked() -> bool:
    placeholders = ["", "YOUR_GEMINI_API_KEY"]
    return not GEMINI_API_KEY or GEMINI_API_KEY.strip() in placeholders
