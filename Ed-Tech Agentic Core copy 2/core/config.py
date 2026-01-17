import os

# --- APP INFO ---
APP_NAME = "Ed-Tech Agentic Core"
VERSION = "1.0.0"

# --- UI CONSTANTS ---
PAGE_TITLE = "Ed-Tech Agentic Core"
PAGE_ICON = "🎓"
LAYOUT = "wide"

# --- MODEL DEFAULTS ---
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
ALLOWED_MODELS = [
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-5-20251101",
    "claude-3-haiku-20240307"
]

# --- RETRY LOGIC ---
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
BACKOFF_FACTOR = 2

# --- PATHS ---
# (Can be expanded if needed)
