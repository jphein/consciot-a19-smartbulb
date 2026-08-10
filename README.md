# Consciot A19 Color Bulb → Home Assistant, Fully Local

**Device:** Consciot A19 Smart Light Bulb · Amazon **B0G6YFQDFW** · 800 lm · 60 W-equivalent ·
RGB color-changing · E26 A19 · dimmable · 2.4 GHz Wi-Fi · sold as a 6-pack
**Box copy:** *"Works with Apple Home, Alexa, Google Home & SmartThings"*
**Goal:** all six bulbs in Home Assistant, **fully local** — no vendor cloud, no vendor app
dependency, no internet required to turn on a light.

> ### 🚧 Research in progress
> This document is written alongside an active teardown/identification effort. Anything not yet
> confirmed against the physical hardware is marked **🚧**. The headline recommendation below is
> an evidence-backed *hypothesis* with a 60-second confirmation test — run the test before you
> plan around it.

---

## TL;DR — the recommended path

**Commission the bulbs as Matter-over-Wi-Fi devices directly into Home Assistant.** No flashing,
no soldering, no vendor cloud account, no custom integration.

If the Matter identification holds (see §1), this device is *dramatically* easier to liberate
than the usual budget Wi-Fi bulb. There is no exploit to land, no OTA window to race, no UART
pads to solder. Matter is a local-by-design protocol: once a bulb is commissioned onto Home
Assistant's fabric, control never leaves your LAN, and the vendor app becomes optional — you can
delete it.

```
Bulb ──(Matter over Wi-Fi, IPv6, local)──> Matter Server add-on ──> Home Assistant
                                                                     └── light.* entity
   no cloud ·  no account · works with the WAN unplugged
```

**Confidence:** high on *"this is the Matter line"*, not yet **verified on the bulb in hand**.
Confirm with §1.2 before buying six more.

---

## Contents

