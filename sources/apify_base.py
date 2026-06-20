"""Shared helpers for Apify-backed sources (TikTok, Instagram, RedNote).

One synchronous call per actor run via the run-sync-get-dataset-items endpoint, which
returns the dataset items directly. Pay-per-result actors keep this cheap on the free tier.
"""
import requests

API_BASE = "https://api.apify.com/v2/acts"
TIMEOUT = 310  # the endpoint itself caps a run at 300s (408 after that)


class ApifyError(Exception):
    """Raised with a human-friendly message when an Apify run fails."""


def run_actor(actor_id, run_input, token, timeout=TIMEOUT):
    """Run an actor synchronously and return its dataset items (a list of dicts)."""
    slug = actor_id.replace("/", "~")  # API wants the tilde form: user~actor-name
    url = f"{API_BASE}/{slug}/run-sync-get-dataset-items"
    try:
        resp = requests.post(url, params={"token": token}, json=run_input, timeout=timeout)
    except requests.RequestException as exc:
        raise ApifyError(f"network error calling {actor_id}: {exc}")

    if resp.status_code in (200, 201):
        try:
            data = resp.json()
            return data if isinstance(data, list) else []
        except ValueError:
            return []
    if resp.status_code == 401:
        raise ApifyError("token rejected (401) — check APIFY_TOKEN in .env")
    if resp.status_code in (402, 403):
        raise ApifyError("payment/credit required (402/403) — the free $5 may be used up this month")
    if resp.status_code == 404:
        raise ApifyError(f"actor not found (404): {actor_id} — check the 'actor' id in config.json")
    if resp.status_code == 408:
        raise ApifyError(f"run timed out (408) for {actor_id} — lower max_items in config.json")
    raise ApifyError(f"error {resp.status_code} for {actor_id}: {resp.text[:160]}")


def dig(obj, path, default=None):
    """Safe nested lookup by dotted path, e.g. dig(item, 'video.duration')."""
    cur = obj
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def first(obj, paths, default=None):
    """Return the first non-empty value among several candidate dotted paths.

    Lets each source tolerate field-name differences between actors without breaking.
    """
    for path in paths:
        value = dig(obj, path)
        if value not in (None, "", [], {}):
            return value
    return default


def to_int(value, default=0):
    """Coerce a possibly-string/float metric into an int (handles '1.2K'-free numerics)."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
