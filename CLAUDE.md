# Session guide — VSLive schedule PWA

Static offline-first PWA on GitHub Pages. The schedule payload is **encrypted at
rest** (`payload.enc.js`); the plaintext source and passphrase exist only on the
owner's desktop and as the `SCHEDULE_PASSPHRASE` Actions secret. Read
APP-OVERVIEW.md for the full design reasoning.

## Hard rules

- **Never commit plaintext schedule data or any passphrase/secret.**
  `schedule-data.json` and `.passphrase` are gitignored on purpose. Do not recreate
  their contents in tracked files, issues, PR text, or workflow inputs.
- Do not hand-edit `payload.enc.js` — it is generated ciphertext.
- Do not remove or weaken the crypto parameters in `index.html` / `tools/schedule_tool.py`
  (they must stay in sync: PBKDF2-SHA256 300k iterations, AES-256-GCM).

## How to change the schedule (works from a cloud session — no desktop needed)

1. Express the change as edit ops (schema in `tools/schedule_tool.py` docstring), e.g.
   `[{"id": "H05", "set": {"room": "Montlake", "bldg": 98}}]`
2. Either write the ops array into `pending-edits.json` and push to `main`, or run
   `gh workflow run update-schedule.yml -f edits='<ops JSON>'`.
3. The **Update Schedule** workflow decrypts with the repo secret, applies the ops,
   re-encrypts, bumps the service-worker VERSION, commits, and deploys. Watch it to a
   green conclusion (`gh run watch`) and report the real result.

**Privacy rule for this channel:** `pending-edits.json` and dispatch inputs are
publicly visible. Only conference-public facts go through them (room moves, speaker
swaps, session times). Personal travel changes are made on the owner's desktop copy
only — if asked to make one from a cloud session, explain this and decline the
public-channel route.

## Shell / app changes (index.html, sw.js, styling)

Normal PR flow: branch → verify at 375px mobile width → PR → merge. A push to `main`
that changes non-`.md` files triggers the regular Pages deploy. If you change any
precached asset, bump `VERSION` in `sw.js` (the update workflow only auto-bumps for
schedule edits).

## Owner conventions

- Small verified PRs; never commit directly to `main` except via the update workflow.
- Commit messages end with `Co-Authored-By: <model name> <noreply@anthropic.com>`.
- Verify in a browser at 375px before claiming done; cards over tables.
