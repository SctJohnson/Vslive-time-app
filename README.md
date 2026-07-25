# VSLive! Seattle 2026 — Schedule PWA

Personal offline-first schedule app for VSLive! @ Microsoft HQ, July 27 – Aug 2, 2026.
Static PWA, no backend; deployed to GitHub Pages via Actions from `main`.

See [APP-OVERVIEW.md](APP-OVERVIEW.md) for what it does and the reasoning behind the
design decisions.

**Install (Android):** open the Pages URL in Chrome → menu ⋮ → *Add to Home screen*.

**Update the schedule:** from the desktop, edit `schedule-data.json` (local only,
gitignored) and run `python tools/schedule_tool.py encrypt` + `bump`, then push. From
anywhere else, use the **Update Schedule** Actions workflow (see `CLAUDE.md`). The
schedule is stored encrypted (`payload.enc.js`); the passphrase lives only on the dev
machine, the phone, and the `SCHEDULE_PASSPHRASE` Actions secret.
