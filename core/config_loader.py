"""Loads config.json and secrets from .env. No third-party config logic lives elsewhere."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv not installed yet
    load_dotenv = None


def load_config():
    """Read config.json from the project root."""
    path = ROOT / "config.json"
    if not path.exists():
        raise FileNotFoundError(
            f"config.json not found at {path}. It ships with the project — restore it."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_secrets():
    """Load API keys from .env (falling back to real environment variables)."""
    if load_dotenv:
        load_dotenv(ROOT / ".env")
    return {
        "youtube_api_key": os.environ.get("YOUTUBE_API_KEY", "").strip(),
        "apify_token": os.environ.get("APIFY_TOKEN", "").strip(),
        "rednote_cookie": os.environ.get("REDNOTE_COOKIE", "").strip(),
    }
