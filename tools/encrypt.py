"""Encrypt schedule-data.json -> payload.enc.js for the public site.

Passphrase comes from .passphrase in the repo root (gitignored, one line) or an
interactive prompt. PBKDF2-HMAC-SHA256 (300k iterations) -> AES-256-GCM, matching
the WebCrypto parameters in index.html. Run from the repo root:

    python tools/encrypt.py
"""
import base64
import getpass
import hashlib
import json
import os
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITERATIONS = 300_000


def get_passphrase():
    pf = os.path.join(ROOT, ".passphrase")
    if os.path.exists(pf):
        with open(pf, encoding="utf-8") as f:
            p = f.read().strip()
        if p:
            return p
    return getpass.getpass("Passphrase: ")


def main():
    with open(os.path.join(ROOT, "schedule-data.json"), encoding="utf-8") as f:
        plaintext = json.dumps(json.load(f), separators=(",", ":")).encode()

    passphrase = get_passphrase()
    if not passphrase:
        sys.exit("Empty passphrase — aborting.")

    salt = os.urandom(16)
    iv = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, ITERATIONS)
    data = AESGCM(key).encrypt(iv, plaintext, None)

    b64 = lambda b: base64.b64encode(b).decode()
    out = f'const ENC = {{ v: 1, iter: {ITERATIONS}, salt: "{b64(salt)}", iv: "{b64(iv)}", data: "{b64(data)}" }};\n'
    with open(os.path.join(ROOT, "payload.enc.js"), "w", encoding="utf-8") as f:
        f.write(out)
    print(f"payload.enc.js written ({len(data)} bytes ciphertext). Remember: bump VERSION in sw.js.")


if __name__ == "__main__":
    main()
