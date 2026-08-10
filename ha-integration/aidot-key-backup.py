#!/usr/bin/env python3
"""Extract AiDot per-device local-control credentials from Home Assistant and
store them in an encrypted file outside HA.

WHY THIS EXISTS
---------------
AiDot bulbs are controlled locally over TCP :10000 using two static per-device
secrets -- `password` and `aesKey` -- which are issued exactly once, by the AiDot
cloud, during onboarding. Nothing about day-to-day control needs the internet.

That means the vendor cloud is a *key-distribution mechanism*, not part of the
control path. Once these triplets are safely off-box, the bulbs keep working even
if AiDot shuts the service down permanently.

SAFETY MODEL
------------
`core.config_entries` holds the secrets of EVERY configured integration --
cloud tokens, API keys, the lot. This script therefore:

  * filters ON THE HOME ASSISTANT SIDE, so only the aidot rows ever cross the
    wire; the full file is never transferred, never written to local disk, and
    never held in this process's memory;
  * excludes the AiDot ACCOUNT token by design (it is re-obtainable by logging
    in again, and backing it up would extend the blast radius for no gain);
  * never prints a secret -- terminal output is counts and device names only;
  * writes ciphertext only, mode 0600, and refuses to write into a git work tree.

USAGE
-----
    ./aidot-key-backup.py --host <user>@<ha-host> --out ~/secure-backup
    ./aidot-key-backup.py --host <user>@<ha-host> --dry-run

Passphrase resolution order:
    1. $AIDOT_BACKUP_PASSPHRASE
    2. `bw get password <item>`  (--bw-item)
    3. interactive prompt

RESTORE
-------
    gpg --decrypt aidot-keys-<date>.json.gpg > /tmp/keys.json   # tmpfs ideally
See the runbook for what to do with the triplets.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STORAGE = "/homeassistant/.storage/core.config_entries"

# Runs ON the HA host. Emits ONLY aidot per-device triplets -- never the file.
REMOTE_FILTER = r'''
import json, sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        blob = json.load(fh)
except FileNotFoundError:
    print(json.dumps({"error": "storage_not_found", "path": path}))
    sys.exit(0)
except Exception as exc:
    print(json.dumps({"error": "storage_unreadable", "detail": str(exc)}))
    sys.exit(0)

out = {"entries": []}
for entry in blob.get("data", {}).get("entries", []):
    if entry.get("domain") != "aidot":
        continue
    data = entry.get("data") or {}
    manual_ips = data.get("manual_ips") or {}

    # The account user id is REQUIRED for the local TCP login handshake -- the bulb
    # resets the connection without it, so a backup of only the per-device triplet
    # is NOT restorable. Verified against real hardware 2026-08-09.
    # `login_response` is the fork's key; core stores login info at the top level.
    login_info = data.get("login_response") or data
    user_id = login_info.get("id") if isinstance(login_info, dict) else None
    devices = []
    for dev in data.get("device_list") or []:
        aes = dev.get("aesKey")
        if isinstance(aes, list):
            aes = aes[0] if aes else None
        if not dev.get("id"):
            continue
        devices.append({
            "id": dev.get("id"),
            "name": dev.get("name"),
            "mac": dev.get("mac"),
            "modelId": dev.get("modelId"),
            "hardwareVersion": dev.get("hardwareVersion"),
            "password": dev.get("password"),
            "aesKey": aes,
            "manual_ip": manual_ips.get(dev.get("id")),
        })
    out["entries"].append({
        "entry_id": entry.get("entry_id"),
        "title": entry.get("title"),
        "user_id": user_id,
        "device_count": len(devices),
        "devices": devices,
    })

# NOTE: the account ACCESS/REFRESH TOKENS are deliberately NOT emitted -- only the
# non-secret `id`, which local login requires.
print(json.dumps(out))
'''


def fail(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def inside_git_worktree(path: Path) -> bool:
    """True if `path` sits inside a git work tree (secrets must not land in a repo)."""
    try:
        res = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return res.returncode == 0 and res.stdout.strip() == "true"


def fetch_triplets(host: str, storage: str) -> dict:
    """Run the filter remotely; only aidot rows come back."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
           host, f"sudo -n python3 - {storage}"]
    try:
        res = subprocess.run(cmd, input=REMOTE_FILTER, capture_output=True,
                             text=True, timeout=90)
    except subprocess.TimeoutExpired:
        fail(f"timed out connecting to {host}")
    except OSError as exc:
        fail(f"could not run ssh: {exc}")

    if res.returncode != 0:
        fail(f"remote extraction failed (rc={res.returncode}): "
             f"{res.stderr.strip()[:400]}")

    stdout = res.stdout.strip()
    if not stdout:
        fail("remote filter produced no output")
    try:
        payload = json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError:
        # Never echo raw stdout -- it could contain unexpected material.
        fail("remote filter returned unparseable output (not shown, may contain secrets)")

    if "error" in payload:
        fail(f"remote: {payload['error']} {payload.get('path', '')}".strip())
    return payload


