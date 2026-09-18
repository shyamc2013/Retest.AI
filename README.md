# Retest.AI

A local Streamlit study app that creates source-grounded practice tests and adapts the next test to the learner's weak topics.

## Setup

1. Put your source PDF, DOCX, and/or PPTX files in `docs/`. The app discovers files by extension; filenames do not matter.
2. Create `.env` in this project directory with `GROQ_API_KEY=your_key_here` (or copy `.env.example`).
3. Install dependencies: `pip install -r requirements.txt`
4. Start the app: `python -m streamlit run app.py` (equivalent to `streamlit run app.py` when the Scripts directory is on your PATH).

Each completed attempt is saved as a separate YAML file in `feedback/`. The next test uses only the latest attempt to target weak topics. Fill-in-the-blank answers deliberately use case-insensitive, trimmed exact matching in v1, so equivalent phrasings may occasionally be marked wrong.

The application uses Groq's `openai/gpt-oss-20b` model. Its model name is configured in `config.py`.
