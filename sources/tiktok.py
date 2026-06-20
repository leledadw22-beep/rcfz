"""TikTok source via Apify (clockworks/tiktok-scraper by default).

Searches per Plane/Heli/Jet keyword group and tags results by the group that found them.
Uniform interface: fetch(cfg, secrets) -> list[normalized video dict].
"""
from datetime import datetime, timezone

from core import normalize
from sources.apify_base import run_actor, dig, first, to_int

PLATFORM = "tiktok"


def fetch(cfg, secrets):
    pcfg = cfg.get("platforms", {}).get(PLATFORM, {})
    tokens = secrets.get("apify_tokens")
    if not pcfg.get("enabled") or not tokens:
        return []

    actor = pcfg.get("actor", "clockworks/tiktok-scraper")
    per_page = pcfg.get("max_items", 50)
    groups = pcfg.get("keywords", {})
    classify_cfg = cfg["classify"]
    heat_cfg = cfg["heat"]
    now = datetime.now(timezone.utc)

    videos = []
    for rc_type, keywords in groups.items():
        if not keywords:
            continue
        items = run_actor(actor, {
            "searchQueries": keywords,
            "resultsPerPage": per_page,
            "searchSection": "/video",
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }, tokens)
        for it in items:
            url = first(it, ["webVideoUrl", "postPage", "url"])
            if not url:
                continue
            text = str(first(it, ["text", "title", "desc"], "")).lower()
            if not normalize.passes_relevance(text, classify_cfg):
                continue
            dur = to_int(dig(it, "videoMeta.duration", 0))  # any length allowed on TikTok
            username = str(first(it, ["authorMeta.name", "authorMeta.uniqueId", "author.uniqueId"], ""))
            videos.append(normalize.make_video(
                platform=PLATFORM,
                video_id=str(first(it, ["id", "video.id", "awemeId"], url)),
                title=str(first(it, ["text", "title", "desc"], "")),
                description="",
                channel=username,
                channel_id=username,
                channel_url=f"https://www.tiktok.com/@{username}" if username else "",
                url=url,
                thumbnail=str(first(it, ["videoMeta.coverUrl", "videoMeta.originalCoverUrl", "covers.default"], "")),
                views=to_int(first(it, ["playCount", "stats.playCount", "views"], 0)),
                likes=to_int(first(it, ["diggCount", "stats.diggCount", "likes"], 0)),
                comments=to_int(first(it, ["commentCount", "stats.commentCount", "comments"], 0)),
                duration_sec=dur,
                published_at=first(it, ["createTimeISO", "createTime", "uploadedAtFormatted"], now.isoformat()),
                rc_type=rc_type,
                is_short=True,
                now=now,
                heat_cfg=heat_cfg,
            ))
    return videos