def resolve_passphrase(bw_item: str | None) -> str:
    env = os.environ.get("AIDOT_BACKUP_PASSPHRASE")
    if env:
        return env
    if bw_item:
        try:
            res = subprocess.run(["bw", "get", "password", bw_item],
                                 capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
            print(f"note: `bw get password {bw_item}` did not return a value; "
                  "falling back to prompt", file=sys.stderr)
        except (OSError, subprocess.SubprocessError):
            print("note: bw unavailable; falling back to prompt", file=sys.stderr)
    first = getpass.getpass("Passphrase for the encrypted backup: ")
    second = getpass.getpass("Confirm passphrase: ")
    if first != second:
        fail("passphrases did not match")
    if not first:
        fail("empty passphrase refused")
    return first


def encrypt(plaintext: str, passphrase: str, dest: Path) -> None:
    """Symmetric AES256 via gpg. Passphrase via fd 0 is not an option (stdin holds
    the plaintext), so use a pipe fd that never touches the filesystem."""
    read_fd, write_fd = os.pipe()
    os.write(write_fd, passphrase.encode())
    os.close(write_fd)
    cmd = [
        "gpg", "--batch", "--yes", "--quiet",
        "--symmetric", "--cipher-algo", "AES256",
        "--passphrase-fd", str(read_fd),
        "--output", str(dest),
    ]
    try:
        res = subprocess.run(cmd, input=plaintext, capture_output=True,
                             text=True, pass_fds=(read_fd,), timeout=120)
    finally:
        try:
            os.close(read_fd)
        except OSError:
            pass
    if res.returncode != 0:
        fail(f"gpg encryption failed: {res.stderr.strip()[:300]}")
    os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)  # 0600


def verify(dest: Path, passphrase: str, expected: int) -> int:
    """Decrypt in-memory and confirm the device count. A backup that has not been
    round-tripped is a claim, not a backup."""
    read_fd, write_fd = os.pipe()
    os.write(write_fd, passphrase.encode())
    os.close(write_fd)
    cmd = ["gpg", "--batch", "--quiet", "--decrypt",
           "--passphrase-fd", str(read_fd), str(dest)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             pass_fds=(read_fd,), timeout=120)
    finally:
        try:
            os.close(read_fd)
        except OSError:
            pass
    if res.returncode != 0:
        fail(f"verification decrypt failed: {res.stderr.strip()[:300]}")
    try:
        blob = json.loads(res.stdout)
    except json.JSONDecodeError:
        fail("verification failed: decrypted payload is not valid JSON")
    return sum(e.get("device_count", 0) for e in blob.get("entries", []))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Back up AiDot per-device local-control keys, encrypted.")
    ap.add_argument("--host", required=True,
                    help="ssh target for Home Assistant, e.g. user@ha-host")
    ap.add_argument("--storage", default=DEFAULT_STORAGE,
                    help=f"path to core.config_entries (default: {DEFAULT_STORAGE})")
    ap.add_argument("--out", default="~/secure-backup",
                    help="output DIRECTORY (default: ~/secure-backup)")
    ap.add_argument("--bw-item", default="aidot-key-backup",
                    help="Vaultwarden item holding the backup passphrase")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be extracted; write nothing")
    args = ap.parse_args()

    payload = fetch_triplets(args.host, args.storage)
    entries = payload.get("entries", [])
    if not entries:
        fail("no `aidot` config entry found -- onboard the bulbs and set up the "
             "integration first")

    total = sum(e.get("device_count", 0) for e in entries)
    complete = sum(
        1 for e in entries for d in e["devices"] if d.get("password") and d.get("aesKey")
    )

    print(f"Found {len(entries)} aidot config entry/entries, {total} device(s).")
    missing_uid = [e for e in entries if not e.get("user_id")]
    if missing_uid:
        print("WARNING: an entry has no account user_id. Local login WILL be rejected "
              "by the bulbs ('Connection reset by peer') -- this backup would not be "
              "restorable. Re-check the integration setup.", file=sys.stderr)
    for e in entries:
        print(f"  entry {e.get('title')}: user_id="
              f"{'present' if e.get('user_id') else 'MISSING'}")
        for d in e["devices"]:
            have = "OK  " if (d.get("password") and d.get("aesKey")) else "MISSING"
            ip = d.get("manual_ip") or "-"
            print(f"  [{have}] {d.get('name') or '(unnamed)'}  "
                  f"model={d.get('modelId') or '?'}  manual_ip={ip}")
    print(f"Credential triplets complete: {complete}/{total}")

    if complete != total:
        print("WARNING: some devices are missing password/aesKey. They cannot be "
              "controlled locally. Re-check the AiDot onboarding for those bulbs.",
              file=sys.stderr)

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    out_dir = Path(os.path.expanduser(args.out)).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if inside_git_worktree(out_dir):
        fail(f"refusing to write secrets inside a git work tree: {out_dir}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = out_dir / f"aidot-keys-{stamp}.json.gpg"

    payload["_meta"] = {
        "generated_utc": stamp,
        "source": "home-assistant core.config_entries (aidot entries only)",
        "note": "AiDot account token deliberately excluded.",
    }

    passphrase = resolve_passphrase(args.bw_item)
    encrypt(json.dumps(payload, indent=2), passphrase, dest)

    verified = verify(dest, passphrase, total)
    if verified != total:
        fail(f"verification mismatch: encrypted {total} devices, "
             f"decrypted {verified}")

    print(f"\nWrote {dest}  (mode 0600)")
    print(f"Verified by round-trip decrypt: {verified} device(s) recoverable.")
    print("Store the passphrase in Vaultwarden. Without it this file is unrecoverable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
