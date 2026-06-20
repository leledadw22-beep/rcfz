"""RedNote / Xiaohongshu source via Apify (nexgendata/rednote-scraper by default).

RedNote is huge for Chinese RC makers/hobbyists, so config queries use Chinese RC terms
(航模 / 遥控飞机 / etc.) grouped by type, and results are tagged by group. This actor is
cookieless (handles auth via residential proxies) — no login needed. RedNote rarely exposes
view counts, so heat falls back to a likes-based proxy (handled in normalize.make_video).

Note: this actor is pay-per-result and relatively pricey (~$20 / 1,000 posts), so keep
`max_items` low in config to protect the free Apify credit.
Uniform interface: fetch(cfg, secrets) -> list[normalized video dict].
"""
from datetime import datetime, timezone

from core import normalize
from sources.apify_base import run_actor, first, to_int

PLATFORM = "rednote"


def _thumb(it):
    imgs = it.get("image_urls") or it.get("images") or it.get("imageList") or []
    if imgs:
        head = imgs[0]
        return head if isinstance(head, str) else head.get("url", "")
    return str(first(it, ["cover", "coverUrl", "noteCard.cover.url"], ""))


def fetch(cfg, secrets):
    pcfg = cfg.get("platforms", {}).get(PLATFORM, {})
    tokens = secrets.get("apify_tokens")
    if not pcfg.get("enabled") or not tokens:
        return []

    actor = pcfg.get("actor", "nexgendata/rednote-scraper")
    limit = pcfg.get("max_items", 15)
    groups = pcfg.get("queries", {})
    heat_cfg = cfg["heat"]
    classify_cfg = cfg["classify"]
    now = datetime.now(timezone.utc)

    videos = []
    seen = set()
    for rc_type, queries in groups.items():
        if not queries:
            continue
        items = run_actor(actor, {
            "mode": "keyword_search",
            "keywords": queries,
            "limit": limit,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "CN",
            },
        }, tokens)
        for it in items:
            url = first(it, ["url", "noteUrl", "shareLink", "link"], "")
            if not url or url in seen:
                continue
            title = str(first(it, ["title", "body", "desc", "content", "displayTitle"], ""))
            if normalize.has_excluded(title.lower(), classify_cfg):
                continue
            seen.add(url)
            videos.append(normalize.make_video(
                platform=PLATFORM,
                video_id=str(first(it, ["noteId", "id", "note_id"], url)),
                title=title,
                description="",
                channel=str(first(it, ["author", "nickname", "author_name", "author.nickname"], "")),
                channel_id=str(first(it, ["author_id", "userId", "author.userId"], "")),
                channel_url=str(first(it, ["author_url", "authorUrl"], "")),
                url=url,
                thumbnail=_thumb(it),
                views=to_int(first(it, ["views", "view_count", "viewCount", "read_count"], 0)),
                likes=to_int(first(it, ["likes_count", "likes", "likedCount", "like_count"], 0)),
                comments=to_int(first(it, ["comments_count", "comments", "commentCount"], 0)),
                duration_sec=0,
                published_at=first(it, ["posted_at", "publishTime", "timestamp", "time", "date"], now.isoformat()),
                rc_type=rc_type,
                is_short=True,
                now=now,
                heat_cfg=heat_cfg,
            ))
    return videos
