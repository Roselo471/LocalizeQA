"""
main.py — Entry point for LocalizeQA

Run this script to test the translation pipeline.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from translator import translate, CONTENT_TYPES

# Load API key from .env file
load_dotenv()


def main():
    # Initialize the DeepSeek client (OpenAI-compatible)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("ERROR: Please set your DEEPSEEK_API_KEY in the .env file.")
        print("  1. Copy .env.example to .env")
        print("  2. Replace 'your_api_key_here' with your actual API key")
        print("  3. Get your key at: https://platform.deepseek.com/")
        return

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    # === Sample travel content for testing ===
    samples = [
        {
            "type": "car_rental",
            "title": "Cashless Toll Roads",
            "text": (
                "Many highways around Orlando use cashless electronic tolls. "
                "Ask your rental desk about adding a toll transponder to your "
                "booking so you can drive through checkpoints without stopping."
            ),
        },
        {
            "type": "hotel_faq",
            "title": "Tipping at Hotels",
            "text": (
                "In the United States, it is customary to tip hotel staff. "
                "A typical tip for housekeeping is $2-5 per night, left on "
                "the pillow or nightstand. Bellhops usually receive $1-2 per bag. "
                "Concierge tips range from $5-20 depending on the service provided."
            ),
        },
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
        },
    ]

    print("=" * 60)
    print("  LocalizeQA — Translation Pipeline Test")
    print("=" * 60)

    for i, sample in enumerate(samples, 1):
        print(f"\n{'─' * 60}")
        print(f"  Sample {i}: {sample['title']}")
        print(f"  Type: {CONTENT_TYPES[sample['type']]}")
        print(f"{'─' * 60}")
        print(f"\n  [English Source]")
        print(f"  {sample['text']}")

        print(f"\n  Translating...", end=" ", flush=True)

        try:
            result = translate(
                source_text=sample["text"],
                content_type=sample["type"],
                client=client,
            )
            print("Done!")
            print(f"\n  [Chinese Translation]")
            print(f"  {result}")
        except Exception as e:
            print(f"Failed!")
            print(f"  Error: {e}")

    print(f"\n{'=' * 60}")
    print("  Translation complete. Next step: quality evaluation.")
    print("=" * 60)


if __name__ == "__main__":
    main()
