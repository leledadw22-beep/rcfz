#!/usr/bin/env python3
"""RC Flight Zone — trending fetch engine.

Runs every enabled source, ranks the combined result set by heat score, flags the
risers, and writes data/videos.js (what the dashboard reads) + data/videos.json.

Usage:
    python fetch_trending.py          # live fetch (needs YOUTUBE_API_KEY in .env)
    python fetch_trending.py --demo   # write realistic sample data, no API key needed
"""
import argparse
import json
import sys
import base64
from datetime import datetime, timezone
from pathlib import Path

from core import config_loader, normalize

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def write_outputs(videos, meta):
    DATA.mkdir(exist_ok=True)
    payload = {"meta": meta, "videos": videos}
    (DATA / "videos.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # videos.js assigns a global so the dashboard loads by plain double-click (no server / no CORS).
    (DATA / "videos.js").write_text(
        "window.RCFZ_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )


def _demo_thumb(rc_type):
    """Self-contained SVG placeholder (no network) so demo mode renders instantly/offline."""
    palette = {"plane": ("#1e3a8a", "#3b82f6"), "heli": ("#065f46", "#10b981"), "jet": ("#7c2d12", "#f97316")}
    c1, c2 = palette.get(rc_type, ("#334155", "#64748b"))
    label = {"plane": "PLANE", "heli": "HELI", "jet": "JET"}.get(rc_type, "RC")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>'
        '<rect width="640" height="360" fill="url(#g)"/>'
        f'<text x="320" y="195" font-family="Segoe UI,sans-serif" font-size="56" font-weight="bold" '
        f'fill="#fff" text-anchor="middle" opacity="0.9">RC {label}</text>'
        '<text x="320" y="245" font-family="Segoe UI,sans-serif" font-size="24" '
        'fill="#fff" text-anchor="middle" opacity="0.6">SAMPLE</text></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def build_demo_videos(cfg):
    """Hand-crafted sample rows so the dashboard looks alive before a real fetch."""
    now = datetime.now(timezone.utc)
    samples = [
        ("F-16 EDF jet screaming low pass 😱 #shorts", "Jet Power RC", "jet", 1850000, 142000, 3200, 34, 0.3),
        ("Goblin 700 flips inches off the deck", "Heli Freestyle", "heli", 1240000, 98000, 2100, 41, 0.6),
        ("80cc Extra 330 hovering on the prop #rc", "Giant Scale Flyers", "plane", 980000, 73000, 1500, 52, 1.4),
        ("Turbine jet 0-200mph in seconds", "Turbine Addicts", "jet", 760000, 61000, 1180, 38, 2.0),
        ("P-51 Mustang knife-edge + smoke", "Warbird Wings", "plane", 540000, 39000, 720, 29, 3.5),
        ("T-Rex 550 rainbow smoke 3D combo", "Align Pilot", "heli", 420000, 31000, 540, 57, 5.0),
        ("FPV flying wing dive-bombs the field", "Wing It RC", "plane", 360000, 27000, 610, 26, 6.5),
        ("Micro collective-pitch heli indoor wizardry", "Indoor Heli", "heli", 210000, 18000, 410, 22, 9.0),
        ("Mini EDF jet backyard ripper", "Foamie Fun", "jet", 158000, 12000, 300, 45, 12.0),
        ("Pitts biplane snap-roll spam", "Aerobatic Aces", "plane", 134000, 9800, 250, 31, 18.0),
        ("Scale Bell 222 maiden — buttery smooth", "Scale Heli Co", "heli", 96000, 7100, 180, 54, 23.0),
        ("Beginner RC plane faceplant 💀", "Learn To Fly RC", "plane", 72000, 6400, 520, 18, 27.0),
    ]
    videos = []
    platforms = ["youtube", "tiktok", "instagram", "rednote"]
    for idx, (title, channel, rc_type, views, likes, comments, dur, days_ago) in enumerate(samples, 1):
        published = now.timestamp() - days_ago * 86400
        published_iso = datetime.fromtimestamp(published, tz=timezone.utc).isoformat()
        platform = platforms[(idx - 1) % len(platforms)]
        search = title.replace(" ", "+")
        demo_urls = {
            "youtube": f"https://www.youtube.com/results?search_query={search}",
            "tiktok": f"https://www.tiktok.com/search?q={search}",
            "instagram": "https://www.instagram.com/explore/tags/rcplane/",
            "rednote": f"https://www.xiaohongshu.com/search_result?keyword={search}",
        }
        videos.append(normalize.make_video(
            platform=platform,
            video_id=f"demo{idx:02d}",
            title=title,
            description=f"{title}. radio control rc {rc_type}.",
            channel=channel,
            channel_id=f"DEMOCHANNEL{idx:02d}",
            channel_url="",
            url=demo_urls[platform],
            thumbnail=_demo_thumb(rc_type),
            views=(0 if platform == "rednote" else views),
            likes=likes,
            comments=comments,
            duration_sec=dur,
            published_at=published_iso,
            rc_type=rc_type,
            is_short=True,
            now=now,
            heat_cfg=cfg["heat"],
        ))
    return videos


def annotate_demo_trends(videos):
    """Fabricate a few acceleration signals so demo mode showcases the Rising-Fast feature."""
    for i, v in enumerate(videos):
        if i % 4 == 0:
            v["momentum"] = round(1.8 + (i % 3) * 0.6, 2)
            v["velocity_now"] = int((v["views"] / max(v["age_days"], 0.5)) * v["momentum"])
            v["delta_views"] = int(v["views"] * 0.18)
            v["rising_fast"] = True
            v["is_new"] = (i == 0)


def main():
    parser = argparse.ArgumentParser(description="Fetch trending RC plane/heli/jet videos.")
    parser.add_argument("--demo", action="store_true",
                        help="write realistic sample data without calling any API")
    args = parser.parse_args()

    cfg = config_loader.load_config()
    now = datetime.now(timezone.utc)
    sources_used = []

    if args.demo:
        videos = build_demo_videos(cfg)
        sources_used = ["demo"]
    else:
        secrets = config_loader.load_secrets()
        videos = []
        sources_used = []

        # YouTube — official, free.
        if secrets["youtube_api_key"]:
            from sources import youtube
            try:
                print("Fetching from YouTube...")
                yt = youtube.fetch(cfg, secrets)
                videos += yt
                sources_used.append("youtube")
                print(f"  YouTube: {len(yt)} shorts")
            except youtube.YouTubeAPIError as exc:
                print(f"  YouTube skipped: {exc}")
        else:
            print("  YouTube skipped: no YOUTUBE_API_KEY in .env")

        # TikTok / Instagram / RedNote — via Apify (needs APIFY_TOKEN).
        if secrets["apify_token"]:
            from sources import tiktok, instagram, rednote
            from sources.apify_base import ApifyError
            for mod in (tiktok, instagram, rednote):
                if not cfg.get("platforms", {}).get(mod.PLATFORM, {}).get("enabled"):
                    continue
                try:
                    print(f"Fetching from {mod.PLATFORM}...")
                    res = mod.fetch(cfg, secrets)
                    videos += res
                    sources_used.append(mod.PLATFORM)
                    print(f"  {mod.PLATFORM}: {len(res)} videos")
                except ApifyError as exc:
                    print(f"  {mod.PLATFORM} skipped: {exc}")
                except Exception as exc:  # one bad actor shouldn't kill the whole run
                    print(f"  {mod.PLATFORM} error: {exc}")
        else:
            print("  TikTok/Instagram/RedNote skipped: no APIFY_TOKEN in .env (free token at apify.com)")

        if not videos:
            print("ERROR: nothing fetched. Add YOUTUBE_API_KEY and/or APIFY_TOKEN to .env, or run with --demo.")
            sys.exit(1)

    # Dedupe across sources, flag risers, rank by heat, cap.
    seen = set()
    unique = []
    for v in videos:
        key = (v["platform"], v["video_id"])
        if key not in seen:
            seen.add(key)
            unique.append(v)
    normalize.mark_rising(unique, cfg["heat"])
    if args.demo:
        annotate_demo_trends(unique)
    else:
        from core import history
        hist_path = DATA / "history.json"
        hist = history.load(hist_path)
        history.annotate(unique, hist, now, cfg.get("trend", {}))
        history.save(hist_path, hist)
    unique.sort(key=lambda v: v["heat_score"], reverse=True)
    unique = unique[: cfg["search"].get("results_cap", 150)]

    by_type = {"plane": 0, "heli": 0, "jet": 0}
    by_platform = {}
    for v in unique:
        by_type[v["rc_type"]] = by_type.get(v["rc_type"], 0) + 1
        by_platform[v["platform"]] = by_platform.get(v["platform"], 0) + 1

    meta = {
        "fetched_at": now.isoformat(),
        "count": len(unique),
        "by_type": by_type,
        "by_platform": by_platform,
        "sources": sources_used,
        "sample": args.demo,
    }
    write_outputs(unique, meta)

    print(f"Fetched {len(unique)} videos "
          f"(plane {by_type['plane']}, heli {by_type['heli']}, jet {by_type['jet']}).")
    print(f"Wrote {DATA / 'videos.js'} and {DATA / 'videos.json'}.")
    if args.demo:
        print("This is SAMPLE data - add your API key and run without --demo for live results.")


if __name__ == "__main__":
    main()
