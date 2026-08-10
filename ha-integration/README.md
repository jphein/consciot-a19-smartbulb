# Consciot A19 → Home Assistant: setup runbook

Local control of Consciot / AiDot Wi-Fi bulbs in Home Assistant, with the vendor
cloud reduced to a **one-time key-issuing step** rather than a permanent dependency.

> Consciot is a brand of **AiDot Inc.** These bulbs are **not Tuya** (LocalTuya,
> tuya-convert and cloudcutter do not apply) and — for the app-onboarded Wi-Fi
> line — **not Matter**.

## What's here

| Path | Purpose |
|---|---|
| `aidot-key-backup.py` | Extracts each bulb's local-control credentials from HA and stores them encrypted, off-box |

The integration itself is **not vendored here** — install it from upstream via HACS
(below). Redistributing a pinned copy would only produce a stale fork with no update
path, so this repo references upstream rather than duplicating it.

## How local is it, exactly?

Read from the `python-aidot` source, not the vendor's marketing:

| Phase | Transport | Needs internet? |
|---|---|---|
| Account auth + credential issue | HTTPS → AiDot cloud | **Yes — once** |
| Device IP discovery | UDP broadcast `:6666` | No |
| Control + state | **TCP `:10000`**, AES-encrypted per device | No |

Each bulb has two static secrets — `password` and `aesKey` — issued once at
onboarding. The cloud is a **key-distribution mechanism, not part of the control
path**. Back the secrets up and the bulbs outlive the vendor.

## Install

The integration domain is **`aidot`**.

> ⚠️ This **shadows Home Assistant's official `aidot` core integration** (they share
> a domain; `custom_components/` always wins). That is intentional here — the core
> integration has no manual-IP option and re-fetches the device list from the cloud
> every 6 hours, failing hard when auth fails. **If the official AiDot integration is
> already configured, delete its config entry before installing this.**

### Install via HACS

1. HACS → ⋮ → **Custom repositories**
2. URL `https://github.com/sulibot/hass-AiDot`, category **Integration** → **Add**
3. Install **AiDot Lights Local** → **restart Home Assistant**

Expect a log line noting you are using a custom integration — that is normal.

Installing from upstream means you get fixes as they land. Pin a specific version in
HACS if you would rather control when that happens.

## Configure

**Settings → Devices & Services → Add Integration → AiDot**

1. **Country / email / password** — your AiDot account
2. **Choose house**
3. **Discovery method** → select **"Configure device IPs manually"**
4. Enter each bulb's IP
5. Submit

### Manual IPs are required on a segmented network

Discovery broadcasts to `255.255.255.255:6666` from a socket bound to `0.0.0.0`.
A limited broadcast leaves via **exactly one** interface — whichever carries the
default route. If your bulbs sit on an IoT VLAN that is *not* HA's default route,
**auto-discovery cannot reach them**, even when HA has an interface on that VLAN.

Manual IPs bypass discovery entirely and take priority over any discovered address.

**Pair this with DHCP reservations.** A manual IP is a fixed pointer; if a bulb's
lease moves, the entity simply goes unavailable with no recovery path.

Both manual IPs and the poll interval are editable later via the integration's
**Configure** button — you do not have to redo the flow.

### Poll interval: raise it for multi-bulb installs

The integration serializes status refreshes behind a **global semaphore** (one
device at a time), with two attempts and a 15 s timeout each — up to ~30 s per
unreachable device. With the default 30 s poll and six bulbs, a bad patch can
queue refreshes faster than they drain.

**Recommended: 60 s for six bulbs.** State is *pushed* over the persistent TCP
connection, so polling is a backstop, not the main path — a longer interval costs
little responsiveness.

⚠️ **Don't just raise it arbitrarily — the two settings are coupled:**

```python
self._availability_grace_seconds = max(poll_interval * 10, 300)
```

| poll_interval | grace before a bulb reads *unavailable* |
|---|---|
| 30 s (default) | 300 s (5 min) |
| **60 s (recommended)** | **600 s (10 min)** |
| 120 s | 1200 s (**20 min**) |

At 120 s a genuinely dead bulb still reports *available* for twenty minutes, so
automations act on stale state. 60 s drains the serialized refresh queue comfortably
for six bulbs while keeping the grace window defensible.

## Entities

One `light.*` per bulb:

| Capability | Notes |
|---|---|
| On / off | — |
| Brightness | device reports 0–100, scaled to HA's 0–255 |
| Colour | `ColorMode.RGBW` — four channels, not plain RGB |
| Colour temperature | min/max **read from the device**, typically ~2700–6500 K |
| Availability | tracks the local TCP session, with a grace window |

Not exposed: music-sync / microphone reactivity and vendor "scenes" — app-side
features with no protocol representation.

## Back up the keys

```bash
./aidot-key-backup.py --host <user>@<ha-host> --dry-run   # inspect first
./aidot-key-backup.py --host <user>@<ha-host> --out ~/secure-backup
```

`core.config_entries` holds **every** integration's secrets, so the script filters
**on the Home Assistant side** — only `aidot` rows cross the wire. The full file is
never transferred and never written locally. The AiDot **account token is excluded
by design** (re-obtainable by logging in; backing it up only widens the blast radius).

Output is gpg symmetric AES256, mode `0600`, round-trip verified before the script
reports success. It refuses to write inside a git work tree.

Passphrase resolution: `$AIDOT_BACKUP_PASSPHRASE` → `bw get password <item>` →
interactive prompt. **Store the passphrase in a password manager — without it the
file is unrecoverable.**

### Restore

```bash
gpg --decrypt aidot-keys-<stamp>.json.gpg > /dev/shm/keys.json   # tmpfs, not disk
```

Yields the account `user_id` plus, per bulb: `id`, `name`, `mac`, `modelId`, `password`,
`aesKey`, `manual_ip`.

⚠️ **The credential set is a quadruplet, not a triplet:**

```
userId  +  deviceId  +  password  +  aesKey
```

The local TCP login payload is `{userId, password}`, so **the account user id is
required** — without it the bulb answers `[Errno 104] Connection reset by peer`. This was
found by restoring a backup and driving real hardware with it; a backup missing that field
looks healthy and verifies its own integrity, then fails exactly when you need it. The
script captures it and warns loudly if it is absent. Account access/refresh **tokens**
remain excluded — only the non-secret `id` is stored.

That is everything needed to drive the bulb over TCP `:10000` — via this integration,
or via any client you write against `python-aidot`. Shred the plaintext afterwards.

> **Re-run the backup if you made one before this fix.** An earlier backup that lacks
> `user_id` will decrypt cleanly and still be unusable. Keep the newer file.

## Acceptance test — prove it is actually local

The claim "cloud-once" is only worth what the test proves:

1. Complete onboarding and confirm all bulbs work.
2. Run the key backup.
3. **Block the bulbs' VLAN from outbound internet** at the firewall.
4. **Restart Home Assistant.**
5. Confirm every bulb still toggles, dims, and changes colour.

Passing step 5 is what demonstrates the credentials are cached and the control path
is genuinely local. Snapshot your firewall config before step 3.

## Credits

Integration by [`sulibot/hass-AiDot`](https://github.com/sulibot/hass-AiDot) (MIT), a
fork of [`toxuin/hass-AiDot`](https://github.com/toxuin/hass-AiDot), built on
[`python-aidot`](https://github.com/AiDot-Development-Team/python-AiDot).

All integration code stays with upstream — install it from there. The only original
work in this directory is `aidot-key-backup.py`, MIT-licensed under this repository's
[LICENSE](../LICENSE).
