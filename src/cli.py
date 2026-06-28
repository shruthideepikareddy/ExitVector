import argparse
import json
import sys
import warnings
from datetime import date
from pathlib import Path

# Suppress deprecation and other low-level warnings for a clean user-facing CLI output
warnings.filterwarnings("ignore")

# Force UTF-8 encoding on stdout/stderr to avoid emoji crash on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from src import config
from src.compliance.rules import parse_date, SchengenComplianceEngine
from src.recommender.engine import TravelAdvisoryEngine

def load_traveler_data() -> dict:
    if not config.TRAVELER_HISTORY_FILE.exists():
        # Initialize default traveler profile
        default_data = {
            "traveler_name": "Explorer",
            "passport_nationality": "US",
            "history": []
        }
        save_traveler_data(default_data)
        return default_data
    
    with open(config.TRAVELER_HISTORY_FILE, "r") as f:
        return json.load(f)

def save_traveler_data(data: dict):
    with open(config.TRAVELER_HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def print_advisory_report(report: dict):
    print("=" * 60)
    print(f"✈️  TRAVEL ADVISORY REPORT FOR: {report['traveler_name'].upper()}")
    print(f"Passport: {report['passport_nationality']}")
    print("=" * 60)
    
    status = report["status"]
    ref_date = status["reference_date"]
    days_spent = status["days_spent"]
    days_remaining = status["days_remaining"]
    is_in_schengen = status["is_in_schengen"]
    overstay_date = status["overstay_date"]

    print(f"Evaluation Date: {ref_date}")
    print(f"Active in Schengen Area: {'Yes 🇪🇺' if is_in_schengen else 'No'}")
    print(f"Schengen Days Used (Last 180 Days): {days_spent}/90 days")
    
    if is_in_schengen:
        if status["is_compliant"]:
            print(f"Days Remaining Before Exit Required: {days_remaining} days")
            print(f"⚠️  MUST EXIT BY (Hard Overstay Limit): {overstay_date}")
        else:
            print("🚨 VIOLATION: You have exceeded the 90-day limit in the Schengen Area!")
    else:
        print(f"Accumulated stay capacity remaining: {days_remaining} days")

    print("-" * 60)

    if report["requires_action"]:
        print("🚨 ACTION REQUIRED: You are close to overstaying your Schengen stay limit!")
        print("Here are the cheapest escape flights to compliant non-Schengen destinations:")
        print("-" * 60)
        
        for rec in report["escape_recommendations"]:
            print(f"📍 Destination: {rec['destination_city']}, {rec['destination_country']} ({rec['destination_iata']})")
            print(f"   ℹ️  Visa Limit for {report['passport_nationality']} passport: {rec['visa_max_stay_days']} days max stay.")
            print(f"   📜 Rule Details: {rec['visa_description']}")
            
            if rec["flight_found"] and rec["flight_details"]:
                f = rec["flight_details"]
                print(f"   💸 Best Flight: ${f['price']} USD")
                print(f"      Outbound: {f['departure_date']} | Return: {f['return_date']}")
                print(f"      Carrier: {f['airline']} | Stops: {f['stops']}")
            else:
                print("   ❌ No flight offers found for target dates.")
            print("-" * 60)
    else:
        print("✅ STATUS GREEN: No immediate exit flights required. You have safe headroom.")
        print("=" * 60)

def handle_history(args):
    data = load_traveler_data()
    history = data.get("history", [])
    if not history:
        print("No travel logs found. Add a trip using 'add' command.")
        return

    print(f"\nTravel Logs for {data['traveler_name']} ({data['passport_nationality']}):")
    print(f"{'City':<15} | {'Country':<15} | {'Region':<10} | {'Arrival':<12} | {'Departure':<12}")
    print("-" * 75)
    for entry in history:
        dep = entry.get("departure_date") or "Ongoing/Active"
        print(f"{entry['city']:<15} | {entry['country']:<15} | {entry.get('region', 'N/A'):<10} | {entry['arrival_date']:<12} | {dep:<12}")
    print()

def handle_add(args):
    data = load_traveler_data()
    
    # Validation
    try:
        date.fromisoformat(args.arrival)
        if args.departure:
            date.fromisoformat(args.departure)
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format.")
        sys.exit(1)

    new_trip = {
        "city": args.city,
        "country": args.country,
        "region": args.region,
        "arrival_date": args.arrival,
        "departure_date": args.departure
    }

    # If there's an ongoing trip and we are adding another ongoing trip, close the previous one
    if not args.departure:
        for entry in data["history"]:
            if entry.get("departure_date") is None:
                print(f"Warning: Ongoing stay in {entry['city']} was active. Automatically setting its departure to today/arrival date of new trip.")
                entry["departure_date"] = args.arrival

    data["history"].append(new_trip)
    save_traveler_data(data)
    print(f"Success: Added trip to {args.city}, {args.country} ({args.region}) starting {args.arrival}.")

def handle_status(args):
    data = load_traveler_data()
    ref_date = parse_date(args.date) if args.date else date.today()
    
    engine = SchengenComplianceEngine(data.get("history", []))
    res = engine.check_compliance(ref_date)
    
    print("\n" + "=" * 45)
    print(f"📊 VISA STATUS FOR {data['traveler_name'].upper()}")
    print("=" * 45)
    print(f"As of Date:         {res['reference_date']}")
    print(f"In Schengen:        {res['is_in_schengen']}")
    print(f"Days Used (180d):   {res['days_spent']}/90")
    print(f"Days Remaining:     {res['days_remaining']}")
    print(f"Compliant:          {res['is_compliant']}")
    if res['overstay_date']:
        print(f"🚨 Overstay Date:   {res['overstay_date']}")
    print("=" * 45 + "\n")

def handle_advisory(args):
    data = load_traveler_data()
    ref_date = parse_date(args.date) if args.date else date.today()
    
    advisory_engine = TravelAdvisoryEngine()
    report = advisory_engine.generate_advisory(data, ref_date)
    print_advisory_report(report)

def main():
    parser = argparse.ArgumentParser(
        description="ExitVector: Autonomous Travel Compliance & Escape Flight Engine"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # History Command
    subparsers.add_parser("history", help="List traveler's history logs")

    # Add Trip Command
    add_parser = subparsers.add_parser("add", help="Add a new trip entry to history")
    add_parser.add_argument("--city", required=True, help="City visited")
    add_parser.add_argument("--country", required=True, help="Country visited")
    add_parser.add_argument("--region", required=True, choices=["Schengen", "Non-Schengen"], help="Geographical compliance region")
    add_parser.add_argument("--arrival", required=True, help="Arrival date (YYYY-MM-DD)")
    add_parser.add_argument("--departure", default=None, help="Departure date (YYYY-MM-DD), leave blank if current ongoing stay")

    # Status Command
    status_parser = subparsers.add_parser("status", help="Calculate Schengen visa limits")
    status_parser.add_argument("--date", default=None, help="Reference date (YYYY-MM-DD), defaults to today")

    # Advisory Command
    advisory_parser = subparsers.add_parser("advisory", help="Generate flight advice and compliance exits")
    advisory_parser.add_argument("--date", default=None, help="Reference date (YYYY-MM-DD), defaults to today")

    args = parser.parse_args()

    if args.command == "history":
        handle_history(args)
    elif args.command == "add":
        handle_add(args)
    elif args.command == "status":
        handle_status(args)
    elif args.command == "advisory":
        handle_advisory(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
