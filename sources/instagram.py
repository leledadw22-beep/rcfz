"""Instagram source via Apify (patient_discovery/instagram-search-reels by default).

Instagram's hashtag *feed* is photos, so we use a Reels-by-keyword actor (no login) that
searches reels the way the IG search bar does. Searches per Plane/Heli/Jet keyword group and
tags results by that group; an RC-signal relevance gate trims off-topic #fyp noise.
Uniform interface: fetch(cfg, secrets) -> list[normalized video dict].
"""
from datetime import datetime, timezone

from core import normalize
from sources.apify_base import run_actor, first, to_int

PLATFORM = "instagram"


def fetch(cfg, secrets):
    pcfg = cfg.get("platforms", {}).get(PLATFORM, {})
    token = secrets.get("apify_token")
    if not pcfg.get("enabled") or not token:
        return []

    actor = pcfg.get("actor", "patient_discovery/instagram-search-reels")
    limit = pcfg.get("max_items", 30)
    groups = pcfg.get("keywords", {})
    classify_cfg = cfg["classify"]
    heat_cfg = cfg["heat"]
    now = datetime.now(timezone.utc)

    videos = []
    seen = set()
    for rc_type, keywords in groups.items():
        for kw in keywords or []:
            items = run_actor(actor, {"search": kw, "maxItems": limit}, token)
            for it in items:
                code = first(it, ["code", "shortcode", "shortCode"], "")
                url = f"https://www.instagram.com/reel/{code}/" if code else first(it, ["video_url", "url"], "")
                if not url or url in seen:
                    continue
                caption = str(first(it, ["caption.text", "caption", "title"], "") or "")
                # Strict gate: the IG reel-search actor returns lots of generic #fyp/viral reels for
                # RC queries, so require an actual RC signal to keep the board clean.
                if not normalize.passes_relevance(caption.lower(), classify_cfg):
                    continue
                dur = to_int(first(it, ["video_duration", "videoDuration"], 0))  # any length allowed on IG
                seen.add(url)
                username = str(first(it, ["user.username", "caption.user.username", "ownerUsername"], ""))
                videos.append(normalize.make_video(
                    platform=PLATFORM,
                    video_id=str(code or first(it, ["id", "pk"], url)),
                    title=caption,
                    description="",
                    channel=username,
                    channel_id=username,
                    channel_url=f"https://www.instagram.com/{username}/" if username else "",
                    url=url,
                    thumbnail=str(first(it, ["thumbnail_url", "display_url", "displayUrl"], "")),
                    views=to_int(first(it, ["play_count", "ig_play_count", "videoViewCount", "view_count"], 0)),
                    likes=to_int(first(it, ["like_count", "likesCount", "likes"], 0)),
                    comments=to_int(first(it, ["comment_count", "commentsCount", "comments"], 0)),
                    duration_sec=dur,
                    published_at=first(it, ["taken_at", "taken_at_ts", "taken_at_date", "timestamp"], now.isoformat()),
                    rc_type=rc_type,
                    is_short=True,
                    now=now,
                    heat_cfg=heat_cfg,
                ))
    return videos
