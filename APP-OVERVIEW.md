# VSLive! Seattle 2026 — Schedule PWA

Personal, mobile-only schedule app for VSLive! @ Microsoft HQ (Redmond, July 27 – Aug 2,
2026). Installed as a PWA on Scott's Android phone; used standing in lobbies, on
shuttles, and inside session rooms with unreliable connectivity.

## What it does

- **Day tabs (Mon 7/27 → Sun 8/2)** with card-per-event, auto-opens today (Pacific time).
- **Now / Next panel** on today's tab: what's in progress, what's next and in how many
  minutes, with a loud warning when the next session is in Building 92.
- **Session notes**: tap a card → textarea, autosaved to `localStorage` on every
  keystroke. Export all notes as Markdown (clipboard or Android share sheet) from Info.
- **Info tab**: Wi-Fi code, shuttle pickup, phone numbers, slides credentials, meal-card
  rules, watch-outs, and the themes being tracked across sessions.
- **Wednesday banner**: the raffle-by-2:45 / leave-W24-early / 5:30-bus choreography as
  a persistent warning on that day's tab.

## Reasoning behind the design (the part worth keeping)

- **No backend, no accounts.** The app was built the day before travel. Everything that
  needs a server (push notifications, sync) was cut deliberately: PWA local scheduled
  notifications are still unreliable (no dependable background timer), and push requires
  a server to send from. The substitute is the time-aware Now/Next panel — it answers
  the same question ("where am I supposed to be?") on open.
- **Offline-first is the core requirement, not a feature.** Conference Wi-Fi
  (MSFTGUEST), shuttles, and T-Mobile Park are all connectivity dead zones. The service
  worker precaches everything; navigations are **network-first with a 2.5s timeout**
  falling back to cache — so schedule fixes propagate when online, but a flaky network
  never blocks the app.
- **Schedule data is inline in `index.html`**, not a fetched JSON. One file to edit,
  one round-trip fewer to cache, and the whole app remains greppable. The PDFs
  themselves warn that speakers shift day-of ("T02's presenter already changed"), so the
  update path is: edit the `DAYS` array → bump `VERSION` in `sw.js` → push → live in
  ~1 minute via Actions.
- **`loose: true` events** (≈ times: shuttles, MoPOP pickup, "evening") are excluded
  from Now/Next urgency math. The itinerary mixes hard commitments with flexible blocks;
  treating "~11am pickup" as a deadline would make the panel cry wolf. `tentative: true`
  (Saturday aquarium) additionally renders a dashed tag.
- **All times are stored as minutes-from-midnight *Pacific*** and the clock reads
  Pacific via `Intl` regardless of device timezone — so the app is already correct if
  opened before the phone's clock flips from Central.
- **Building 92 vs 98 is a first-class field** (`bldg`), not part of the room string.
  It drives the amber room color, the "(Bldg 92 — walk!)" flag in Next, and the
  computed ⚠ building-change dividers between consecutive sessions.
- **Notes save on `input`, not blur** (see UI gotchas in global CLAUDE.md), and cards
  fade when past rather than disappearing — you still want to jot a note about a
  session that just ended.
- **The entire schedule payload is encrypted at rest in the repo.** GitHub Pages
  cannot put auth in front of a site on any plan, and a week-long hour-by-hour
  itinerary is location data — stalker-grade if found. So the public repo/site carry
  only ciphertext (`payload.enc.js`): AES-256-GCM, key derived from a passphrase via
  PBKDF2-HMAC-SHA256 (300k iterations), decrypted client-side with WebCrypto. The
  plaintext source (`schedule-data.json`) and the passphrase file (`.passphrase`) are
  gitignored and exist only on the dev machine. Personal booking references (flight
  confirmation, shuttle bookings, lounge order) live inside the encrypted payload.
- **The passphrase is cached in `localStorage` after first unlock** — deliberately the
  passphrase, not the derived key, so re-encrypted payloads (fresh salt each run of
  `tools/encrypt.py`) still auto-unlock without re-prompting mid-conference. Exposure
  is equivalent: anyone with the unlocked phone has the data anyway. Consequence: the
  passphrase should be unique to this app, not a reused one.
- **Git history was reset when encryption landed** — v1 had committed the schedule in
  plaintext, and a public repo's history is as public as its HEAD.

## Deploy

GitHub Actions from `main` (`.github/workflows/deploy.yml`) → GitHub Pages via
`deploy-pages`, `paths-ignore: '**.md'` so doc-only changes skip the deploy. No build
step — the repo root *is* the site.

**Schedule update paths** (two, by design — Scott is at the conference with only a
phone for a week):

- **Desktop:** edit `schedule-data.json` → `python tools/schedule_tool.py encrypt`
  (reads `.passphrase`) → `python tools/schedule_tool.py bump` → push. Without the
  VERSION bump, installed clients keep the old cached `payload.enc.js` (index.html
  itself refreshes via network-first regardless).
- **Cloud (no desktop):** the `update-schedule.yml` workflow holds the passphrase as
  the `SCHEDULE_PASSPHRASE` Actions secret and does decrypt → apply ops → encrypt →
  bump → commit → deploy entirely in the runner. Triggered by `workflow_dispatch`
  with an `edits` input, or by pushing ops into `pending-edits.json`. The runner
  deploys Pages itself because a GITHUB_TOKEN push doesn't trigger the regular deploy
  workflow. Plaintext exists in the runner for seconds and is deleted before the
  Pages artifact is built (the artifact would otherwise publish it — that `rm` step
  is load-bearing).

**Known accepted leak:** the edit channel (`pending-edits.json`, dispatch inputs) is
publicly visible, so it carries conference-public facts only — room/speaker/time
changes that VSLive publishes anyway. Personal travel edits stay desktop-only. The
upgrade path if this ever matters: hybrid public-key encryption of the edits file
(public key in repo, private key as a second Actions secret).

## Known trade-offs

- Notes live only in the phone's `localStorage` — the Markdown export button is the
  backup story. Good enough for one week; would need real storage for anything longer.
- The Now/Next panel only looks at the current day; at 11pm it shows nothing rather
  than "tomorrow: shuttle at 7". Acceptable — the day tabs are one tap away.
