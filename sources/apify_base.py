"""Shared helpers for Apify-backed sources (TikTok, Instagram, RedNote).

One synchronous call per actor run via the run-sync-get-dataset-items endpoint, which
returns the dataset items directly. Pay-per-result actors keep this cheap on the free tier.
"""
import time

import requests

API_BASE = "https://api.apify.com/v2/acts"
TIMEOUT = 310  # the endpoint itself caps a run at 300s (408 after that)


class ApifyError(Exception):
    """Raised with a human-friendly message when an Apify run fails."""


def run_actor(actor_id, run_input, tokens, timeout=TIMEOUT, retries=2):
    """Run an actor synchronously and return its dataset items (a list of dicts).

    `tokens` may be a single token or a list. On 402/403 (free credit used up) or a bad token,
    we fail over to the next token. Transient 5xx/timeout/network errors are retried on the same
    token first, then we move on. Raises ApifyError only when every token is exhausted/failing.
    """
    if isinstance(tokens, str):
        tokens = [tokens]
    tokens = [t for t in (tokens or []) if t]
    if not tokens:
        raise ApifyError("no Apify token provided")

    slug = actor_id.replace("/", "~")  # API wants the tilde form: user~actor-name
    url = f"{API_BASE}/{slug}/run-sync-get-dataset-items"
    exhausted = 0
    last_err = ""

    for token in tokens:
        for attempt in range(retries + 1):
            try:
                resp = requests.post(url, params={"token": token}, json=run_input, timeout=timeout)
            except requests.RequestException as exc:
                last_err = f"network error: {exc}"
                if attempt < retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                break  # give up on this token, try the next
            if resp.status_code in (200, 201):
                try:
                    data = resp.json()
                    return data if isinstance(data, list) else []
                except ValueError:
                    return []
            if resp.status_code == 404:
                raise ApifyError(f"actor not found (404): {actor_id} — check the 'actor' id in config.json")
            if resp.status_code in (402, 403):
                exhausted += 1
                last_err = "free credit used up (402/403)"
                break  # this token is tapped out — fail over to the next
            if resp.status_code == 401:
                last_err = "token rejected (401)"
                break  # bad token — try the next
            if resp.status_code == 408 or resp.status_code >= 500:
                last_err = f"transient error {resp.status_code}"
                if attempt < retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                break  # transient kept failing — try the next token
            raise ApifyError(f"error {resp.status_code} for {actor_id}: {resp.text[:160]}")

    if exhausted >= len(tokens):
        raise ApifyError(f"all {len(tokens)} Apify token(s) out of free credit (402) — add another or wait for reset")
    raise ApifyError(f"{actor_id} failed across {len(tokens)} token(s): {last_err}")


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
