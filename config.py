"""Central application configuration."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_ROOT / "docs"
CACHE_DIR = DOCS_DIR / ".cache"
CACHE_FILE = CACHE_DIR / "combined_text.txt"
CACHE_MANIFEST = CACHE_DIR / "manifest.json"
FEEDBACK_DIR = PROJECT_ROOT / "feedback"

# Gemini provider configuration is intentionally disabled. Retained here only
# as a migration reference:
# MODEL_NAME = "gemini-3-flash-preview"
# FALLBACK_MODEL_NAME = "gemini-3.6-flash"

GROQ_MODEL_NAME = "openai/gpt-oss-20b"

# openai/gpt-oss-20b on Groq's free tier caps each request (prompt + completion
# tokens combined) at 8,000 TPM. The source document alone runs ~5,000 tokens,
# so QUESTION_COUNT and the *_MAX_OUTPUT_TOKENS budgets below are sized to leave
# headroom under that ceiling rather than to fit the schema alone.
QUESTION_COUNT = 12
QUESTION_MAX_OUTPUT_TOKENS = 2500
FEEDBACK_MAX_OUTPUT_TOKENS = 1200
