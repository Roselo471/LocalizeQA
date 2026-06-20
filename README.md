# LocalizeQA — AI-Powered Localization Quality Assessment System

An automated quality assessment system for English-to-Chinese travel content localization, powered by LLMs.

## What It Does

- Translates English travel content (hotel FAQs, car rental tips, city guides) into natural, culturally adapted Simplified Chinese
- Automatically evaluates translation quality across 4 dimensions: Accuracy, Fluency, Cultural Adaptation, Terminology Consistency
- Generates improvement suggestions for flagged issues
- Tracks translation history and quality trends

## Tech Stack

- **Language:** Python 3.10+
- **LLM API:** DeepSeek API (OpenAI-compatible)
- **Database:** SQLite (planned)
- **Backend:** FastAPI (planned)
- **Frontend:** Streamlit (planned)
- **Deployment:** Docker + Streamlit Cloud (planned)

## Project Status

- [x] Project setup
- [x] Core translation module
- [ ] Quality evaluation module
- [ ] Fix suggestion module
- [ ] Database layer
- [ ] REST API
- [ ] Web interface
- [ ] Automated benchmark
- [ ] Deployment

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/LocalizeQA.git
cd LocalizeQA
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your API key

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

### 4. Run

```bash
python main.py
```

## Project Structure

```
LocalizeQA/
├── main.py              # Entry point
├── translator.py        # Translation module
├── evaluator.py         # Quality evaluation module (coming soon)
├── fixer.py             # Fix suggestion module (coming soon)
├── requirements.txt     # Python dependencies
├── .env.example         # API key template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Background

Built from real-world experience doing AI localization QA at Welo Data (Welocalize). This project automates the manual quality assessment workflow — moving from human-in-the-loop evaluation to a systematic, scalable pipeline.

## License

MIT