- [1. What this bulb actually is](#1-what-this-bulb-actually-is)
- [2. Path 1 — Matter over Wi-Fi ✅ recommended](#2-path-1--matter-over-wi-fi--recommended)
- [3. Network prerequisites (the part that actually bites)](#3-network-prerequisites-the-part-that-actually-bites)
- [4. Doing all six](#4-doing-all-six)
- [5. What you get in Home Assistant](#5-what-you-get-in-home-assistant)
- [6. Proving it is really local](#6-proving-it-is-really-local)
- [7. Fallback paths if it is NOT Matter](#7-fallback-paths-if-it-is-not-matter)
- [8. Open questions](#8-open-questions)
- [9. Prior art & credits](#9-prior-art--credits)

---

## 1. What this bulb actually is

### 1.1 The evidence

**Consciot is an AiDot-platform brand, not (apparently) a Tuya rebadge.**
Consciot listings direct buyers to the **AiDot** app. AiDot is a smart-home brand family whose
siblings include **Linkind, Orein, and Winees**. That matters for expectations: the entire
Tuya-liberation toolchain everyone reaches for first — `tuya-cloudcutter`, `tuya-convert`,
LocalTuya — is keyed to Tuya's firmware and cloud, and

> **Consciot appears 0 times in the `tuya-cloudcutter` device database** — 1,149 device profiles,
> grepped locally, zero hits.

So the reflexive *"cheap Wi-Fi bulb = Tuya OEM"* assumption is **not supported** for this brand.
Plan around Matter, not around cloudcutter.

**Consciot ships two distinct product lines, and the ecosystem list on the box tells you which
one you are holding.** The tell is *Apple Home* and *SmartThings*:

| Line | Box says | Example ASINs |
|---|---|---|
| **Matter line** | "Matter-Certified" · Works with **Apple Home** / Siri / **SmartThings** | B0C4Y9L54Q, B0C4YDSSGQ, B0CB837NDQ, B0CBKJBLTF, B0CBMYZX3L |
| **Non-Matter line** | Works with Alexa & Google Home **only** | B0BYNFG5S4, B0C5M1FSQZ, B0CDC3SQSB |

**Our ASIN (B0G6YFQDFW) lists all four ecosystems, including Apple Home and SmartThings → it
matches the Matter line.**

The reasoning behind that inference is worth stating explicitly, because it is the load-bearing
step: **Apple Home support on a budget Wi-Fi bulb effectively requires Matter.** The only
pre-Matter way to speak to Apple Home was HomeKit-native (HAP over Wi-Fi), which required
per-device **MFi certification** — a licensing and hardware-attestation burden that a no-name ODM
selling six bulbs for the price of one Hue does not carry. Alexa and Google Home both have
cloud-to-cloud paths that any vendor can implement; Apple Home does not. So "Works with Apple
Home" on a non-hub, non-Thread Wi-Fi bulb is a strong Matter-over-Wi-Fi signal.

### 1.2 Confirm it in 60 seconds — do this first

Three independent checks, cheapest first. Any one of them settles it.

1. **Look for the Matter logo and setup code.** A Matter device *must* carry a commissioning
   payload. Check the bulb's plastic body, the box, and the paper insert for:
   - the Matter mark (three interlocking arrows forming a triangle), and
   - an **11-digit numeric setup code** (often printed as `1234-567-8901`) and/or a **QR code**
     whose payload begins with `MT:`.

   An 11-digit code beginning its QR payload with `MT:` is conclusive — that is a Matter onboarding
   payload and nothing else uses that format.

2. **Look for `_matterc._udp` on the network.** Power on a factory-fresh bulb and watch mDNS.
   A commissionable Matter device advertises `_matterc._udp`; a commissioned one advertises
   `_matter._tcp`.

   ```bash
   # Commissionable (not yet paired) Matter devices:
   avahi-browse -rt _matterc._udp
   # Already-commissioned Matter devices:
   avahi-browse -rt _matter._tcp
   ```

3. **Check the app's own words.** If the AiDot app offers "Add to Apple Home / SmartThings" or
   surfaces a *"Matter setup code"* / *"pairing mode"* screen, it is Matter.

> ### 📸 Photograph every setup code before you install the bulbs
> This is the single most valuable 30 seconds in this whole document. The Matter setup code is
> printed **on the bulb itself** — and becomes permanently unreadable the moment the bulb is
> screwed into a recessed can, a globe fixture, or anything face-up. Lay all six out, photograph
> every code, and store the photos somewhere you will still have them in two years. Losing the
> code does not brick the bulb, but re-commissioning it after a factory reset means taking the
> fixture apart.
>
> **Treat those photos as secrets.** A Matter setup code is a commissioning credential: anyone who
> has it and is in radio range of an uncommissioned bulb can join it to *their* fabric. Never
> commit them, never post them in a screenshot.

---

## 2. Path 1 — Matter over Wi-Fi ✅ recommended

### What you need

| | |
|---|---|
| **Home Assistant** | 2023.x or newer (any modern release). HAOS or Supervised is the easy road. |
| **Matter Server** | The **Matter Server** add-on (Settings → Add-ons → Add-on Store → *Matter Server*), plus the **Matter (BETA)** integration. On HAOS this is a two-click install. |
| **A phone with the HA Companion app** | Required. Commissioning is **Bluetooth-assisted** — the phone talks BLE to the bulb to hand over Wi-Fi credentials. There is no browser-only path. |
| **Bluetooth on the phone** | Just for the ~30 seconds of commissioning. Not needed afterwards. |
| **2.4 GHz Wi-Fi** | The bulb is 2.4 GHz-only. See §3. |
| **IPv6 on the LAN** | **Non-negotiable.** See §3 — this is the #1 cause of Matter failures. |

You do **not** need: a Thread border router (this is Wi-Fi Matter, not Thread), a hub, a bridge,
an AiDot account, or an internet connection.

### Step 1 — install the Matter server

Settings → Add-ons → Add-on Store → **Matter Server** → Install → Start (enable *Start on boot*
and *Watchdog*). Then Settings → Devices & Services → **Add Integration** → **Matter** → accept
the default (use the local add-on).

### Step 2 — factory-reset the bulb

A bulb fresh from the box is already commissionable. A bulb that has ever been paired to the
vendor app is not, and must be reset first.

**🚧 The exact reset gesture for this model is unconfirmed.** The near-universal convention for
Wi-Fi bulbs — and the AiDot family's documented method — is a **power cycle count**: switch the
bulb **on for ~1 second, off for ~1 second, repeated 5 times**, leaving it on the 5th. The bulb
confirms by **blinking or cycling color**. Some AiDot models use 3 cycles instead of 5. If 5 does
nothing, try 3.

Confirmation that it worked: the bulb starts advertising `_matterc._udp` (check 2 in §1.2).

### Step 3 — commission it into Home Assistant

Open the **Home Assistant Companion app** on your phone (not the browser), then:

> Settings → Devices & Services → **Add Integration** → **Matter** → **Add Matter device**
> → scan the QR code (or tap *"I don't have a QR code"* and type the 11-digit setup code)

The phone does the rest: BLE handshake → hands the bulb your Wi-Fi credentials → the bulb joins
2.4 GHz → HA's Matter fabric adopts it → a `light.*` entity appears. Typically 30–90 seconds.

**Platform notes:**

- **Android** — commissioning runs through Google Play Services' Matter module. The Google Home
  app may need to be installed (not necessarily used) for that module to be present. Android will
  often show its own Google-branded pairing sheet mid-flow; that is expected and does **not** mean
  the bulb is being joined to Google's cloud.
- **iOS** — the HA Companion app can commission directly. Alternatively, pair to **Apple Home**
  first, then share to HA via Matter **multi-admin**: in the Home app, open the accessory →
  Settings → *Turn On Pairing Mode* → Apple generates a **new, one-time setup code** → type that
  into HA. Both approaches end at the same place.

### Step 4 — delete the vendor app

Once the bulb is on HA's fabric, the AiDot app is dead weight. Matter devices do not need it, and
nothing in HA's control path traverses it. Uninstalling the app does not un-commission the bulb.

> **Multi-admin, and why you might keep a second controller:** Matter devices support a limited
> number of simultaneous fabrics — commonly **5**. Each ecosystem you add (HA, Apple Home, Alexa,
> Google, SmartThings) consumes one slot. For an all-local setup, use exactly one: Home Assistant.
> If you want Siri too, add Apple Home as a second and stop there.

---

## 3. Network prerequisites (the part that actually bites)

Matter commissioning failures are almost never the bulb. They are almost always one of these
three, in this order of frequency.

### 3.1 IPv6 is mandatory — this is the #1 failure cause

**Matter's operational transport is IPv6-only.** There is no IPv4 fallback. If your LAN has IPv6
disabled — a very common "hardening" choice on IoT segments — commissioning will appear to
succeed and then the device will be permanently unreachable, or it will fail at the final step
with an unhelpful timeout.

What must be true:

- IPv6 enabled on the network segment the bulb lands on. **Link-local (`fe80::/10`) is sufficient**
  — you do not need a global prefix, ULA, or any ISP delegation.
- **Router Advertisements (RA) reaching that segment**, so devices configure themselves.
- **MLD snooping** either working correctly or switched off. Broken MLD snooping silently eats the
  IPv6 multicast that Matter's mDNS depends on, and is a genuinely nasty failure mode because
  everything else on the network looks fine.

### 3.2 mDNS must reach Home Assistant

Matter discovery is mDNS (`_matterc._udp` before commissioning, `_matter._tcp` after). HA's Matter
server must be able to see those advertisements.

- **Simplest, most reliable:** put the bulbs on the **same L2 segment / VLAN** as Home Assistant.
- **If your IoT devices live on a separate VLAN** (a good practice, and worth keeping): you need an
  **mDNS reflector / Avahi repeater** bridging the HA segment and the IoT segment, **for IPv6 as
  well as IPv4**, plus firewall rules permitting the Matter operational traffic between them. Many
  mDNS reflectors default to IPv4-only — which reflects just enough for the device to be
  *discovered* and not enough for it to *work*.
- **Host networking:** the Matter Server add-on needs host-level network access to see multicast.
  The stock HAOS add-on is configured correctly out of the box; hand-rolled Docker setups are the
  ones that break here.

> **The honest recommendation:** if you run a segmented network, commission the bulbs on the same
> VLAN as HA and *then* decide whether moving them is worth the reflector debugging. Commissioning
> across VLANs is the hardest version of this task, and it is optional.

### 3.3 2.4 GHz band steering

The bulb is 2.4 GHz-only. If your SSID is a single band-steered name covering 2.4 and 5 GHz, the
credential handoff can succeed while the join fails, because the bulb is handed an SSID it then
cannot find on a band it can hear.

Fixes, in order of preference:

1. Use a **dedicated 2.4 GHz SSID** (an IoT SSID is the clean answer).
2. Temporarily disable the 5 GHz radio for the duration of commissioning, then re-enable it.
3. Move the phone and bulb close to the AP so 2.4 GHz is the strongest candidate.

---

## 4. Doing all six

Six bulbs is six commissioning runs — there is no bulk-import path. What makes it painless:

1. **Do them all on a bench first, before installing.** One lamp, or a bare socket adapter. Screw
   in bulb → photograph the code → commission → rename in HA → unscrew → next. All six in ~15
   minutes, all with the codes still readable.
2. **Rename each entity as you go**, while you still know which physical bulb it is. After they are
   in fixtures, `light.consciot_a19_4` tells you nothing. Name them for where they are going —
   `light.kitchen_can_1` — not for what they are.
3. **Label the bulbs physically.** A marker dot on the base matching the HA name saves a real
   diagnostic afternoon later.
4. **Group them once they are up:**

```yaml
# configuration.yaml — one switch, six bulbs
light:
  - platform: group
    name: Kitchen Cans
    entities:
      - light.kitchen_can_1
      - light.kitchen_can_2
      - light.kitchen_can_3
```

> **Sending one command to six bulbs is six unicast messages.** Matter over Wi-Fi has no broadcast
> group primitive in this path, so a group turn-on is inherently a little staggered. It is usually
> imperceptible; on a slow or congested 2.4 GHz band it can become a visible ripple. If that
> bothers you, the fix is RF conditions (AP placement, channel width, fewer competing devices) —
> not Home Assistant configuration.

---

## 5. What you get in Home Assistant

🚧 **Unverified against this hardware** — this is the Matter Color Temperature Light device-type
baseline, which is what an RGB+tunable bulb of this class conventionally implements. To be
replaced with a verified capability table.

| Capability | Expected | Notes |
|---|---|---|
| On / off | ✅ | Matter On/Off cluster |
| Brightness | ✅ | Level Control cluster, 0–254 mapped to HA's 0–255 |
| RGB color | ✅ | Color Control cluster — advertised as color-changing |
| Color temperature | 🚧 | Likely, in mireds; depends on whether the bulb is RGB-only or RGBTW |
| Transitions | ✅ | `transition:` supported by the Level Control cluster |
| Vendor "scenes" / effects | ❌ | App-side effects are usually vendor-proprietary and do **not** cross the Matter boundary. Rebuild them as HA scripts. |
| Power / energy metering | ❌ | Not present on bulbs in this class |
| Firmware update from HA | 🚧 | Matter OTA Requestor is optional for vendors; may or may not be implemented |

**The effects trade-off is worth naming up front:** going Matter-local usually means giving up the
vendor app's canned effects (candle flicker, music sync, rainbow fade). What you get back is that
the light works when the internet doesn't, responds in milliseconds instead of via a round-trip to
someone's cloud, and cannot be deprecated out from under you. Rebuilding a candle flicker as an HA
script is an afternoon; getting an abandoned cloud bulb back is not possible at all.

---

## 6. Proving it is really local

Do not take "it's Matter, so it's local" on faith — verify it, once:

1. **Block the bulbs at the firewall.** Deny the bulbs' addresses all WAN egress.
2. **Toggle from HA.** It should work, instantly and unchanged.
3. **Harder version — pull the internet entirely.** Unplug the WAN. HA → bulb must still work. If
   it does, the control path is genuinely local end to end.
4. **Watch what they phone.** Log outbound connection attempts for a day. A Matter bulb on a local
   fabric should be near-silent — NTP and possibly a DNS lookup or an OTA check. Anything
   resembling a persistent TLS session to a vendor endpoint is worth investigating.

Once verified, leave the WAN block in place permanently. There is no feature on the far side of it
that you want.

---

## 7. Fallback paths if it is NOT Matter

If §1.2 comes back negative — no `MT:` payload, no `_matterc._udp`, Alexa/Google only — then this
is the non-Matter Consciot line and the job gets substantially harder. Ranked by effort:

| Path | Viability | Notes |
|---|---|---|
| **Matter, via a newer revision** | — | Check whether the exact ASIN shipped a revised, Matter-certified SKU. Returning a non-Matter 6-pack and buying the Matter one is *far* cheaper than any path below. |
| **LocalTuya / `tuya-local`** | ⚠️ Unlikely | Requires the device to actually be Tuya underneath. Current evidence says no (§1.1). Would need local key extraction. |
| **`tuya-cloudcutter`** | ❌ Ruled out (provisionally) | **Zero** Consciot profiles in the device DB. Cloudcutter is vendor-keyed, not silicon-keyed — the right chip is not sufficient. |
| **`tuya-convert`** | ❌ | Deprecated upstream, and inapplicable for the same vendor reason. |
| **ESPHome / OpenBK via OTA** | 🚧 Unknown | Depends entirely on the silicon and whether an unauthenticated OTA path exists. **Pending research file `02-ota-path.md`.** |
| **ESPHome / OpenBK via UART** | 🚧 Unknown | Always works eventually, costs an afternoon and a soldering iron per bulb — ×6. **Pending research file `03-uart-flash.md`.** |

> ### ⚠️ Mains safety
> Every path below the Matter line involves opening a bulb. An A19 bulb's driver board sits
> directly on **mains potential** — there is no isolation transformer. The board can hold a lethal
> charge in its bulk capacitor **after** it is unplugged. Never open a bulb that is connected to
> mains, never probe a powered board, and discharge the bulk cap before touching anything. If you
> are not already comfortable working on non-isolated mains circuitry, the correct move is to
> return the bulbs and buy the Matter SKU.

---

## 8. Open questions

Tracked here, resolved as research lands.

- [ ] **Is B0G6YFQDFW Matter-certified?** Inferred from the four-ecosystem box copy; needs the
      physical `MT:` payload or a CSA certification-database hit. *(§1.2 settles it.)*
- [ ] **What silicon is inside?** Unknown. Determines every fallback path. — `01-chip-id.md` 🚧
- [ ] **Is there an unauthenticated OTA path?** — `02-ota-path.md` 🚧
- [ ] **UART pad locations / flash procedure?** — `03-uart-flash.md` 🚧
- [ ] **Verified HA capability surface** — does it expose color temperature, or RGB only?
- [ ] **Factory-reset gesture** — 5 power cycles or 3?
- [ ] **Does it implement Matter OTA?** Affects whether firmware can be updated without the vendor app.

---

## 9. Prior art & credits

**What makes the recommended path possible**

- **[Home Assistant](https://www.home-assistant.io/) Matter integration** and the
  [Python Matter Server](https://github.com/home-assistant-libs/python-matter-server) — the local
  fabric controller doing the actual work here.
- **[Connectivity Standards Alliance](https://csa-iot.org/)** — Matter itself. A budget bulb that
  can be adopted by any controller, with no vendor cloud in the path, is the entire point of the
  standard, and it is genuinely delivering on it.
- **[project-chip/connectedhomeip](https://github.com/project-chip/connectedhomeip)** — the
  reference SDK, and the source of the `chip-tool` diagnostics worth knowing about.

**Context projects — investigated, and *not* applicable here**

- **[tuya-cloudcutter](https://github.com/tuya-cloudcutter/tuya-cloudcutter)** — brilliant work,
  wrong vendor. Zero Consciot profiles. Listed so the next person does not spend an evening
  discovering that independently.
- **[tuya-convert](https://github.com/ct-Open-Source/tuya-convert)** — deprecated upstream, and
  inapplicable for the same reason.
- **[ESPHome](https://esphome.io/) / [OpenBeken](https://github.com/openshwprojects/OpenBK7231T_App)**
  — the destination if this turns out to be the non-Matter line and a flash path is needed.

**Research notes** — the working notes behind this document (chip ID, OTA, UART, HA end-state) are
kept locally and synthesized here rather than published raw, because they contain network detail
specific to the author's lab.

---

## Disclaimer

This documents independent interoperability research on hardware the author purchased. No
affiliation with Consciot, AiDot, Amazon, or the Connectivity Standards Alliance.

Opening a mains-powered bulb voids its warranty and carries a real risk of electric shock and
fire. Everything past §7 is at your own risk. The recommended path (§2) involves no disassembly
and no warranty impact.

## License

[MIT](LICENSE) © 2026 JP ([@jphein](https://github.com/jphein))
