"""Schedule pipeline tool: encrypt / decrypt / apply / bump.

The passphrase is resolved in order: SCHEDULE_PASSPHRASE env var (CI), .passphrase
file in the repo root (desktop, gitignored), interactive prompt. Crypto parameters
must match the WebCrypto code in index.html: PBKDF2-HMAC-SHA256 300k iterations,
AES-256-GCM.

Commands (run from repo root):
    python tools/schedule_tool.py decrypt          payload.enc.js -> schedule-data.json
    python tools/schedule_tool.py apply EDITS.json apply edit ops to schedule-data.json
    python tools/schedule_tool.py encrypt          schedule-data.json -> payload.enc.js
    python tools/schedule_tool.py bump             increment VERSION in sw.js

Edit ops file is a JSON array; each op is one of:
    {"id": "H05", "set": {"room": "Montlake", "bldg": 98}}   merge fields into item
    {"id": "H05", "remove": true}                            delete item
    {"day": "2026-07-30", "add": {..full item..}}            insert item, sorted by start
    {"day": "2026-07-30", "set": {"banner": "..."}}          merge day-level fields
    {"replace_all": {..full schedule object..}}              escape hatch, replaces everything
"""
import base64
import getpass
import hashlib
import json
import os
import re
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "schedule-data.json")
PAYLOAD = os.path.join(ROOT, "payload.enc.js")
SW = os.path.join(ROOT, "sw.js")
ITERATIONS = 300_000


def get_passphrase():
    p = os.environ.get("SCHEDULE_PASSPHRASE", "").strip()
    if p:
        return p
    pf = os.path.join(ROOT, ".passphrase")
    if os.path.exists(pf):
        with open(pf, encoding="utf-8") as f:
            p = f.read().strip()
        if p:
            return p
    return getpass.getpass("Passphrase: ")


def derive(passphrase, salt):
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, ITERATIONS)


def cmd_encrypt():
    with open(DATA, encoding="utf-8") as f:
        plaintext = json.dumps(json.load(f), separators=(",", ":")).encode()
    passphrase = get_passphrase()
    if not passphrase:
        sys.exit("Empty passphrase — aborting.")
    salt, iv = os.urandom(16), os.urandom(12)
    data = AESGCM(derive(passphrase, salt)).encrypt(iv, plaintext, None)
    b64 = lambda b: base64.b64encode(b).decode()
    with open(PAYLOAD, "w", encoding="utf-8") as f:
        f.write(f'const ENC = {{ v: 1, iter: {ITERATIONS}, salt: "{b64(salt)}", iv: "{b64(iv)}", data: "{b64(data)}" }};\n')
    print(f"payload.enc.js written ({len(data)} bytes ciphertext).")


def cmd_decrypt():
    with open(PAYLOAD, encoding="utf-8") as f:
        src = f.read()
    fields = dict(re.findall(r'(\w+): "([^"]*)"', src))
    iters = int(re.search(r"iter: (\d+)", src).group(1))
    salt, iv, data = (base64.b64decode(fields[k]) for k in ("salt", "iv", "data"))
    passphrase = get_passphrase()
    try:
        plain = AESGCM(derive(passphrase, salt) if iters == ITERATIONS else
                       hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, iters)).decrypt(iv, data, None)
    except Exception:
        sys.exit("Decrypt failed — wrong passphrase or corrupted payload.")
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(json.loads(plain), f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("schedule-data.json written.")


def find_item(schedule, item_id):
    for day in schedule["days"]:
        for i, it in enumerate(day["items"]):
            if it["id"] == item_id:
                return day, i
    sys.exit(f"apply: no item with id '{item_id}'")


def cmd_apply(edits_path):
    with open(edits_path, encoding="utf-8") as f:
        ops = json.load(f)
    if not isinstance(ops, list):
        sys.exit("apply: edits must be a JSON array of ops")
    if not ops:
        print("apply: no ops, nothing to do.")
        return
    with open(DATA, encoding="utf-8") as f:
        schedule = json.load(f)

    for op in ops:
        if "replace_all" in op:
            schedule = op["replace_all"]
            if not isinstance(schedule.get("days"), list):
                sys.exit("apply: replace_all payload has no days array")
        elif "id" in op:
            day, i = find_item(schedule, op["id"])
            if op.get("remove"):
                del day["items"][i]
            elif isinstance(op.get("set"), dict):
                day["items"][i].update(op["set"])
            else:
                sys.exit(f"apply: op for id '{op['id']}' needs 'set' or 'remove'")
        elif "day" in op:
            match = [d for d in schedule["days"] if d["key"] == op["day"]]
            if not match:
                sys.exit(f"apply: no day with key '{op['day']}'")
            d = match[0]
            if isinstance(op.get("add"), dict):
                item = op["add"]
                missing = [k for k in ("id", "start", "end", "time", "title") if k not in item]
                if missing:
                    sys.exit(f"apply: added item missing fields {missing}")
                if any(it["id"] == item["id"] for day in schedule["days"] for it in day["items"]):
                    sys.exit(f"apply: id '{item['id']}' already exists")
                d["items"].append(item)
            elif isinstance(op.get("set"), dict):
                d.update(op["set"])
            else:
                sys.exit(f"apply: op for day '{op['day']}' needs 'add' or 'set'")
        else:
            sys.exit(f"apply: unrecognized op {op}")

    for day in schedule["days"]:
        day["items"].sort(key=lambda it: it["start"])
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"apply: {len(ops)} op(s) applied.")


def cmd_bump():
    with open(SW, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'const VERSION = "v(\d+)";', src)
    if not m:
        sys.exit("bump: VERSION line not found in sw.js")
    new = f'const VERSION = "v{int(m.group(1)) + 1}";'
    with open(SW, "w", encoding="utf-8") as f:
        f.write(src.replace(m.group(0), new, 1))
    print(f"bump: sw.js VERSION -> v{int(m.group(1)) + 1}")


if __name__ == "__main__":
    cmds = {"encrypt": cmd_encrypt, "decrypt": cmd_decrypt, "bump": cmd_bump}
    if len(sys.argv) >= 3 and sys.argv[1] == "apply":
        cmd_apply(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] in cmds:
        cmds[sys.argv[1]]()
    else:
        sys.exit(__doc__)
