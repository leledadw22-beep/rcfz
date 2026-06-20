"""View-trajectory tracking so we can flag clips ACCELERATING right now.

Each run records a small snapshot of every clip's views/likes into data/history.json, keyed by
platform:video_id. Next run we compare current views to the last snapshot to get the *recent*
velocity (views/day since we last looked) and compare it to the clip's lifetime average:

    momentum = recent_velocity / lifetime_velocity     (>1 = heating up, <1 = cooling)

A clip is "rising fast" when momentum clears a threshold and recent velocity is meaningful — i.e.
it's gaining faster than its own norm. Brand-new clips that are already hot get flagged on day 1
(before any history exists) so the board is never empty.
"""
import json
from pathlib import Path

from core.normalize import parse_dt


def load(path):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return {}


def save(path, data):
    p = Path(path)
    p.parent.mkdir(exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def annotate(videos, history, now, trend_cfg):
    """Annotate each video with recent velocity/momentum vs its last snapshot, then record the
    current snapshot. Mutates `videos` and `history` in place; returns `history`."""
    threshold = trend_cfg.get("momentum_threshold", 1.2)
    floor = trend_cfg.get("min_velocity_now", 1000)
    fresh_hours = trend_cfg.get("fresh_hours", 36)
    max_snaps = trend_cfg.get("max_snapshots", 8)

    for v in videos:
        key = f"{v['platform']}:{v['video_id']}"
        rec = history.get(key)
        v["is_new"] = rec is None

        if rec and rec.get("snaps"):
            prev = rec["snaps"][-1]
            dt_days = max((now - parse_dt(prev["t"])).total_seconds() / 86400.0, 0.04)
            delta = max(0, v["views"] - int(prev.get("views", 0)))
            vel_now = delta / dt_days
            vel_avg = v["views"] / max(v["age_days"], 0.5)
            v["velocity_now"] = round(vel_now, 1)
            v["delta_views"] = delta
            v["momentum"] = round(vel_now / vel_avg, 2) if vel_avg > 0 else 0
            v["rising_fast"] = v["momentum"] >= threshold and vel_now >= floor

        # Day-1 signal: brand-new and already hot -> treat as rising fast.
        if v["is_new"] and (v["age_days"] * 24) <= fresh_hours and v.get("rising"):
            v["rising_fast"] = True

        rec = history.setdefault(key, {"first_seen": now.isoformat(), "snaps": []})
        rec["snaps"].append({"t": now.isoformat(), "views": v["views"], "likes": v["likes"]})
        rec["snaps"] = rec["snaps"][-max_snaps:]
        rec["last_seen"] = now.isoformat()

    # Prune clips we haven't seen in a while to keep the file small.
    cutoff = now.timestamp() - trend_cfg.get("retention_days", 14) * 86400
    for key in [k for k, r in history.items()
                if parse_dt(r.get("last_seen") or r.get("first_seen")).timestamp() < cutoff]:
        del history[key]

    return history
