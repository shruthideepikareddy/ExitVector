# 🛫 ExitVector

An autonomous travel compliance engine for digital nomads. ExitVector tracks your travel history, computes your Schengen visa window using a rolling 180-day algorithm, retrieves country-specific stay limits via generative AI, and surfaces the cheapest compliant escape flights before you overstay.

---

## 🌟 Why This Project Stands Out (Resume Highlights)

Instead of a generic tutorial project, this project showcases advanced software engineering and system design concepts:

* **Schengen Rolling 180-Day Window Algorithm**: Implements the official European Union rolling-window presence calculation. It utilizes set-based date deduplication to ensure flight transit days and layovers are not double-counted across state transfers.
* **AI-Driven Visa Rule Extraction**: Leverages the Gemini API with structured schema output definitions. Instead of hardcoding visa regulations for 190+ countries, it uses an LLM to parse travel rules into validated Pydantic models.
* **Pluggable client design (Strategy Pattern)**: Features a decoupled flight search infrastructure with a live `AmadeusClient` and a fully offline `MockAmadeusClient` for mock simulations and local unit testing.
* **Caching & Cost Optimization**: Implements a local JSON-based document cache to store extracted visa rules, minimizing LLM token consumption and bypassing external API rate limits.
* **Resilient Systems Engineering**: Configured with automated UTF-8 terminal reconfigurations to prevent Unicode/emoji rendering crashes in legacy Windows shell environments (e.g., `cp1252`).

---

## 🛠️ System Architecture

```text
               +-----------------------+
               | Traveler History Logs |
               +-----------+-----------+
                           |
                           v
             +-------------+-------------+
             | Schengen Compliance Engine|
             +-------------+-------------+
                           |
                           v  (Exceeding 90-day threshold?)
             +-------------+-------------+
             |  Travel Advisory Recommender  |
             +------+--------------+-----+
                    |              |
     (Get Visa Rules)              (Search Escape Routes)
                    v              v
     +--------------+-----+  +-----+---------------+
     |  AI Rule Extractor |  | Flight Search Client|
     | (Gemini / Cache DB)|  | (Live Amadeus/Mock) |
     +--------------------+  +---------------------+
```

---

## 🚀 Getting Started

### Prerequisites

* Python 3.8+
* [Optional] Amadeus API Key & Secret (if running live)
* [Optional] Gemini API Key (if fetching custom visa rules live)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/NomadTax-Visa-Tracker.git
   cd NomadTax-Visa-Tracker
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   AMADEUS_API_KEY=your_amadeus_key_here
   AMADEUS_SECRET=your_amadeus_secret_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   *Note: If no API keys are provided (or if placeholders are detected), the system automatically runs in offline MOCK mode for flight searches and visa rule extraction.*

---

## 🖥️ CLI Usage

The system exposes a rich, interactive Command Line Interface to manage travel history and check compliance:

### 1. View Travel Logs
Displays the traveler's historical journeys and ongoing stays:
```bash
python -m src.cli history
```

### 2. Add a New Trip
Append a trip to your travel history. Leave off `--departure` to record an active, ongoing stay:
```bash
python -m src.cli add --city Paris --country France --region Schengen --arrival 2026-05-01 --departure 2026-06-15
```

### 3. Check Stay Statistics
Run the compliance algorithm for a specific date (defaults to today):
```bash
python -m src.cli status --date 2026-06-28
```
**Example Output:**
```text
=============================================
📊 VISA STATUS FOR SOFIA
=============================================
As of Date:         2026-06-28
In Schengen:        True
Days Used (180d):   82/90
Days Remaining:     8
Compliant:          True
🚨 Overstay Date:   2026-07-06
=============================================
```

### 4. Get Advisory Exit Flights
Generates exit flight recommendations and displays local visa requirements for target safe zones if stay limits are nearing:
```bash
python -m src.cli advisory --date 2026-06-28
```
**Example Output:**
```text
[Info] Amadeus credentials missing or placeholder. Running in MOCK flight search mode.
[Warning] Schengen overstay date is 2026-07-06. Searching flights leaving Berlin (BER) around 2026-07-03...
============================================================
✈️  TRAVEL ADVISORY REPORT FOR: SOFIA
Passport: US
============================================================
Evaluation Date: 2026-06-28
Active in Schengen Area: Yes 🇪🇺
Schengen Days Used (Last 180 Days): 82/90 days
Days Remaining Before Exit Required: 8 days
⚠️  MUST EXIT BY (Hard Overstay Limit): 2026-07-06
------------------------------------------------------------
🚨 ACTION REQUIRED: You are close to overstaying your Schengen stay limit!
Here are the cheapest escape flights to compliant non-Schengen destinations:
------------------------------------------------------------
📍 Destination: London, United Kingdom (LON)
   ℹ️  Visa Limit for US passport: 180 days max stay.
   📜 Rule Details: US citizens can stay in the UK for up to 6 months (180 days) per entry/year.
   💸 Best Flight: $45.0 USD
      Outbound: 2026-07-03 | Return: 2026-08-02
      Carrier: FR | Stops: 0
------------------------------------------------------------
📍 Destination: Istanbul, Turkey (IST)
   ℹ️  Visa Limit for US passport: 90 days max stay.
   📜 Rule Details: US citizens can stay in Turkey for up to 90 days in any 180-day period.
   💸 Best Flight: $110.0 USD
      Outbound: 2026-07-03 | Return: 2026-08-02
      Carrier: TK | Stops: 0
------------------------------------------------------------
📍 Destination: Tirana, Albania (TIA)
   ℹ️  Visa Limit for US passport: 365 days max stay.
   📜 Rule Details: US citizens can stay in Albania visa-free for up to 1 year.
   💸 Best Flight: $55.0 USD
      Outbound: 2026-07-03 | Return: 2026-08-02
      Carrier: W6 | Stops: 0
------------------------------------------------------------
```

---

## 🧪 Testing

To run the unit tests verifying Schengen rolling window math:
```bash
python -m pytest
```

**Test Execution Output:**
```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\sofia\OneDrive\Documents\Projects\FlightDealFinder\Flight-Deal-Finder
plugins: anyio-4.12.1, cov-7.0.0
collected 4 items

tests\test_compliance.py ....                                            [100%]

============================== 4 passed in 0.05s ==============================
```
