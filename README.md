# Consciot A19 (AiDot Wi-Fi) → Home Assistant, Local

**Device:** Consciot A19 Smart Light Bulb · Amazon **B0G6YFQDFW** · 800 lm · 60 W-equivalent ·
RGB color-changing · E26 A19 · dimmable · 2.4 GHz Wi-Fi · sold as a 6-pack
**Platform:** **AiDot Wi-Fi line** — owner-confirmed from the physical packaging. **Not Matter.
Not Tuya.**
**Goal:** all six bulbs in Home Assistant, controlled locally, with the vendor cloud out of the
picture after setup.

---

## TL;DR — the honest version

**There is no way to set these bulbs up without the vendor. There is a way to never need it
again.**

Getting a factory-fresh AiDot bulb onto your network requires AiDot's app and AiDot's cloud, and no
community tool replaces either. But once that one-time bootstrap is done, the
**`sulibot/hass-AiDot`** fork caches the per-device keys and keeps working with the internet cut
off. That end state is genuinely local — it just costs one afternoon with a vendor account.

```
                ONE TIME                          FOREVER AFTER
   AiDot app ──> AiDot cloud                Home Assistant ──> Bulb ×6
   (Wi-Fi creds)  (issues keys)              AES-encrypted TCP :10000
        └──────────┬──────────┘                  no cloud · no internet
        back up the keys, then
        firewall it off for good
```

**The five steps:**

