# I Built an AI-Powered Localization QA System — Here's What I Learned

As someone working in AI localization QA, I noticed a gap: AI can translate travel content fast, but the quality assessment still relies on manual review. So I built LocalizeQA — a system that automates the full pipeline from translation to evaluation to fixing.

Here's what I learned building it.

## The Real Problem Isn't Translation — It's Cultural Adaptation

When I was doing QA work at Welo Data (Welocalize), evaluating AI translations of hotel and travel content, I kept seeing the same pattern: the translations were grammatically correct but culturally tone-deaf.

For example, a hotel FAQ about tipping in the US would be translated accurately into Chinese — but a Chinese traveler reading it would have no idea how much "$2-5" actually is, because the translation didn't include an RMB equivalent. Or a car rental tip mentioning Uber would be translated literally, even though Chinese travelers use Didi.

These aren't translation errors. They're localization failures. And they happen systematically because the AI doesn't know what the target audience needs.

## So I Built a System to Catch These Issues Automatically

LocalizeQA runs a three-stage pipeline:

**Stage 1: Translate** — Not word-for-word, but with explicit instructions for cultural adaptation (convert units, explain unfamiliar concepts, suggest local alternatives).

**Stage 2: Evaluate** — Score the translation across four dimensions: Accuracy, Fluency, Cultural Adaptation, and Terminology Consistency. Each dimension gets a 1-5 score with specific issues identified.

**Stage 3: Fix** — Take the evaluation feedback and generate an improved translation that addresses every flagged issue.

## The Hardest Problem: AI Grading Its Own Homework

The first version of my evaluator gave every translation a perfect 5/5 score. Every. Single. One.

This is a well-known issue called self-evaluation bias — when an LLM evaluates output from a similar model, it tends to be overly generous. It's like asking a student to grade their own exam.

My solution was what I call "anti-bias calibration" — adding explicit instructions to the evaluation prompt:
- "A score of 5 should be RARE"
- "Most good translations score 3-4"
- "If you find ZERO issues across all 4 dimensions, re-read more carefully"
- A checklist of common localization issues to actively look for

After calibration, the evaluator started catching real issues — missing currency conversions, untranslated cultural concepts, subtle accuracy shifts. The average score dropped from 5.0 to 4.87, which is much more realistic.

## Another Surprise: The API Kept Returning Empty Responses

I used DeepSeek V4's API for the LLM backend. About 30% of my evaluation calls were failing — returning empty strings instead of JSON.

After debugging, I found the cause: DeepSeek V4 has a "thinking mode" that sometimes conflicts with the `response_format: json_object` parameter. The model would "think" but produce no output.

The fix was simple — remove the forced JSON format and rely on prompt instructions plus robust parsing with three fallback layers:
1. Extract JSON boundaries from the response
2. Clean common formatting issues (trailing commas, comments)  
3. Retry with a simplified prompt if parsing fails

This brought my success rate from ~60% to ~95%.

## What the Benchmark Revealed

I built a test suite of 12 travel content samples (hotel FAQs, car rental tips, city guides, transport info) and ran them all through the pipeline.

Key findings:
- **Cultural Adaptation is the weakest dimension** (4.53/5.0 average) — confirming that this is where AI translation needs the most help
- **Transport content is hardest to localize** (4.55/5.0) — because it involves the most cultural-specific concepts (toll systems, ride-hailing apps, transit cards)
- **The #1 issue is missing currency conversion** — appeared in almost every sample that mentioned prices

## Tech Stack & What I Learned

- **Python** for the core pipeline (modular design: each stage is an independent module)
- **DeepSeek V4 API** via OpenAI-compatible SDK (cost-effective for development)
- **SQLite** for tracking translation history and quality trends
- **Streamlit + Plotly** for the web dashboard
- **Git/GitHub** for version control

Building this project taught me more than any tutorial could: API integration, database design, error handling in production, prompt engineering at scale, and the importance of testing your assumptions (like "surely the AI will grade fairly").

## What's Next

I'm planning to add support for more target languages (Japanese, Spanish), build a REST API layer, and create a human-in-the-loop interface for calibrating the evaluation model against expert annotations.

If you're working in localization, AI content, or multilingual systems, I'd love to connect and hear about the challenges you're facing.

**Try it out:** [GitHub](https://github.com/YOUR_USERNAME/LocalizeQA) | [Live Demo](https://localizeqa.streamlit.app)

---
*Built by Jie Xu — CS student at University of the People, AI localization QA at Welo Data*
