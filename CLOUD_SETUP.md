# RC Flight Zone on your phone — fresh daily, automatic, no PC

This sets up a **free cloud robot** that runs your daily fetch and publishes the dashboard to a web
address. You install it on your phone once; after that it refreshes itself every morning — your PC
can stay off, and you can check it anywhere.

**You do this once (~10 minutes). Then never again.** I already built the automation (`.github/workflows/daily.yml`).

---

## 1. Make a free GitHub account
Go to **https://github.com** → **Sign up**. (Free.)

## 2. Create a repo and upload the project
- Click **+ (top right) → New repository** → name it `rcfz` → choose **Public** → **Create repository**.
- On the repo page: **Add file → Upload files** → drag in **everything from your `RCFZ App` folder EXCEPT the `.env` file**, then **Commit changes**.

> 🔒 **Never upload `.env`.** Your keys are NOT files — you paste them into the encrypted box in step 3.

## 3. Paste your keys into the encrypted vault
Repo → **Settings → Secrets and variables → Actions → New repository secret.** Add two:
| Name | Value |
|------|-------|
| `YOUTUBE_API_KEY` | your YouTube key |
| `APIFY_TOKEN` | your Apify token |

These are encrypted, never shown again, and never appear in the app.

## 4. Turn the website on
Repo → **Settings → Pages → Build and deployment → Source:** pick **GitHub Actions**.

## 5. Run it once (to go live now instead of waiting for tomorrow)
Repo → **Actions** tab → **RCFZ daily refresh + publish** → **Run workflow**.
Give it ~2 minutes. When it turns green, your site is live at:

**`https://YOUR-USERNAME.github.io/rcfz/`**

## 6. Install it on your phone
Open that link in **Chrome** on your phone → **⋮ → Install app / Add to Home screen**.
Tap the icon any time → **today's hottest RC clips.** It refreshes itself every morning. 🎉

---

### Tweaks
- **Change the refresh time:** edit `.github/workflows/daily.yml`, the `cron:` line (UTC). Default ≈ 7 AM US Eastern.
- **Refresh right now any day:** Actions tab → Run workflow.
- **It costs $0:** GitHub Actions + Pages are free; your YouTube quota is free; TikTok runs on Apify's free credit.
