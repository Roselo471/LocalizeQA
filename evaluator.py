"""
evaluator.py — Quality evaluation module for LocalizeQA

Evaluates Chinese translations across 4 dimensions:
- Accuracy: Does the translation preserve the original meaning?
- Fluency: Does it read naturally in Chinese?
- Cultural Adaptation: Are references adapted for Chinese travelers?
- Terminology: Are travel/transport terms translated consistently and correctly?

Returns structured scores and specific issue descriptions.
"""

import json
from openai import OpenAI


EVALUATION_PROMPT = """You are a STRICT localization QA specialist for travel content.
You are evaluating a Simplified Chinese translation of English travel content.

## IMPORTANT: Evaluation Standards
- A score of 5 should be RARE. Only give 5 if the translation is truly flawless.
- Most good translations score 3-4. A score of 4 means high quality with minor issues.
- You MUST actively look for problems. Common issues include:
  * Missing cultural context for Chinese travelers (e.g., tipping customs not explained)
  * Units not converted (miles, Fahrenheit, pounds) or prices not given approximate RMB equivalents
  * "Contactless" mistranslated as "接触式" instead of "非接触式/闪付"
  * Translationese: phrases that are grammatically correct but no native Chinese speaker would say
  * Proper nouns translated when they should be kept in English, or vice versa
  * Missing practical tips that a Chinese traveler would need (e.g., how to pay, app alternatives)
- If you find ZERO issues across all 4 dimensions, re-read the translation more carefully.

## Source (English)
{source_text}

## Translation (Chinese)
{translated_text}

## Content Type
{content_type}

## Evaluation Criteria

Score each dimension from 1-5:
- 5 = Excellent, no issues
- 4 = Good, minor issues that don't affect comprehension
- 3 = Acceptable, noticeable issues but still usable
- 2 = Poor, significant issues that may confuse readers
- 1 = Unacceptable, critical errors or mistranslations

### Dimensions:
1. **Accuracy**: Does the translation faithfully convey ALL information from the source? Any omissions, additions, or distortions?
2. **Fluency**: Does it read naturally to a native Chinese speaker? Any awkward phrasing, translationese, or grammatical errors?
3. **Cultural Adaptation**: Are culture-specific references adapted for Chinese travelers? (e.g., payment methods, tipping customs, measurement units, app/service alternatives)
4. **Terminology**: Are travel, transport, and hospitality terms translated correctly and consistently? (e.g., toll transponder, congestion charge, Oyster card)

## Response Format
Respond with ONLY a valid JSON object, no markdown, no explanation:
{{
    "accuracy": {{
        "score": <1-5>,
        "issues": ["issue1", "issue2"] 
    }},
    "fluency": {{
        "score": <1-5>,
        "issues": ["issue1", "issue2"]
    }},
    "cultural_adaptation": {{
        "score": <1-5>,
        "issues": ["issue1", "issue2"]
    }},
    "terminology": {{
        "score": <1-5>,
        "issues": ["issue1", "issue2"]
    }},
    "overall_score": <average of 4 scores, rounded to 1 decimal>,
    "summary": "<1-2 sentence overall assessment in Chinese>"
}}

If a dimension has no issues, use an empty list: "issues": []
"""


def evaluate(
    source_text: str,
    translated_text: str,
    content_type: str,
    client: OpenAI,
) -> dict:
    """
    Evaluate translation quality across 4 dimensions.

    Args:
        source_text: Original English text
        translated_text: Chinese translation to evaluate
        content_type: Content category (hotel_faq, car_rental, etc.)
        client: OpenAI-compatible API client

    Returns:
        Dictionary with scores, issues, and summary
    """
    prompt = EVALUATION_PROMPT.format(
        source_text=source_text,
        translated_text=translated_text,
        content_type=content_type,
    )

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        max_tokens=1500,
        temperature=0.1,  # Low temperature for consistent evaluation
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    raw_output = response.choices[0].message.content

    # Handle None or empty response — retry once
    if not raw_output or not raw_output.strip():
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            max_tokens=1500,
            temperature=0.1,
            messages=[
                {"role": "user", "content": prompt + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. No other text."}
            ],
        )
        raw_output = response.choices[0].message.content or ""

    # Parse JSON from response, handling various formatting issues
    cleaned = raw_output.strip()

    # Remove markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )

    # Try to extract JSON object from the text
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        cleaned = cleaned[start:end]

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # Second attempt: remove trailing commas and comments
        import re
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        cleaned = re.sub(r'//.*?\n', '\n', cleaned)

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # Debug: print raw output so user can report the issue
            print(f"\n  [DEBUG] Raw API output: {repr(raw_output[:500])}")

            result = {
                "accuracy": {"score": 0, "issues": ["Failed to parse evaluation"]},
                "fluency": {"score": 0, "issues": ["Failed to parse evaluation"]},
                "cultural_adaptation": {"score": 0, "issues": ["Failed to parse evaluation"]},
                "terminology": {"score": 0, "issues": ["Failed to parse evaluation"]},
                "overall_score": 0,
                "summary": "评估失败：无法解析 AI 返回的结果",
                "_raw_output": raw_output,
            }

    return result


def format_report(eval_result: dict) -> str:
    """
    Format evaluation result into a readable report.

    Args:
        eval_result: Dictionary returned by evaluate()

    Returns:
        Formatted string report
    """
    dimensions = [
        ("Accuracy (准确性)", "accuracy"),
        ("Fluency (流畅度)", "fluency"),
        ("Cultural Adaptation (文化适配)", "cultural_adaptation"),
        ("Terminology (术语一致性)", "terminology"),
    ]

    lines = []
    lines.append(f"  Overall Score: {eval_result.get('overall_score', 'N/A')} / 5.0")
    lines.append(f"  Summary: {eval_result.get('summary', 'N/A')}")
    lines.append("")

    for label, key in dimensions:
        dim = eval_result.get(key, {})
        score = dim.get("score", "N/A")
        issues = dim.get("issues", [])

        # Score bar visualization
        if isinstance(score, (int, float)) and score > 0:
            bar = "█" * int(score) + "░" * (5 - int(score))
        else:
            bar = "░" * 5

        lines.append(f"  {label}: {bar} {score}/5")
        if issues:
            for issue in issues:
                lines.append(f"    - {issue}")
        lines.append("")

    return "\n".join(lines)
