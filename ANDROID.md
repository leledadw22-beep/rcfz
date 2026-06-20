# Put RC Flight Zone on your Android phone

Your dashboard is now an installable **PWA** (web app). The phone needs to reach it at a web
address, so **hosting is step 1 for any option**. Then either install it in 30 seconds (Option A)
or build a real **APK** (Option B).

> ⚠️ **Only ever upload the `dist` folder.** Run `build_web.bat` to (re)build it — it contains just
> the safe files (dashboard + data + icons). **Never upload the main project folder** — it holds
> your `.env` API keys.

---

## Step 1 — Host it free (required)

Easiest is **Netlify Drop** (no account needed to try):
1. Double-click **`build_web.bat`** → it creates/updates the **`dist`** folder.
2. Go to **https://app.netlify.com/drop**
3. Drag the **`dist`** folder onto the page.
4. You get a free HTTPS link like `https://rcfz-xxxx.netlify.app` — **that's your app URL.**

(Cloudflare Pages, GitHub Pages, and Vercel work too — any static host.)

---

## Option A — Install as an app (30 seconds, no APK)

On your phone, open that link in **Chrome** → tap **⋮** menu → **Install app / Add to Home screen.**
You get a fullscreen app icon that works offline and looks/feels native. Fastest path.

## Option B — Build a real APK (what you asked for)

1. Go to **https://www.pwabuilder.com**
2. Paste your hosted URL → **Start**. It scores the app (manifest + service worker are already set, so it should pass).
3. **Package For Stores → Android.**
4. Pick **"Signed test package"** for sideloading → **Download.** You get an **`.apk`** (and an `.aab`
   for the Play Store) plus a signing key — **keep that key file safe.**
5. Move the `.apk` to your phone (Drive/email/USB), tap it, allow **"install from unknown sources,"** install.
   - To put it on the **Google Play Store** instead: upload the `.aab` (one-time $25 Google developer account).

---

## Keeping the app fresh

The app shows whatever data is hosted. After each `refresh.bat`:
1. Run **`build_web.bat`** (copies the new data into `dist`).
2. Re-deploy `dist` (drag to Netlify Drop again, or `git push` for Pages).

**Want it fully hands-free?** Ask me to set up the **cloud auto-fetch** (GitHub Actions): it runs the
daily pull *and* updates the hosted app itself — phone always fresh, PC can stay off.
