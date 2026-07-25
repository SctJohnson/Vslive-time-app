# VSLive! Seattle 2026 — Schedule PWA

Personal offline-first schedule app for VSLive! @ Microsoft HQ, July 27 – Aug 2, 2026.
Static PWA, no backend; deployed to GitHub Pages via Actions from `main`.

See [APP-OVERVIEW.md](APP-OVERVIEW.md) for what it does and the reasoning behind the
design decisions.

**Install (Android):** open the Pages URL in Chrome → menu ⋮ → *Add to Home screen*.

**Update the schedule:** edit `schedule-data.json` (local only, gitignored), run
`python tools/encrypt.py`, bump `VERSION` in `sw.js`, push to `main`. The schedule is
stored encrypted (`payload.enc.js`) — the passphrase never leaves the dev machine and
the phone.
