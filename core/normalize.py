"""Common Video schema, heat-score math, and the strict RC plane/heli/jet classifier.

Every source maps its platform-specific fields into make_video(), so the dashboard
only ever sees one shape regardless of where a video came from.
"""
import math
import re
from datetime import datetime, timezone

_DURATION_RE = re.compile(
    r"P(?:(?P<days>\d+)D)?T?(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?"
)


def parse_iso_duration(iso):
    """ISO-8601 duration (e.g. 'PT4M13S') -> seconds. Returns 0 on anything unparseable."""
    if not iso:
        return 0
    match = _DURATION_RE.fullmatch(iso)
    if not match:
        return 0
    parts = match.groupdict()
    days = int(parts["days"] or 0)
    hours = int(parts["h"] or 0)
    minutes = int(parts["m"] or 0)
    seconds = int(parts["s"] or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def parse_dt(value):
    """Parse a timestamp into an aware UTC datetime.

    Handles ISO 8601 (incl. trailing 'Z'), epoch seconds, and epoch milliseconds
    (different platforms return different formats). Falls back to 'now' if unparseable.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value is None or value == "":
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def days_since(published, now):
    """Fractional days between a published timestamp and now."""
    return max((now - parse_dt(published)).total_seconds() / 86400.0, 0.0)


def compute_heat(views, likes, comments, age_days, heat_cfg):
    """Velocity-based heat score: roughly views-per-day, nudged by engagement rate.

    A clip with 80k views in 3 days outranks one with 500k views over 2 years, which is
    exactly what we want for spotting content *while it is climbing*.
    """
    age = max(age_days, 0.5)  # avoid divide-by-zero on brand-new uploads
    base = views / age
    engagement = (likes + heat_cfg.get("comment_weight", 5) * comments) / max(views, 1)
    boost = 1 + min(engagement, heat_cfg.get("engagement_boost_cap", 0.5))
    return base * boost


def classify_rc_type(text, classify_cfg):
    """Return 'heli' | 'jet' | 'plane' | None. Most-specific category wins (heli, then jet)."""
    for key in ("heli", "jet", "plane"):
        for kw in classify_cfg.get(key, []):
            if kw in text:
                return key
    return None


def has_excluded(text, classify_cfg):
    """True if text contains any excluded term (cars/boats/drones/etc.). Used by all sources."""
    return any(bad in text for bad in classify_cfg.get("exclude", []))


def passes_relevance(text, classify_cfg):
    """Strict gate: drop excluded categories (cars/boats/drones/etc.) and require an RC signal."""
    if has_excluded(text, classify_cfg):
        return False
    if not classify_cfg.get("require_rc_signal", True):
        return True
    signals = classify_cfg.get("rc_signals", []) + classify_cfg.get("strong_terms", [])
    return any(sig in text for sig in signals)


def make_video(*, platform, video_id, title, description, channel, channel_id,
               channel_url, url, thumbnail, views, likes, comments, duration_sec,
               published_at, rc_type, now, heat_cfg, is_short=None):
    """Assemble one normalized video record. `rising` is filled in later across the full set."""
    age = days_since(published_at, now)
    # Some platforms (e.g. RedNote) don't expose view counts — fall back to a likes-based
    # reach proxy so they still rank sensibly against view-rich platforms.
    reach = views if views > 0 else int(likes * heat_cfg.get("like_view_proxy", 18))
    heat = compute_heat(reach, likes, comments, age, heat_cfg)
    return {
        "platform": platform,
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "channel_id": channel_id,
        "channel_url": channel_url,
        "url": url,
        "thumbnail": thumbnail,
        "views": int(views),
        "likes": int(likes),
        "comments": int(comments),
        "duration_sec": int(duration_sec),
        "is_short": (duration_sec > 0 and duration_sec <= 60) if is_short is None else bool(is_short),
        "published_at": parse_dt(published_at).isoformat(),
        "age_days": round(age, 2),
        "rc_type": rc_type,
        "heat_score": round(heat, 1),
        "rising": False,
        "velocity_now": None,
        "momentum": None,
        "delta_views": 0,
        "rising_fast": False,
        "is_new": False,
    }


def percentile(sorted_vals, pct):
    """Linear-interpolated percentile of an already-sorted list."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (len(sorted_vals) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_vals[int(rank)]
    return sorted_vals[low] * (high - rank) + sorted_vals[high] * (rank - low)


def mark_rising(videos, heat_cfg):
    """Flag videos whose heat sits at/above the configured percentile of the batch."""
    if len(videos) < 4:
        return videos
    heats = sorted(v["heat_score"] for v in videos)
    threshold = percentile(heats, heat_cfg.get("rising_percentile", 75))
    for v in videos:
        v["rising"] = v["heat_score"] >= threshold
    return videos
