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
    """Load API keys from .env (falling back to real environment variables).

    Apify supports a failover list: set APIFY_TOKEN, then optionally APIFY_TOKEN_2..._5
    (and/or a comma-separated APIFY_TOKENS). When one runs out of free credit, the next is used.
    """
    if load_dotenv:
        load_dotenv(ROOT / ".env")

    raw = []
    for name in ("APIFY_TOKEN", "APIFY_TOKEN_2", "APIFY_TOKEN_3", "APIFY_TOKEN_4", "APIFY_TOKEN_5"):
        raw.append(os.environ.get(name, ""))
    raw.extend(os.environ.get("APIFY_TOKENS", "").split(","))

    apify_tokens, seen = [], set()
    for token in (t.strip() for t in raw):
        if token and token not in seen:
            seen.add(token)
            apify_tokens.append(token)

    return {
        "youtube_api_key": os.environ.get("YOUTUBE_API_KEY", "").strip(),
        "apify_tokens": apify_tokens,
        "apify_token": apify_tokens[0] if apify_tokens else "",
        "rednote_cookie": os.environ.get("REDNOTE_COOKIE", "").strip(),
    }
