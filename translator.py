"""
translator.py — Core translation module for LocalizeQA

Handles English-to-Chinese translation of travel content
with cultural adaptation awareness.

Uses DeepSeek API (OpenAI-compatible format).
"""

from openai import OpenAI


# Content type definitions - different types need different translation strategies
CONTENT_TYPES = {
    "hotel_faq": "酒店常见问题",
    "car_rental": "租车提示",
    "city_guide": "城市指南",
    "transport": "交通指引",
}

# Translation prompt template
TRANSLATION_PROMPT = """You are a professional travel content localizer specializing in English to Simplified Chinese translation.

## Task
Translate the following travel content into natural, culturally adapted Simplified Chinese.

## Content Type
{content_type}

## Rules
1. Do NOT do word-for-word translation. Rewrite naturally as if originally written in Chinese for Chinese travelers.
2. Convert measurements to metric if needed (miles → km, Fahrenheit → Celsius).
3. Adapt cultural references — for example, explain payment methods or tipping customs unfamiliar to Chinese travelers.
4. Keep proper nouns (place names, brand names) in their original form with Chinese translation in parentheses on first mention.
5. Use a friendly, informative tone — not overly formal, not too casual.
6. If the content mentions services that work differently in the local market (e.g., toll systems, ride-hailing apps), add a brief note for Chinese travelers.

## Source Content
{source_text}

## Output Format
Return ONLY the translated Chinese text. No explanations, no notes, no markdown formatting.
"""


def translate(source_text: str, content_type: str, client: OpenAI) -> str:
    """
    Translate English travel content to Simplified Chinese.

    Args:
        source_text: English text to translate
        content_type: One of "hotel_faq", "car_rental", "city_guide", "transport"
        client: OpenAI-compatible API client (pointed at DeepSeek)

    Returns:
        Translated Chinese text
    """
    # Validate content type
    if content_type not in CONTENT_TYPES:
        raise ValueError(
            f"Unknown content type: {content_type}. "
            f"Must be one of: {list(CONTENT_TYPES.keys())}"
        )

    # Build the prompt
    prompt = TRANSLATION_PROMPT.format(
        content_type=CONTENT_TYPES[content_type],
        source_text=source_text,
    )

    # Call the API
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    # Extract text from response
    return response.choices[0].message.content
