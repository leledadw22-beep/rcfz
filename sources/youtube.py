"""YouTube Data API v3 source — focused on SHORTS (short-form vertical clips).

Pattern that stays far inside the free 10,000-units/day quota:
  1. search.list per keyword with videoDuration=short (100 units each) -> candidate IDs
  2. videos.list in batches of 50 (1 unit each) -> exact stats + duration
  3. keep only Shorts: duration <= shorts_max_seconds, optionally confirmed by the
     youtube.com/shorts/<id> redirect test (a real Short returns 200; long-form 30x-redirects
     to /watch). These checks are plain HTTP (no API quota) and run concurrently.

Exposes the uniform interface: fetch(cfg, secrets) -> list[normalized video dict].
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from core import normalize

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
SHORTS_URL = "https://www.youtube.com/shorts/{}"
TIMEOUT = 30
UA = {"User-Agent": "Mozilla/5.0 (compatible; RCFZ/1.0)"}


class YouTubeAPIError(Exception):
    """Raised with a human-friendly message when the API rejects a request."""


def _get(url, params):
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    if resp.status_code == 200:
        return resp.json()
    try:
        reason = resp.json()["error"]["errors"][0].get("reason", "")
        message = resp.json()["error"].get("message", "")
    except Exception:
        reason, message = "", resp.text[:200]
    if resp.status_code == 400 or reason in ("keyInvalid", "badRequest"):
        raise YouTubeAPIError(
            "YouTube rejected the API key. Check YOUTUBE_API_KEY in your .env file "
            f"and that 'YouTube Data API v3' is enabled in Google Cloud.\n  ({message})"
        )
    if reason in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
        raise YouTubeAPIError(
            "YouTube daily quota reached. It resets at midnight Pacific time — "
            f"try again tomorrow, or trim the keyword list in config.json.\n  ({message})"
        )
    raise YouTubeAPIError(f"YouTube API error {resp.status_code}: {message or reason}")


def _published_after(days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _best_thumbnail(thumbnails):
    for size in ("maxres", "standard", "high", "medium", "default"):
        if size in thumbnails:
            return thumbnails[size]["url"]
    return ""


def _search_ids(keyword, search_cfg, api_key):
    params = {
        "key": api_key,
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "order": "viewCount",
        "videoDuration": "short",  # < 4 min — biases the results toward Shorts
        "publishedAfter": _published_after(search_cfg["published_within_days"]),
        "maxResults": min(search_cfg.get("max_results_per_keyword", 50), 50),
        "relevanceLanguage": search_cfg.get("relevance_language", "en"),
        "regionCode": search_cfg.get("region_code", "US"),
        "safeSearch": "none",
    }
    data = _get(SEARCH_URL, params)
    return [
        item["id"]["videoId"]
        for item in data.get("items", [])
        if item.get("id", {}).get("videoId")
    ]


def _hydrate(video_ids, api_key):
    out = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        params = {
            "key": api_key,
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch),
            "maxResults": 50,
        }
        out.extend(_get(VIDEOS_URL, params).get("items", []))
    return out


def _verify_short_url(video_id, duration_sec, session):
    """A real Short returns HTTP 200 on /shorts/<id>; long-form redirects (30x) to /watch."""
    try:
        r = session.head(SHORTS_URL.format(video_id), allow_redirects=False, timeout=8, headers=UA)
        if r.status_code == 200:
            return True
        if 300 <= r.status_code < 400:
            return False
        return duration_sec <= 60  # ambiguous response -> fall back to the tight duration rule
    except requests.RequestException:
        return duration_sec <= 60  # network hiccup -> don't drop a likely Short


def fetch(cfg, secrets):
    api_key = secrets.get("youtube_api_key")
    if not api_key:
        raise YouTubeAPIError("No YouTube API key provided.")

    search_cfg = cfg["search"]
    classify_cfg = cfg["classify"]
    heat_cfg = cfg["heat"]
    blocklist = {c.lower() for c in cfg.get("channel_blocklist", [])}
    min_views = search_cfg.get("min_views", 0)
    shorts_max = search_cfg.get("shorts_max_seconds", 180)
    verify = search_cfg.get("verify_shorts", True)
    now = datetime.now(timezone.utc)

    # 1) Candidate IDs across every keyword (Shorts-biased search).
    all_keywords = []
    for group in search_cfg["keywords"].values():
        all_keywords.extend(group)
    ids, seen_ids = [], set()
    for kw in all_keywords:
        for vid in _search_ids(kw, search_cfg, api_key):
            if vid not in seen_ids:
                seen_ids.add(vid)
                ids.append(vid)

    # 2) Hydrate, then apply the strict RC gate + Shorts-length pre-filter.
    candidates = []
    for item in _hydrate(ids, api_key):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        details = item.get("contentDetails", {})

        text = " ".join([
            snippet.get("title", ""),
            snippet.get("description", ""),
            " ".join(snippet.get("tags", [])),
        ]).lower()

        if not normalize.passes_relevance(text, classify_cfg):
            continue
        rc_type = normalize.classify_rc_type(text, classify_cfg)
        if rc_type is None:
            continue

        channel = snippet.get("channelTitle", "")
        if channel.lower() in blocklist:
            continue

        views = int(stats.get("viewCount", 0))
        if views < min_views:
            continue

        duration_sec = normalize.parse_iso_duration(details.get("duration", ""))
        if duration_sec <= 0 or duration_sec > shorts_max:  # long-form -> skip; we want Shorts
            continue

        channel_id = snippet.get("channelId", "")
        candidates.append({
            "video_id": item["id"],
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel": channel,
            "channel_id": channel_id,
            "channel_url": f"https://www.youtube.com/channel/{channel_id}" if channel_id else "",
            "url": SHORTS_URL.format(item["id"]),
            "thumbnail": _best_thumbnail(snippet.get("thumbnails", {})),
            "views": views,
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "duration_sec": duration_sec,
            "published_at": snippet.get("publishedAt", now.isoformat()),
            "rc_type": rc_type,
        })

    # 3) Confirm true Shorts via the /shorts/ redirect test (concurrent, no API quota).
    if verify and candidates:
        with requests.Session() as session, ThreadPoolExecutor(max_workers=10) as pool:
            keep = list(pool.map(
                lambda c: _verify_short_url(c["video_id"], c["duration_sec"], session),
                candidates,
            ))
        candidates = [c for c, ok in zip(candidates, keep) if ok]

    return [normalize.make_video(
        platform="youtube",
        video_id=c["video_id"],
        title=c["title"],
        description=c["description"],
        channel=c["channel"],
        channel_id=c["channel_id"],
        channel_url=c["channel_url"],
        url=c["url"],
        thumbnail=c["thumbnail"],
        views=c["views"],
        likes=c["likes"],
        comments=c["comments"],
        duration_sec=c["duration_sec"],
        published_at=c["published_at"],
        rc_type=c["rc_type"],
        is_short=True,
        now=now,
        heat_cfg=heat_cfg,
    ) for c in candidates]
