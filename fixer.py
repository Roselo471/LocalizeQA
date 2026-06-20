"""
fixer.py — Auto-fix module for LocalizeQA

Takes the original text, translation, and evaluation results,
then generates an improved translation that addresses the flagged issues.
"""

from openai import OpenAI


FIX_PROMPT = """You are a senior travel content localizer. You are given an English source text, 
its Chinese translation, and a quality evaluation report that identified specific issues.

Your job is to produce an IMPROVED Chinese translation that fixes ALL flagged issues 
while keeping everything that was already good.

## Source (English)
{source_text}

## Current Translation (Chinese)
{current_translation}

## Issues Found
{issues_text}

## Fix Requirements
1. Fix every issue listed above. Do not ignore any.
2. Keep the parts of the current translation that had no issues — do not rewrite everything.
3. For currency amounts, add approximate RMB equivalents in parentheses, e.g., "15英镑（约140元人民币）"
4. For cultural concepts unfamiliar to Chinese travelers (tipping, congestion charges, etc.), add a brief explanatory note.
5. Use natural Chinese phrasing — avoid translationese.
6. Keep proper nouns with their original English in parentheses on first mention.

## Output Format
Return ONLY the improved Chinese translation. No explanations, no markdown.
"""


def fix(
    source_text: str,
    current_translation: str,
    eval_result: dict,
    client: OpenAI,
) -> dict:
    """
    Generate an improved translation based on evaluation feedback.

    Args:
        source_text: Original English text
        current_translation: Current Chinese translation
        eval_result: Evaluation result dictionary from evaluator.py
        client: OpenAI-compatible API client

    Returns:
        Dictionary with fixed translation and change summary
    """
    # Collect all issues from evaluation
    all_issues = []
    dimensions = ["accuracy", "fluency", "cultural_adaptation", "terminology"]

    for dim in dimensions:
        dim_data = eval_result.get(dim, {})
        issues = dim_data.get("issues", [])
        if issues:
            dim_label = {
                "accuracy": "准确性",
                "fluency": "流畅度",
                "cultural_adaptation": "文化适配",
                "terminology": "术语一致性",
            }[dim]
            for issue in issues:
                all_issues.append(f"[{dim_label}] {issue}")

    # If no issues found, no fix needed
    if not all_issues:
        return {
            "fixed_translation": current_translation,
            "had_issues": False,
            "issues_fixed": [],
            "changes": "无需修复，翻译质量已达标。",
        }

    # Build issues text
    issues_text = "\n".join(f"- {issue}" for issue in all_issues)

    # Call the API
    prompt = FIX_PROMPT.format(
        source_text=source_text,
        current_translation=current_translation,
        issues_text=issues_text,
    )

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        max_tokens=2000,
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    fixed_translation = response.choices[0].message.content

    return {
        "fixed_translation": fixed_translation,
        "had_issues": True,
        "issues_fixed": all_issues,
        "changes": f"修复了 {len(all_issues)} 个问题。",
    }


def format_diff(original: str, fixed: str) -> str:
    """
    Format a simple before/after comparison.

    Args:
        original: Original translation
        fixed: Fixed translation

    Returns:
        Formatted comparison string
    """
    lines = []
    lines.append(f"  [Before]")
    lines.append(f"  {original}")
    lines.append(f"")
    lines.append(f"  [After]")
    lines.append(f"  {fixed}")
    return "\n".join(lines)
