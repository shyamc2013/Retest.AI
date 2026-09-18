# Retest.AI

A local Streamlit study app that creates source-grounded practice tests and adapts the next test to the learner's weak topics.

## Setup

1. Put your source PDF, DOCX, and/or PPTX files in `docs/`. The app discovers files by extension; filenames do not matter.
2. Get a free Groq API key (see [Creating a Groq API key](#creating-a-groq-api-key) below).
3. Create `.env` in this project directory with `GROQ_API_KEY=your_key_here` (or copy `.env.example`), replacing `your_key_here` with your key.
4. Create a virtual environment: `python -m venv .venv`
5. Activate the virtual environment (your terminal prompt should then start with `(.venv)`):
   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
   - Windows (Command Prompt): `.venv\Scripts\activate.bat`
   - macOS/Linux: `source .venv/bin/activate`
6. Install dependencies: `pip install -r requirements.txt`
7. Start the app: `python -m streamlit run app.py` (equivalent to `streamlit run app.py` when the Scripts directory is on your PATH).

### Creating a Groq API key

1. Go to the Groq API keys page: <https://console.groq.com/keys>.
2. Sign up or log in (Google, GitHub, or email). A free account is enough.
3. Click **Create API Key**.
4. Enter a name for the key (for example, `retest-ai`) and submit.
5. Copy the key right away. Groq shows it only once, so store it somewhere safe.
6. Paste it into your `.env` file as `GROQ_API_KEY=<your key>`. Never commit `.env` or share the key.

The free tier has rate limits for `openai/gpt-oss-20b` (about 8,000 tokens per minute and 200,000 tokens per day at the time of writing). The question count and token budgets in `config.py` are sized to stay within them.

Each completed attempt is saved as a separate YAML file in `feedback/`. The next test uses only the latest attempt to target weak topics. Fill-in-the-blank answers deliberately use case-insensitive, trimmed exact matching in v1, so equivalent phrasings may occasionally be marked wrong.

The application uses Groq's `openai/gpt-oss-20b` model. Its model name is configured in `config.py`.
