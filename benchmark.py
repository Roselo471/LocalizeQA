"""
benchmark.py — Automated benchmark for LocalizeQA

Runs the full pipeline (translate → evaluate → fix) on a curated
test dataset, stores results in the database, and generates a
quality report.
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
from translator import translate, CONTENT_TYPES
from evaluator import evaluate
from fixer import fix
from database import get_connection, save_record, get_stats, get_stats_by_type, get_common_issues, format_stats_report

load_dotenv()

# === Test Dataset ===
# Curated from real travel content patterns, covering different
# content types and localization challenges.

TEST_SAMPLES = [
    # --- Hotel FAQ ---
    {
        "type": "hotel_faq",
        "title": "Tipping at Hotels",
        "text": (
            "In the United States, it is customary to tip hotel staff. "
            "A typical tip for housekeeping is $2-5 per night, left on "
            "the pillow or nightstand. Bellhops usually receive $1-2 per bag."
        ),
        "challenges": ["tipping culture", "currency"],
    },
    {
        "type": "hotel_faq",
        "title": "Early Check-in",
        "text": (
            "Early check-in is available from 12 PM subject to availability. "
            "You can request it through the front desk or via the hotel app. "
            "A fee of $25-50 may apply depending on the room type."
        ),
        "challenges": ["time format", "currency", "app reference"],
    },
    {
        "type": "hotel_faq",
        "title": "Resort Fees",
        "text": (
            "Please note that a daily resort fee of $35 plus tax will be "
            "added to your bill. This covers Wi-Fi, pool access, fitness "
            "center, and local phone calls. The fee is charged per room, "
            "not per guest."
        ),
        "challenges": ["resort fee concept", "currency", "tax system"],
    },
    {
        "type": "hotel_faq",
        "title": "Ice Machine Location",
        "text": (
            "Ice machines are located on every other floor near the elevator. "
            "Ice buckets and plastic bags are provided in your room. "
            "Please do not use the coffee maker to melt ice."
        ),
        "challenges": ["hotel amenity terms", "floor layout"],
    },

    # --- Car Rental ---
    {
        "type": "car_rental",
        "title": "Cashless Toll Roads",
        "text": (
            "Many highways around Orlando use cashless electronic tolls. "
            "Ask your rental desk about adding a toll transponder to your "
            "booking so you can drive through checkpoints without stopping."
        ),
        "challenges": ["toll system", "transponder concept"],
    },
    {
        "type": "car_rental",
        "title": "Fuel Policy",
        "text": (
            "Your rental comes with a full tank of gas. Please return it "
            "full to avoid a refueling charge of $9.99 per gallon. Gas "
            "stations near the airport typically charge $3.50-4.00 per gallon."
        ),
        "challenges": ["gallon to liter", "currency", "fuel terms"],
    },
    {
        "type": "car_rental",
        "title": "GPS Navigation",
        "text": (
            "A GPS unit can be added to your rental for $15 per day. "
            "Alternatively, you can use Google Maps or Waze on your "
            "phone — just make sure to download offline maps before "
            "leaving the airport."
        ),
        "challenges": ["app alternatives for China", "currency", "offline maps"],
    },

    # --- City Guide ---
    {
        "type": "city_guide",
        "title": "Getting Around London",
        "text": (
            "The London Underground (the Tube) is the fastest way to get "
            "around central London. Buy an Oyster card at any station for "
            "discounted fares. Contactless payment cards also work on all "
            "Transport for London services. Avoid driving in central London "
            "due to the Congestion Charge (£15 per day)."
        ),
        "challenges": ["contactless payment", "currency conversion", "Oyster card"],
    },
    {
        "type": "city_guide",
        "title": "Street Food in Bangkok",
        "text": (
            "Bangkok's street food scene is legendary. Head to Yaowarat "
            "(Chinatown) for the best pad thai and mango sticky rice. "
            "Most dishes cost 40-80 baht ($1-2). Eat where the locals "
            "eat — long lines are a good sign."
        ),
        "challenges": ["currency", "food terms", "cultural tips"],
    },
    {
        "type": "city_guide",
        "title": "Taxis in Tokyo",
        "text": (
            "Tokyo taxis are safe and metered. The base fare starts at "
            "¥500 (about $3.50). Doors open and close automatically — "
            "do not touch them. Most drivers speak limited English, so "
            "have your destination written in Japanese or show it on "
            "Google Maps."
        ),
        "challenges": ["currency", "cultural customs", "app reference"],
    },

    # --- Transport ---
    {
        "type": "transport",
        "title": "Airport Express Train",
        "text": (
            "The Airport Express train departs every 12 minutes from "
            "Terminal 1 and takes 24 minutes to reach Central Station. "
            "A single ticket costs HK$115 ($15). You can buy tickets at "
            "the station or use your Octopus card for a faster entry."
        ),
        "challenges": ["dual currency", "Octopus card", "transit terms"],
    },
    {
        "type": "transport",
        "title": "Ride-Hailing Apps",
        "text": (
            "Uber and Lyft are widely available in most US cities. "
            "Download the app before your trip and link a credit card. "
            "Rides from the airport typically cost $25-45 depending on "
            "your destination. Surge pricing may apply during peak hours."
        ),
        "challenges": ["app alternatives", "currency", "surge pricing concept"],
    },
]


def run_benchmark():
    """Run the full benchmark on all test samples."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("ERROR: Please set your DEEPSEEK_API_KEY in the .env file.")
        return

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    conn = get_connection()

    total = len(TEST_SAMPLES)
    success = 0
    failed = 0

    print("=" * 60)
    print(f"  LocalizeQA — Benchmark ({total} samples)")
    print("=" * 60)

    for i, sample in enumerate(TEST_SAMPLES, 1):
        print(f"\n  [{i}/{total}] {sample['title']} ({CONTENT_TYPES[sample['type']]})")

        # Step 1: Translate
        print(f"    Translating...", end=" ", flush=True)
        try:
            translation = translate(
                source_text=sample["text"],
                content_type=sample["type"],
                client=client,
            )
            print("OK", end=" → ", flush=True)
        except Exception as e:
            print(f"FAILED ({e})")
            failed += 1
            continue

        # Step 2: Evaluate
        print("Evaluating...", end=" ", flush=True)
        try:
            eval_result = evaluate(
                source_text=sample["text"],
                translated_text=translation,
                content_type=sample["type"],
                client=client,
            )
            score = eval_result.get("overall_score", 0)
            print(f"{score}/5.0", end=" → ", flush=True)
        except Exception as e:
            print(f"FAILED ({e})")
            failed += 1
            continue

        # Step 3: Fix
        print("Fixing...", end=" ", flush=True)
        try:
            fix_result = fix(
                source_text=sample["text"],
                current_translation=translation,
                eval_result=eval_result,
                client=client,
            )
            if fix_result["had_issues"]:
                print(f"Fixed {len(fix_result['issues_fixed'])} issues", end="", flush=True)
            else:
                print("No issues", end="", flush=True)
        except Exception as e:
            print(f"FAILED ({e})")
            fix_result = None

        # Step 4: Save to database
        try:
            save_record(
                conn=conn,
                source_text=sample["text"],
                translated_text=translation,
                content_type=sample["type"],
                eval_result=eval_result,
                fix_result=fix_result,
            )
            print(" → Saved ✓")
            success += 1
        except Exception as e:
            print(f" → Save FAILED ({e})")
            failed += 1

    # Generate report
    print(f"\n  Benchmark complete: {success}/{total} successful, {failed} failed")

    stats = get_stats(conn)
    by_type = get_stats_by_type(conn)
    common_issues = get_common_issues(conn)

    report = format_stats_report(stats, by_type, common_issues)
    print(f"\n{report}")

    conn.close()


if __name__ == "__main__":
    run_benchmark()
