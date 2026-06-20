# RC Flight Zone — "What's Hot Today" Dashboard

A daily board of the hottest **RC plane, helicopter, and jet** videos on YouTube, ranked by
how *fast* they're gaining views (not just raw view count) so you can spot rising content early
and pick repost candidates in minutes.

> **V1 = YouTube only**, runs on your PC, free. Built to grow into TikTok/Instagram/Facebook
> (Phase 2) and a cloud-hosted, phone-accessible content tracker (Phase 3).

---

## ⚡ See it right now (no setup, sample data)

```
python fetch_trending.py --demo
```

Then open `index.html` in your browser (or run `refresh.bat`). You'll see the dashboard filled with sample
videos and a yellow "sample data" banner. This needs **no API key and no installs**.

---

## 🚀 Go live (real trending videos) — one-time setup

### 1. Get a free YouTube API key (~5 minutes)
1. Go to <https://console.cloud.google.com> and sign in.
2. Create a project (top bar → **New Project** → name it `RCFZ`).
3. **APIs & Services → Library** → search **"YouTube Data API v3"** → **Enable**.
4. **APIs & Services → Credentials → Create Credentials → API key**. Copy the key.

### 2. Add the key
- Copy `.env.example` to a new file named `.env`.
- Replace `your_key_here` with your key.

### 3. Install the two dependencies
```
pip install -r requirements.txt
```

### 4. Run it
```
python fetch_trending.py
```
…or just **double-click `refresh.bat`** — it fetches *and* opens the dashboard for you.

The free quota (10,000 units/day) is far more than this uses (~1,300/day), so daily refreshes cost nothing.

---

## 🌐 Add TikTok, Instagram & RedNote (optional, cheap)

These three have no free official discovery API, so we use **Apify** — pay-per-result and
cheap (TikTok ~$0.30 / 1,000, Instagram ~$0.50 / 1,000). Apify's **free plan gives $5 of
credit every month with no credit card**, which covers light use (refresh a few times a week
and you'll likely pay nothing).

1. Make a free account at <https://apify.com>.
2. **Settings → Integrations → API tokens** → copy your token.
3. Add it to `.env`: `APIFY_TOKEN=...`
4. Run `python fetch_trending.py` (or `refresh.bat`) — TikTok, Instagram, and RedNote now flow
   into the same board, with a platform filter and a per-card platform badge.

Tune or disable each platform under `"platforms"` in `config.json` (RedNote uses Chinese RC
terms like 航模 / 遥控飞机 since that's where its RC content lives). Keep `max_items` modest to
stay inside the free $5.

> This is web scraping, which is against those platforms' terms of service (YouTube stays fully
> official). You're only *discovering* content — you still get the creator's permission before reposting.

---

## 🔁 Make it refresh automatically every morning

Run this once in a Command Prompt (adjust the path if you moved the folder). It creates a
Windows scheduled task that refreshes the data every day at 7:00 AM:

```
schtasks /create /tn "RCFZ Trending Refresh" /sc daily /st 07:00 ^
  /tr "python \"%USERPROFILE%\OneDrive - Convergint\Desktop\RCFZ App\fetch_trending.py\""
```

> If `python` isn't found by the task, replace it with the full path to your python.exe
> (find it by running `where python`).

Then each morning just open the dashboard (or `refresh.bat`) and today's videos are already there.

---

## 🔥 How the "heat score" works

Videos are ranked by **velocity**, not raw views:

```
heat = (views ÷ days_since_posted) × small engagement boost
```

So an 80K-views-in-3-days clip beats a 500K-views-over-2-years clip. The number on each card
("🔥 18K/day") is roughly how many views it pulls per day. Videos in the top 25% of the batch
get a **📈 RISING** flag. All the weights live in `config.json`.

---

## ⚙️ Customizing (no coding)

Everything tunable lives in **`config.json`**:
- `search.keywords` — what to search, grouped by `plane` / `heli` / `jet`.
- `search.published_within_days` — how recent (default 14).
- `search.min_views` — ignore videos below this.
- `classify.exclude` — terms that get a video dropped (RC cars, boats, drones, etc.).
- `classify.plane/heli/jet` — words that tag a video as each type.
- `channel_blocklist` — channels to never show (e.g., your own).
- `platforms.tiktok / instagram / rednote` — turn each on/off, set search terms, and `max_items` (keep modest to stay inside Apify's free $5/month).

Edit, save, re-run. No code changes needed.

---

## 📁 What's in here

```
fetch_trending.py     The engine — run this (or refresh.bat) to update the board
config.json           Your keywords, platforms & settings (edit freely)
.env                  Secret keys: YOUTUBE_API_KEY + APIFY_TOKEN (you create this)
sources/youtube.py    YouTube Shorts (official API, free)
sources/tiktok.py     TikTok    (via Apify)
sources/instagram.py  Instagram (via Apify)
sources/rednote.py    RedNote / Xiaohongshu (via Apify)
sources/apify_base.py Shared Apify runner
core/                 Shared video format, heat-score math, plane/heli/jet classifier
index.html            The dashboard (open this)
data/                 Auto-generated results the dashboard reads
refresh.bat           One-click: fetch + open dashboard
```

---

## 🗺️ Roadmap

- **Phase 2 — Multi-platform — DONE:** TikTok, Instagram, and RedNote are wired in via Apify
  (add your `APIFY_TOKEN` to switch them on). Facebook can be added later the same way if wanted.
- **Phase 3 — Cloud:** host it online for phone access, track heat over time, and add a repost
  pipeline (Discovered → Shortlisted → Permission Asked → Edited → Posted).

YouTube discovery uses the official API and is fully within YouTube's terms. The Apify-based
platforms rely on third-party scraping, which is against those platforms' terms of service —
you're only discovering content, and you still get the creator's permission before reposting.