1. Onboard all six bulbs once in the **AiDot app**, using a **throwaway account**.
2. Install **`sulibot/hass-AiDot`** via HACS and log in **once**.
3. **Back up each bulb's `deviceId` + `password` + `aesKey`** — the step that makes the rest permanent.
4. Give every bulb a **static IP / DHCP reservation** and configure it **manually** (required — see [§5](#5-manual-ips-are-required-not-troubleshooting)).
5. **Firewall the bulbs and Home Assistant outbound**, and confirm control survives a restart.

> **Buying rather than already owning?** AiDot sells an explicitly **Matter-certified** Consciot SKU
> that commissions natively into Home Assistant with no app, no account and no cloud at all. It is
> strictly better and costs about the same. See [§9](#9-the-matter-sku-exists--this-just-isnt-it).

---

## Contents

- [1. What this bulb actually is](#1-what-this-bulb-actually-is)
- [2. The cloud accounting, stated plainly](#2-the-cloud-accounting-stated-plainly)
- [3. Path 1 — `hass-AiDot` ✅ recommended](#3-path-1--hass-aidot--recommended)
- [4. 🔴 Back up the keys the same day](#4--back-up-the-keys-the-same-day)
- [5. Manual IPs are required, not troubleshooting](#5-manual-ips-are-required-not-troubleshooting)
- [6. Proving it is really local](#6-proving-it-is-really-local)
- [7. What you get in Home Assistant](#7-what-you-get-in-home-assistant)
- [8. Security — an open commissioning window](#8-security--an-open-commissioning-window)
- [9. The Matter SKU exists — this just isn't it](#9-the-matter-sku-exists--this-just-isnt-it)
- [10. Flashing — the last resort](#10-flashing--the-last-resort)
- [11. Open questions](#11-open-questions)
- [12. Prior art & credits](#12-prior-art--credits)

---

## 1. What this bulb actually is

**Brand:** Consciot, a brand of **AiDot Inc.** Sibling brands include **Linkind**, **OREiN** and
**Winees**. The app is **AiDot**.

**Manufacturer:** the A19 manual names **Leedarson IoT Technology Inc.** (Xiamen) as producer, with
Spring Sunshine Technology Co., Ltd (HK) as importer of record. Leedarson is a tier-1 lighting ODM
that builds for major brands (FCC grantee codes `2AB2Q`, `2AVZB`). AiDot's own FCC grantee code is
`2BLWS`.

### It is not Tuya — do not reach for the Tuya toolchain

This is the single most common wrong turn, because "cheap Wi-Fi RGB bulb" pattern-matches to Tuya:

- **Zero hits for "Consciot"** across all **1,149 device profiles** in the `tuya-cloudcutter`
  device database.
- AiDot holds its **own CSA vendor ID** and ships its **own app**. A Tuya OEM would appear under
  Tuya's VID and the Smart Life app.
- ⇒ `tuya-convert`, `tuya-cloudcutter` and **LocalTuya do not apply.** A Tuya `local_key` is
  something an AiDot device has no way to possess, and cloudcutter attacks a Tuya activation
  handshake that simply isn't present.

If you already run LocalTuya, that makes it a *more* tempting wrong turn, not a less one.

### It is not Matter either — and here is why that took some pinning down

The owner has the physical packaging: **no Matter logo, no QR, no 11-digit setup code.** That is
decisive, and it settles the question.

It is worth recording why the paper trail pointed the other way, because the next person will hit
the same trap:

- AiDot holds **136 Matter 1.5 certifications**, and there *is* a CSA certificate for a product
  named "Consciot Smart Light Bulb" (AiDot Inc., VID `0x1396`).
- **A CSA certificate binds a product family, not an ASIN.** Consciot ships a Matter line *and* a
  legacy Wi-Fi line side by side. A certificate existing under the brand does not mean the box in
  your hand is the certified variant.
- The four-ecosystem box copy ("Apple Home … SmartThings") is *suggestive* of Matter but not
  conclusive at the SKU level.

**The lesson:** for this vendor, brand-level and certification-level evidence cannot resolve a
SKU-level question. Only the physical box can. If you are documenting one of these, look at the
carton before building an argument.

A third piece of evidence arrived later and is worth recording *with* its limits, because it is the
same trap wearing a better disguise: the SafeThings 2024 paper in [§8](#8-security--an-open-commissioning-window)
**physically tested a "Consciot bulb" over Matter-over-Wi-Fi.** That is stronger evidence than a
certificate — it is a real device on a bench. It still does not tell you what is in *your* box:
"a Consciot bulb" is a brand-level identifier, and Consciot ships both lines. Note also that
**without a setup code printed on the device there is no Matter commissioning path at all**,
whatever the silicon is capable of — a Matter controller has nothing to commission *with*. So
Matter-native setup is not an available alternative for these units, however capable the hardware
may be.

### One more myth worth killing

**"It broadcasts no setup Wi-Fi network, so it must be Tuya SmartConfig."** No. AiDot provisioning
is **BLE-assisted** — the app talks to the bulb over Bluetooth and hands it Wi-Fi credentials. No
SoftAP is expected, and its absence tells you nothing about Tuya either way.

That detail also explains why no community provisioning tool exists: reverse-engineering a BLE
pairing flow is a substantially harder target than an HTTP-to-a-setup-AP flow. Don't expect an
"AiDotTools" to appear.

---

## 2. The cloud accounting, stated plainly

Two separate claims. Keeping them apart is the whole story.

### The bootstrap requires the vendor — twice, unavoidably

| Half | What it does | Community replacement? |
|---|---|---|
| **Provisioning** | The AiDot app pushes Wi-Fi credentials to a factory-fresh bulb | ❌ none exists |
| **Key issuance** | The AiDot cloud issues the per-device `deviceId` + `password` + **`aesKey`** | ❌ none exists |

Nobody has reverse-engineered AiDot provisioning, and no library derives the local `aesKey`
independently of the cloud. The closest public artifact is the protocol documentation inside
`sulibot/hass-AiDot`, which documents the *control* protocol while explicitly sourcing the keys
**from the cloud**.

### The end state does not

Once the keys are cached locally, the fork keeps running without them being re-issued. Control is
**AES-encrypted TCP on port 10000**, device-to-HA, no internet involved. Cut the WAN and the lights
still work.

**So: the vendor owns your setup day, not your next five years** — provided you complete
[§4](#4--back-up-the-keys-the-same-day).

---

## 3. Path 1 — `hass-AiDot` ✅ recommended

### Why the community fork and not the official integration

Home Assistant has a built-in **`aidot`** integration (core, 2026.6+). It is easier to install and
perfectly fine while AiDot is alive. It is also the wrong choice for a setup meant to outlive the
vendor:

| | Official **`aidot`** (HA core) | Community **`sulibot/hass-AiDot`** (HACS) |
|---|---|---|
| Control transport | Persistent **TCP** connection per device | AES-encrypted **TCP :10000** |
| Discovery | — | UDP **:6666** broadcast (*discovery only*) |
| **Cloud after setup** | **Re-checks the cloud every 6 hours, forever** | Cloud at first login only |
| **When cloud auth fails** | Raises `ConfigEntryError` → **the integration stops loading** | Falls back to **cached credentials** and keeps working |
| Credential persistence | — | Persists `aesKey` + `password` to the config entry |
| Install | Built in — easiest | HACS |
| Devices | A19, BR30 | Lights (brightness, color temp), switches |
| Quality tier | Bronze | community |

**That fourth row is the entire decision.** On the day AiDot's auth endpoint stops answering, the
official integration raises a config error and stops loading — and your lights go with it. That is
a vendor-shutdown brick, reproduced in software, in an integration marketed as having local
control. The fork degrades gracefully to *"using cached login info"* and keeps working.

**Use the fork.** It is the harder install and the right one.

### Step 1 — a throwaway AiDot account

The app is unavoidable; your real identity is not. Create the account with an alias address. This
minimises what the vendor learns and costs nothing.

### Step 2 — onboard all six bulbs in the AiDot app

Put them on the network segment you intend them to live on permanently — moving them later means
re-provisioning. The bulbs are **2.4 GHz only**; if your SSID is a single band-steered name, make
sure 2.4 GHz is actually being offered during onboarding, or the join will fail in a way the app
reports unhelpfully.

Also do this now, while the bulbs are on a bench and not yet in fixtures:

- Label each bulb physically (a marker dot on the base) and name it in the app to match.
- Decide the naming scheme by **where the bulb is going** — `kitchen_can_1` — not what it is.

### Step 3 — install the fork and log in once

Add `sulibot/hass-AiDot` through **HACS** as a custom repository, install, restart Home Assistant,
then add the integration and log in with the throwaway account. Select your house when prompted.

### Step 4 — back it up before you do anything else

→ **[§4](#4--back-up-the-keys-the-same-day). Do not skip this.** It is the step that converts a
permanent vendor dependency into a one-time errand, and it is only possible while AiDot is alive.

### Step 5 — configure the bulbs by IP

→ **[§5](#5-manual-ips-are-required-not-troubleshooting).** Required on many setups, not optional
troubleshooting.

### Step 6 — cut the cord and verify

→ **[§6](#6-proving-it-is-really-local).**

---

## 4. 🔴 Back up the keys the same day

The `deviceId` / `password` / **`aesKey`** triplet is issued **only by AiDot's cloud**. It is the
sole thing keeping these bulbs controllable if AiDot ever shuts its servers down. **Back up all six
immediately after onboarding.**

With the fork, the credentials live in Home Assistant's `.storage/core.config_entries`.

### There is a tool in this repo that does it safely

**[`ha-integration/aidot-key-backup.py`](ha-integration/aidot-key-backup.py)** — see the
[setup runbook](ha-integration/README.md) for the full flow.

```bash
./aidot-key-backup.py --host <user>@<ha-host> --dry-run    # inspect first
./aidot-key-backup.py --host <user>@<ha-host> --out ~/secure-backup
```

It filters **on the Home Assistant side**, so only the `aidot` rows ever cross the wire — the
full secrets file is never transferred and never written to local disk. It excludes the AiDot
account token by design, never prints a secret, writes gpg-AES256 ciphertext at mode `0600`,
**refuses to write inside a git work tree**, and round-trip-decrypts to verify before reporting
success. A backup that has not been round-tripped is a claim, not a backup.

> ### ⚠️ That file contains every integration's secrets — not just AiDot's
> API tokens, cloud passwords and access tokens for **everything else** you have configured are in
> there too. Treat a copy as a top-tier secret:
>
> - encrypt it, and store it in a password manager or an encrypted volume
> - **never commit it to a repository**, and never paste it into an issue or a chat
> - if you would rather not handle the whole file, **extract just the per-bulb triplet** and back
>   that up instead — it is all you actually need

**Why this matters more than it sounds.** This is the lesson of every dead-cloud bulb project,
applied one device *earlier*. When a vendor dies, its key issuance dies with it: the secrets become
unobtainable at exactly the moment you need them, and recovery becomes a community
reverse-engineering effort — if it happens at all. Here those secrets are obtainable **right now,
while the vendor is alive**, and only now.

Ten minutes today, or a bricked six-pack later. There is no third option.

---

## 5. Manual IPs are required, not troubleshooting

The fork discovers devices by **UDP broadcast to `255.255.255.255:6666`**. A broadcast like that
leaves **only the default-route interface**.

So on a **multi-homed Home Assistant host** — where the IoT network is reached over a secondary NIC
that is *not* the default route — the discovery packet never goes out the leg the bulbs are on.
**Discovery then finds nothing, silently, while every other part of the configuration looks
correct.** It is a genuinely nasty failure mode because there is no error to read.

**On any multi-homed host, plan on manual configuration from the start:**

- Give **every bulb a DHCP reservation**, so its address never moves.
- Configure **each bulb by IP** in the integration rather than relying on discovery.

Do this as part of setup. Treating it as a troubleshooting step costs an evening of chasing a
discovery mechanism that was never going to work on that topology.

> Note that **UDP :6666 is discovery only** — actual control is the AES-encrypted TCP :10000
> session. Once bulbs are configured by IP, discovery is not in the path at all, which is why
> manual configuration is a clean permanent answer rather than a workaround.

---

## 6. Proving it is really local

This is both the final setup step and the falsifiable test of everything above.

1. **Firewall the bulbs *and* Home Assistant outbound.** Deny WAN egress.
2. **Restart Home Assistant.**
3. **Confirm control still works** — on/off, brightness, color, from the HA UI.

> ### 🚧 This is the one genuinely unverified claim in this document
> The fork's README says "no cloud dependency for device control," and its protocol documentation
> implies credentials are cached — but neither states outright that they survive a restart. **The
> restart is the part that matters**: it is what distinguishes credentials genuinely persisted to
> disk from credentials merely held in memory since login. Do not take either project's marketing
> on faith; run the test yourself, and know the answer before you need it.

Once it passes, **leave the egress block in place permanently.** There is nothing on the far side
of it you want — and with the block in place, a future vendor shutdown becomes a non-event.

Worth also watching what the bulbs attempt outbound for a day. Anything resembling a persistent TLS
session to a vendor endpoint is worth understanding.

---

## 7. What you get in Home Assistant

One `light.*` entity per bulb:

| Capability | Notes |
|---|---|
| On / off | ✅ |
| Brightness | ✅ |
| Color temperature | ✅ ~**2700 K – 6500 K** |
| RGB color | ✅ on capable devices — this bulb is advertised as color-changing |
| Transitions | ⚠️ integration-dependent, not a protocol guarantee |
| Vendor effects / music sync | ❌ app-side only; these do not cross into HA |
| Power / energy metering | ❌ not present in this hardware class |
| Firmware updates | ❌ not surfaced — updates go through the vendor app |

**What you give up versus the app:** music-sync and microphone reactivity, and the vendor's canned
scenes. What you get back is a light that works when the internet doesn't, responds without a
round-trip to someone's data centre, and cannot be switched off by a business decision. Rebuilding
a candle flicker as an HA script is an afternoon; recovering an abandoned cloud bulb is not possible
at all.

### Grouping the six

```yaml
# configuration.yaml
light:
  - platform: group
    name: "Consciot Bulbs"
    entities:
      - light.kitchen_can_1
      - light.kitchen_can_2
      - light.kitchen_can_3
```

---

## 8. Security — an open commissioning window

Independent, peer-reviewed research has found a serious flaw in how AiDot's **Matter** devices
handle commissioning.

> **Shafqat & Ranganathan**, *"Seamlessly Insecure: Uncovering Outsider Access Risks in
> AiDot-Controlled Matter Devices"* — Northeastern University, **SafeThings 2024**.

**What they found.** On the AiDot Matter devices physically tested — a **Consciot bulb** among them
— the Matter **commissioning window stays open after the user has finished commissioning the
device**. Matter's pairing window is supposed to close once a device has joined a fabric. It didn't.

**What that permits.** An outsider can connect to the device and control or monitor it remotely:

- from **more than 30 feet away**, with **no line of sight**
- with **no QR code** and **no setup code**
- with **no Wi-Fi credentials** and **no physical access**
- **without alerting the owner**

The authors replicated it **three times** and confirmed the window was still open **24 hours after
pairing**. The paper's mitigation column for this finding reads **"None."** AiDot did not respond
to a **three-month** coordinated disclosure.

### Does this affect these bulbs?

**Probably not — and the reason is the useful part.**

The same paper found AiDot's **legacy, non-Matter** devices were **not** vulnerable, because their
manufacturer commissioning channel was **already occupied** — leaving no free slot for an outsider
to claim. These bulbs are the legacy Wi-Fi line (owner-confirmed), so on the paper's own evidence
they sit in the category that tested *safe*.

> ### 🛑 But this changes the recommendation in §9
> [§9](#9-the-matter-sku-exists--this-just-isnt-it) tells you to buy the Matter SKU instead, because
> it is simpler and needs no vendor account. That advice now comes with a caveat: **the Matter SKU
> is the variant that tested vulnerable.** It is still a defensible choice — the flaw is a
> commissioning-window bug, not an architectural property of Matter, and it is fixable in firmware —
> but you should make it knowingly rather than discover it later.

### Mitigations

Stated with what each one actually does, because two of the three are **not** fixes for this
specific finding:

1. **Keep the bulbs on a dedicated, isolated IoT network** (separate VLAN or SSID).
   **What it does:** contains blast radius. An attacker who claims a bulb reaches only that segment,
   not your file server.
   **What it does not do:** close the window. The attack needs no Wi-Fi credentials, so network
   segmentation does not prevent the initial access — it limits the consequences. Worth doing
   regardless; this is defence in depth, not a patch.

2. **Remove the Matter QR / setup-code stickers from the bulbs after setup.**
   **What it does:** defends against a *different* and simpler attack — someone photographing a
   visible setup code and commissioning the bulb legitimately.
   **What it does not do:** address this finding, which explicitly requires **no code at all**.
   **Photograph and store the codes first** — you need them if you ever factory-reset the bulb, and
   the sticker is unreadable once the bulb is in a fixture.

3. **Claim the manufacturer channel yourself.**
   > **🚧 Reasoned hypothesis — unproven. This is not one of the paper's Matter findings.**
   >
   > The paper's *legacy* devices were safe precisely because their manufacturer channel was already
   > occupied. It is therefore plausible that onboarding a Matter unit through the **AiDot app**
   > occupies that channel and closes the window. **This was not tested on the Matter line**, by the
   > authors or by us. Treat it as a hypothesis worth investigating, not a mitigation you can rely
   > on.
   >
   > Note the trade-off if it *were* true: installing the vendor app to secure the Matter SKU costs
   > you the no-app, no-account property that made the Matter SKU attractive in the first place.

**General Matter hygiene, worth knowing regardless of vendor:** a commissioning window that stays
open is a class of bug, not a one-off. If your controller can list a device's fabrics, check
periodically that only the fabrics you expect are present.

---

## 9. The Matter SKU exists — this just isn't it

AiDot/Consciot sells an explicitly **Matter-certified** A19 that commissions **natively into Home
Assistant**: no app, no account, no cloud contact at any point, no keys to back up, and no
integration to keep alive. It is a strictly better outcome than everything described above, and it
costs about the same.

**These bulbs are not that SKU** — owner-confirmed from the packaging.

> ### ⚠️ Read [§8](#8-security--an-open-commissioning-window) before acting on this
> The Matter SKU is the variant that tested **vulnerable** to an open commissioning window in
> peer-reviewed research: an outsider within radio range, holding no code and no credentials, could
> claim the device without alerting the owner. It remains a defensible choice — the flaw is a
> firmware bug rather than a property of Matter, and AiDot's legacy line was unaffected — but the
> "simpler and safer" framing needs that asterisk. Decide knowingly.

If you are buying rather than already holding a six-pack, buy the Matter one instead. Look for
**"Matter-Certified" in the listing title** and, decisively, a **Matter logo plus an 11-digit setup
code (or QR) printed on the bulb and the box**. Candidate Matter SKUs seen in AiDot's catalogue
include **B0C4YDSSGQ** and **B0CGMDX8VJ** — but verify against the carton, not the listing, for the
reason described in [§1](#1-what-this-bulb-actually-is).

For an existing six-pack the calculus is less obvious: Path 1 reaches a genuinely local end state,
and returning working hardware has its own costs. The honest summary is that Path 1 is *good*, and
the Matter SKU is *better and simpler*.

---

## 10. Flashing — the last resort

Flashing to **ESPHome** is the only path with **zero** vendor involvement at any stage — no account,
no app, no keys. It is also **not recommended here**, for a concrete reason: **the silicon is
unidentified.**

- **There is no public teardown of any AiDot / Linkind / Consciot bulb.** Verified negative, not an
  assumption.
- There is therefore **no prior art**, no known-good pinout, and no confirmed procedure.
- It costs **six disassemblies and six soldering jobs** on unknown hardware — and UART is the only
  route, since there is no Tuya-style OTA exploit path for this vendor.

Two **conflicting leads** exist, and neither resolves it:

| Lead | Points to | Strength |
|---|---|---|
| FCC internal photos of an AiDot bulb filing show module pads labelled `NC · TX · RX · **CEN** · SL_2 · SL_1 · GND` | **`CEN` is Beken/Realtek nomenclature** — Espressif labels it `EN`. Suggests **Beken BK7231N** | module photo, but from a different filing than this SKU |
| The blakadder template database lists two **Linkind wall switches** on **ESP32-SOLO-1** | Suggests AiDot is an **Espressif** house | inference across product lines, not this bulb |

Note that even if it *is* a Beken part, **`tuya-cloudcutter` still does not apply** — cloudcutter is
keyed to the *vendor's* cloud activation handshake, not to the silicon, and Consciot appears nowhere
in its database. Beken silicon would mean **OpenBeken or ESPHome via LibreTiny, over UART**.

**If you attempt it anyway: scout one bulb first.** Open exactly one, identify the chip, dump the
flash before writing anything, and only then decide whether to do the other five.

> ### ⚠️ Mains safety — read before opening any bulb
> An A19 bulb's driver board sits directly on **mains potential** — there is no isolation
> transformer. The board can hold a **lethal charge in its bulk capacitor after it is unplugged**.
>
> - Never open a bulb that is connected to mains, and never probe a powered board.
> - Discharge the bulk capacitor before touching anything.
> - Use **3.3 V logic only** — 5 V will destroy the module.
> - A USB-serial adapter's 3V3 pin is often too weak to power a Wi-Fi module through boot; use a
>   proper external 3.3 V supply with a common ground.
>
> If you are not already comfortable working on non-isolated mains circuitry, do not start here.

---

## 11. Open questions

- [ ] 🚧 **Do the fork's cached credentials survive a Home Assistant restart with the WAN blocked?**
      Implied by its protocol documentation, not stated outright. **This is the load-bearing
      unverified claim in this document** — [§6](#6-proving-it-is-really-local) is the test.
- [ ] **What SoC is inside?** Unidentified. Two conflicting leads ([§10](#10-flashing--the-last-resort)),
      no public teardown. Only matters if flashing is ever attempted.
- [ ] **Does the fork expose full RGB on this model,** or only brightness + color temperature?
- [ ] **Can the `aesKey` be recovered from a flash dump?** Would remove the cloud from key issuance
      entirely — but requires UART, so it collapses into [§10](#10-flashing--the-last-resort) anyway.
- [ ] 🚧 **Does claiming the manufacturer channel close the Matter commissioning window?** The
      hypothesis in [§8](#8-security--an-open-commissioning-window) — that onboarding a Matter unit
      through the AiDot app occupies the channel that kept the legacy line safe. **Untested by the
      paper's authors and by us.** Only relevant to the Matter SKU, but it is the difference between
      "no mitigation exists" and "there is a workaround", so it is worth someone's afternoon.

---

## 12. Prior art & credits

**What makes the recommended path possible**

- **[sulibot/hass-AiDot](https://github.com/sulibot/hass-AiDot)** — the community fork this guide is
  built around. Its `protocol_documentation.md` is the best public description of the AiDot local
  protocol, and its cached-credential behaviour is what makes a no-cloud end state reachable at all.
- **[AiDot-Development-Team/hass-AiDot](https://github.com/AiDot-Development-Team/hass-AiDot)** — the
  upstream the fork derives from.
- **[Home Assistant `aidot` integration](https://www.home-assistant.io/integrations/aidot)** — the
  official built-in option. Easier; see [§3](#3-path-1--hass-aidot--recommended) for why it is not
  the recommendation here.

**Security research**

- **Shafqat & Ranganathan**, *"Seamlessly Insecure: Uncovering Outsider Access Risks in
  AiDot-Controlled Matter Devices"* — Northeastern University, **SafeThings 2024**. The source for
  [§8](#8-security--an-open-commissioning-window). Physical testing of AiDot Matter devices,
  including a Consciot bulb, with a three-month coordinated disclosure the vendor did not answer.
  Independent security work on budget IoT hardware is rare and thankless; this one is worth reading
  in full if you own anything on this platform.

**Investigated and *not* applicable**

- **[tuya-cloudcutter](https://github.com/tuya-cloudcutter/tuya-cloudcutter)** — excellent work,
  wrong vendor. Zero Consciot profiles in 1,149. Documented so the next person does not spend an
  evening rediscovering that.
- **[tuya-convert](https://github.com/ct-Open-Source/tuya-convert)** — deprecated upstream, and
  inapplicable for the same reason.
- **LocalTuya** — same. AiDot devices have no Tuya `local_key`.

**If you ever go down [§10](#10-flashing--the-last-resort)**

- **[ESPHome](https://esphome.io/)** and **[LibreTiny](https://github.com/libretiny-eu/libretiny)**
- **[OpenBeken](https://github.com/openshwprojects/OpenBK7231T_App)** — if the Beken lead is correct
- **[blakadder's device templates](https://templates.blakadder.com/)** — source of the Linkind
  ESP32-SOLO-1 lead

---

## Disclaimer

Independent interoperability research on hardware the author purchased. No affiliation with
Consciot, AiDot, Leedarson, Amazon, or Home Assistant.

Paths 1 through 8 involve no disassembly and no warranty impact. Opening a mains-powered bulb voids
its warranty and carries a real risk of electric shock and fire; [§10](#10-flashing--the-last-resort)
is entirely at your own risk.

## License

[MIT](LICENSE) © 2026 JP ([@jphein](https://github.com/jphein))
