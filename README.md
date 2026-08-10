# Consciot A19 Color Bulb → Home Assistant, Fully Local

**Device:** Consciot A19 Smart Light Bulb · Amazon **B0G6YFQDFW** · 800 lm · 60 W-equivalent ·
RGB color-changing · E26 A19 · dimmable · 2.4 GHz Wi-Fi · sold as a 6-pack
**Box copy:** *"Works with Apple Home, Alexa, Google Home & SmartThings"*
**Goal:** all six bulbs in Home Assistant, **fully local** — no vendor cloud, no vendor app, no
internet required to turn on a light.

---

## TL;DR — commission them as Matter devices. That's it.

**This bulb is Matter-certified.** Home Assistant speaks Matter natively and locally. There is no
exploit to land, no OTA window to race, no UART pads to solder, no vendor account to create.

> **Do not flash this bulb.** The recommendation *inverts* relative to the usual cheap-Wi-Fi-bulb
> project: flashing a Matter device is actively destructive. See [§9](#9-flashing--ruled-out).

```
Bulb ──(Matter over Wi-Fi · local IPv6)──> Matter Server add-on ──> Home Assistant
                                                                     └── light.* entity
   no cloud · no account · no vendor app · works with the WAN unplugged
```

**Primary-source proof** — CSA certified-products database, *"Consciot Smart Light Bulb"*:

| Field | Value |
|---|---|
| Company | **AiDot Inc.** |
| Vendor ID (VID) | **`0x1396`** |
| Product ID (PID) | **`0x11BA`** |
| Certification ID | **CSA2609OMAT49756-24** |
| Certified | **2026-01-30** |
| Matter spec | **1.5** |
| Transport | **Wi-Fi + Bluetooth** (BLE carries commissioning) |
| Device type | **Extended Color Light** (`0x010D`) |
| Family SKU / variant | `LS0102603211A` / `CS01271101` |

Corroboration: AiDot holds **136 Matter 1.5 certifications** for smart lighting. Consciot, Linkind
and OREiN are all AiDot brands, and all three have Matter bulb entries in the CSA database.

**One open item, and it is the only thing that changes the recommendation:** Consciot ships two
parallel SKU lines, and this exact ASIN is new enough that its listing could not be read directly.
[§2](#2--which-sku-do-you-have) has three tests that settle it in under a minute.

---

## Contents

- [1. Why we know it's Matter](#1-why-we-know-its-matter)
- [2. 🚧 Which SKU do you have?](#2--which-sku-do-you-have)
- [3. Four myths that send people the wrong way](#3-four-myths-that-send-people-the-wrong-way)
- [4. Path A — Matter commissioning ✅ recommended](#4-path-a--matter-commissioning--recommended)
- [5. Network prerequisites (the part that actually bites)](#5-network-prerequisites-the-part-that-actually-bites)
- [6. Doing all six](#6-doing-all-six)
- [7. What you get in Home Assistant](#7-what-you-get-in-home-assistant)
- [8. Path B — if there is no Matter code](#8-path-b--if-there-is-no-matter-code)
- [9. Flashing — ruled out](#9-flashing--ruled-out)
- [10. Open questions](#10-open-questions)
- [11. Prior art & credits](#11-prior-art--credits)

---

## 1. Why we know it's Matter

**The CSA certificate above is the primary source** — not an inference, not a listing claim. A
Matter certification is issued per product, carries a vendor ID assigned to a real company, and is
publicly queryable. AiDot Inc. holds VID `0x1396` in its own name.

**The manufacturing chain is a tier-1 ODM, not a white-label shop.** The Consciot A19 manual names
**Leedarson IoT Technology Inc.** (Xiamen) as producer — a tier-1 lighting ODM that builds for
major brands (FCC grantee codes `2AB2Q`, `2AVZB`). AiDot's own FCC grantee code is `2BLWS`.

**It is definitively not Tuya**, which matters because the entire toolchain most people reach for
first — `tuya-cloudcutter`, `tuya-convert`, LocalTuya — is keyed to Tuya's firmware and cloud:

- **Zero hits for "Consciot"** across all **1,149 device profiles** in the `tuya-cloudcutter`
  device database.
- AiDot holds its **own CSA Vendor ID** and ships its **own app**. A Tuya OEM would appear under
  Tuya's VID and the Smart Life app.
- ⇒ `tuya-convert` and `tuya-cloudcutter` **do not apply**, and a Tuya `local_key` is something an
  AiDot device has no way to possess.

**Why the box copy is corroborating evidence:** "Works with Apple Home" on a budget Wi-Fi bulb
effectively requires Matter. The only pre-Matter route to Apple Home was HomeKit-native (HAP over
Wi-Fi), which required per-device **MFi certification** — a licensing and hardware-attestation
burden a no-name ODM selling six bulbs for the price of one Hue does not carry. Alexa and Google
both have cloud-to-cloud paths any vendor can implement; Apple Home does not. "**& SmartThings**"
is the same tell, and in AiDot's catalogue that phrase appears only on Matter SKUs.

---

## 2. 🚧 Which SKU do you have?

**Status: owner confirming.** Consciot ships a Matter line *and* a legacy non-Matter Wi-Fi line.
The CSA record proves *a* Consciot A19 is Matter-certified; confirming that **your** box is that
SKU takes under a minute. Three independent tests, any one of which settles it.

### Test 1 — the Matter setup code (easiest, needs nothing)

Look on the **bulb itself** (usually printed on the plastic diffuser skirt near the base) and on
the box for:

- the **Matter logo** — three interlocking arrows forming a triangle
- a **QR code**, and/or an **11-digit numeric setup code** formatted `1234-567-8901`

**Present → it is Matter. Done.** No teardown, no chip ID, nothing else needed. A non-Matter AiDot
bulb has no such code. If the model number on the box resembles `LS0102603211A` / `CS01271101`,
that is further confirmation.

### Test 2 — a BLE scan (decisive, works without the box)

A Matter device in commissioning mode advertises over BLE with **service UUID `0xFFF6`**, and the
payload encodes the discriminator, **Vendor ID and Product ID**. This discriminates every remaining
hypothesis at once:

```bash
sudo btmgmt find -l                  # LE scan — look for UUID FFF6 in the AD data
# or
bluetoothctl --timeout 20 scan le    # then: bluetoothctl info <address>
```

| Scan result | Verdict |
|---|---|
| Advert with **UUID `0xFFF6`** | **Matter.** The payload's VID should read **`0x1396` = AiDot**, confirming the SKU too |
| Advert with **Tuya manufacturer data**, no `0xFFF6` | Tuya BLE-assisted → not Matter (and not expected here) |
| **No BLE advertising at all** | Legacy Wi-Fi SmartConfig bulb → not Matter → [§8](#8-path-b--if-there-is-no-matter-code) |

> ⏱️ **Power-cycle the bulb immediately before scanning.** Many implementations advertise only
> during a ~15-minute commissioning window after power-up; a bulb that has been powered for hours
> may have gone quiet. Any phone BLE scanner (nRF Connect, LightBlue) works equally well.

### Test 3 — ask Apple Home (zero setup)

Open **Apple Home** → *Add Accessory* → **Matter**. If the bulb appears, it is Matter — Apple Home
is the one ecosystem in the packaging list that a non-Matter budget bulb cannot possibly join.

**Path selector:** code/`0xFFF6`/Apple Home present → **[Path A](#4-path-a--matter-commissioning--recommended)**.
Definitively absent → **[Path B](#8-path-b--if-there-is-no-matter-code)**.

---

## 3. Four myths that send people the wrong way

Each of these has sent someone down a dead end on this exact device.

| Myth | Reality |
|---|---|
| *"It works with the AiDot app, so it isn't Matter."* | **False.** AiDot's Matter bulbs work with the AiDot app *too*. A vendor app is not evidence against Matter — and AiDot Inc. is the company on the Matter certificate. |
| *"It's a Wi-Fi bulb, so it isn't Matter."* | **False.** Matter runs **over** Wi-Fi. Matter-over-Wi-Fi and Matter-over-Thread are both Matter; this is the Wi-Fi kind. |
| *"It broadcasts no setup Wi-Fi network, so it's a Tuya SmartConfig bulb."* | **Backwards.** **Matter devices never broadcast a SoftAP** — commissioning happens over BLE, then the device is handed Wi-Fi credentials. No AP is *consistent with* Matter. It rules out Tuya **AP mode** specifically, and nothing else. |
| *"Cheap Wi-Fi bulb ⇒ Tuya ⇒ use cloudcutter."* | **False here.** Zero Consciot profiles in 1,149. Wrong vendor entirely — see [§1](#1-why-we-know-its-matter). |

---

## 4. Path A — Matter commissioning ✅ recommended

### What you need

| | |
|---|---|
| **Home Assistant** | Any modern release. HAOS or Supervised is the easy road. |
| **Matter Server** | The **Matter Server** add-on (Settings → Add-ons → Add-on Store), plus the **Matter** integration. Two clicks on HAOS. |
| **A way to reach the bulb over BLE** | Either an **existing ESPHome/Shelly BLE proxy** (best — see below) or a phone with the HA Companion app. |
| **2.4 GHz Wi-Fi** | The bulb is 2.4 GHz-only. See [§5](#5-network-prerequisites-the-part-that-actually-bites). |
| **IPv6 on the LAN** | **Non-negotiable.** See §5 — the #1 cause of Matter failures. |

You do **not** need: a Thread border router (this is Wi-Fi Matter), a hub, a bridge, an AiDot
account, the vendor app, or an internet connection.

### ⭐ The good option: phone-free commissioning via BLE proxy

**Matter Server add-on ≥ 8.5.0 can commission through Home Assistant's own Bluetooth stack**,
including **ESPHome and Shelly BLE proxies**. If you already run BLE proxies for Bluetooth sensors,
you have everything you need — and for six identical bulbs this turns six phone dances into six
paste-a-code-in-the-UI operations.

1. **Settings → Add-ons → Matter Server → Configuration** → enable **`ble_proxy`**
   ("Enable BLE proxy"). Leave `beta` off unless the toggle is missing. **Take a backup first** —
   9.x migrates its data store on first start.
2. Restart the add-on.

> Note: **BLE-proxy mode and a local Bluetooth adapter are mutually exclusive.** If HA has a USB
> Bluetooth dongle configured, the proxy path takes precedence anyway.

### Commission bulb #1

1. Screw in **one** bulb, powered on, **within BLE range of a proxy**. Factory-fresh bulbs enter
   pairing mode automatically.
2. **Settings → Devices & Services → Matter → Add device.**
3. Choose **"No, it's new."**
4. Enter the **11-digit setup code** (or scan the QR). HA will ask for the **Wi-Fi SSID and
   password** to hand the bulb over BLE.
   > ⚠️ **This is the step that decides which network the bulb lands on.** If you run a separate
   > IoT network, give it *that* SSID. Getting this wrong is the main way to end up with a bulb on
   > the wrong segment and an unexplained "commissioned but offline" bulb.
5. Wait — commissioning takes a couple of minutes.
6. Name it and finish.

### 🛑 Verify bulb #1 before doing the other five

Do not commission all six and *then* discover a problem. Confirm:

- The `light.*` entity appears and responds to on/off, brightness, **and color**.
- The bulb picked up an address on the network segment you intended.
- **It survives a power-cycle plus five minutes and comes back online by itself.**

That last one is the real test, and it is easy to skip. Commissioning succeeding only proves the
BLE path worked; **coming back after a power-cycle is what proves mDNS and IPv6 discovery work on
that segment.** A bulb that commissions and then never returns is the single most common Matter
failure, and you would much rather find it on bulb one than bulb six.

### If BLE proxy commissioning misbehaves

**Phone flow:** HA Companion app → Settings → Matter → Add device → "No, it's new." Requires
Android 8.1+ (12+ recommended, Location set to "Allow all the time") or iOS 16+. **The phone must
be joined to the target 2.4 GHz network during commissioning** — Android's commissioner hands the
device the phone's *current* Wi-Fi credentials. Move the phone back afterwards.

**If HA can't do BLE at all — the network-commissioning trick:** commission into **Apple Home**
first (iPhone scans the QR; the phone must be on the target network), then in Apple Home use
**Share / Add to other ecosystem** to generate a fresh setup code. In HA choose **"Yes, it's
already in use."** HA then commissions **over the network** — no BLE needed at all, because the
bulb is already on Wi-Fi. Matter's multi-fabric support means the bulb lives in both ecosystems
simultaneously, and **it stays fully local in HA either way.**

> **Fabric budget:** Matter devices support a limited number of simultaneous fabrics — commonly
> **5**. Each ecosystem you add consumes one. For an all-local setup, use exactly one: Home
> Assistant. If you want Siri too, add Apple Home as a second and stop there.

---

## 5. Network prerequisites (the part that actually bites)

Matter commissioning failures are almost never the bulb. They are almost always one of these three.

### 5.1 IPv6 is mandatory — the #1 failure cause

**Matter's operational transport is IPv6-only.** There is no IPv4 fallback. If IPv6 is disabled on
the segment — a very common "hardening" choice on IoT networks — commissioning can appear to
succeed and the device is then permanently unreachable.

- **Link-local (`fe80::/10`) is sufficient** when commissioner and device share an L2 segment. You
  do not need a global prefix, ULA, or ISP delegation.
- **Router Advertisements** should reach the segment.
- **MLD snooping** must either work correctly or be switched off. Broken MLD snooping silently eats
  the IPv6 multicast that Matter's mDNS depends on — a genuinely nasty failure mode, because
  everything else on the network looks fine.

### 5.2 mDNS must reach Home Assistant

Discovery is mDNS: `_matterc._udp` before commissioning, `_matter._tcp` after.

```bash
avahi-browse -rt _matterc._udp    # commissionable (not yet paired)
avahi-browse -rt _matter._tcp     # already commissioned
```

- **Simplest and most reliable:** put the bulbs on the **same L2 segment as Home Assistant**. If
  your HA host is multi-homed with a real NIC on the IoT segment, you already satisfy this — no
  mDNS reflector, no IPv6 ULA plumbing, no firewall holes.
- **Separate IoT VLAN, HA not present on it:** you need an **mDNS reflector / Avahi repeater**
  bridging both segments **for IPv6 as well as IPv4**, plus firewall rules for Matter operational
  traffic. Many reflectors default to IPv4-only — which reflects just enough for the device to be
  *discovered* and not enough for it to *work*.
- **Host networking:** the Matter Server container needs host network mode to see multicast. The
  stock HAOS add-on is correct out of the box; hand-rolled Docker setups are what break here.
- **On the AP:** check **multicast / IGMP-MLD snooping** and **client isolation** on the IoT SSID.
  Aggressive isolation can drop the multicast Matter needs.

> **Interface selection on multi-NIC hosts:** older guidance about a `--primary-interface` flag is
> from the python-matter-server era. Add-on 9.x is the matter.js rewrite, which normally binds
> **all** interfaces — which is what you want. **Do not set it speculatively.** If, and only if,
> bulbs commission but then show offline, that is the knob to investigate.

### 5.3 2.4 GHz band steering

The bulb is 2.4 GHz-only. (The CSA family entry confusingly says "dual-band 2.4G and 5G"; the
product listings say 2.4 GHz.) If your SSID is a single band-steered name, the credential handoff
can succeed while the join fails — the bulb is handed an SSID it cannot find on a band it can hear.

1. Use a **dedicated 2.4 GHz SSID** (an IoT SSID is the clean answer).
2. Or temporarily disable the 5 GHz radio during commissioning.
3. Or move phone and bulb close to the AP.

---

## 6. Doing all six

There is no bulk-commission mechanism in Matter — each bulb needs its own code, so it is six runs
at roughly 2–3 minutes each.

1. **Do them on a bench first, before installing.** One lamp or a bare socket adapter. Screw in →
   photograph the code → commission → rename → unscrew → next.
2. **Rename each entity as you go**, while you still know which physical bulb it is. Name them for
   *where they are going* — `light.kitchen_can_1` — not for what they are.
3. **Label the bulbs physically.** A marker dot on the base matching the HA name saves a real
   diagnostic afternoon later.
4. **Group them:**

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

> ### 📸 Photograph every setup code before you install
> The Matter setup code is printed **on the bulb itself**, and becomes permanently unreadable the
> moment it is screwed into a recessed can or a globe fixture. *"If you reset your device you'll
> need the QR code or numeric setup code to commission that device again."* Losing it does not
> brick the bulb, but re-commissioning means taking the fixture apart.
>
> **Treat those photos as secrets.** A setup code is a commissioning credential: anyone with the
> code, in radio range of an uncommissioned bulb, can join it to *their* fabric. Never commit them,
> never post them in a screenshot.

**Sending one command to six bulbs is six unicast messages.** Matter over Wi-Fi has no broadcast
group primitive here, so a group turn-on is inherently a little staggered — usually imperceptible,
occasionally a visible ripple on a congested 2.4 GHz band. The fix is RF conditions, not HA config.

---

## 7. What you get in Home Assistant

Device type `0x010D` **Extended Color Light** — the exact type that maps to brightness + RGB +
color temperature — yields one `light.*` entity per bulb:

| Capability | Exposed as |
|---|---|
| On / off | `light.turn_on` / `light.turn_off` |
| Brightness | `brightness` (0–255); `supported_color_modes` includes `hs`/`xy` |
| Full RGB color | `rgb_color` / `hs_color` / `xy_color` |
| Tunable white | `color_temp_kelvin`, ~**2700 K – 6500 K** |
| Transitions | `transition`, per the Matter Level Control cluster |
| Firmware updates | Possibly an `update.*` entity — Matter 1.5 with DCL enabled can surface OTA |

Plus a device entry showing vendor **AiDot Inc.**, model, serial and firmware version. Commissioning
one bulb and reading `0x1396` on its device page verifies identity *and* proves the end state
works, in a single step.

**No cloud. No account. No vendor app. No internet dependency.** Matter operational traffic is
local IPv6 between Home Assistant and the bulbs.

**What you give up versus the vendor app:** music-sync / microphone reactivity and vendor "scenes"
are not Matter clusters, so they will not appear in HA. What you get back is a light that works
when the internet doesn't, responds in milliseconds instead of via a round-trip to someone's cloud,
and cannot be deprecated out from under you. Rebuilding a candle flicker as an HA script is an
afternoon; recovering an abandoned cloud bulb is not possible at all.

### Proving it is really local

Verify once, then stop worrying:

1. **Block the bulbs at the firewall** — deny them all WAN egress.
2. **Toggle from HA.** Should work, instantly and unchanged.
3. **Harder version:** unplug the WAN entirely. HA → bulb must still work.
4. **Watch what they phone.** A Matter bulb on a local fabric should be near-silent.

Then leave the block in place permanently. There is no feature on the far side of it that you want.

---

## 8. Path B — if there is no Matter code

**Only if [§2](#2--which-sku-do-you-have) comes back definitively negative** — no setup code, no
`0xFFF6` advert, and Apple Home refuses it. That means the legacy AiDot Wi-Fi SKU.

**Do not reach for LocalTuya.** It is the tempting wrong turn, especially if you already have a
`localtuya` install. Consciot is AiDot, not Tuya; these devices do not speak the Tuya local
protocol and will not yield to Tuya local-key extraction.

### There is no zero-cloud option on this branch — be clear-eyed about it

The vendor is required **twice**, and both halves are currently unavoidable:

| Half | What it does | Community replacement? |
|---|---|---|
| **Provisioning** | The AiDot app pushes Wi-Fi credentials to a factory-fresh bulb | ❌ none exists |
| **Key issuance** | The AiDot cloud issues the per-device `deviceId` + `password` + **`aesKey`** | ❌ none exists |

There is **no "AiDotTools" analogue** to the reverse-engineered tooling that exists for some other
vendors. Nobody has reverse-engineered AiDot *provisioning*, and no library derives the local
`aesKey` independently of the cloud. Because provisioning is BLE-assisted rather than a SoftAP HTTP
flow, it is a substantially harder reverse-engineering target — which is likely why no such tool
exists, and a reason not to expect one soon.

### Two integrations, and they differ in a way that matters

Both require an AiDot account and one-time onboarding in the AiDot app. After that they diverge:

| | Official **`aidot`** (HA core, 2026.6+) | Community **`sulibot/hass-AiDot`** (HACS) |
|---|---|---|
| Transport | Persistent **TCP** connection per device | UDP discovery + AES over **TCP 10000** |
| **Cloud after setup** | **Checks the cloud every 6 hours, permanently** | Cloud in Phase 1 (key harvest) only |
| Install | Built in — easiest | HACS |
| Devices | A19, BR30 | Lights (brightness, color temp), switches |
| Quality tier | Bronze | community |

**The official integration is easier; the community fork has better longevity.** That 6-hourly
cloud check is exactly the dependency that turns into a brick when a vendor shuts down its
servers. The fork's architecture is cloud-once-then-local. Day-to-day *control* is local in both
cases — the cloud is not in the command path either way.

> ⚠️ **Do not take either project's marketing on faith.** The fork's README claims "no cloud
> dependency for device control" but does not explicitly state that credentials survive a restart.
> **Test it:** firewall the bulbs *and* HA from the internet, restart HA, and confirm control still
> works. That is the falsifiable version of "cloud-once."

### 🔴 If you land here, back up the keys the same day

The `deviceId` / `password` / **`aesKey`** triplet is issued **only by AiDot's cloud**, and it is
the sole thing that keeps these bulbs controllable if AiDot ever goes away. **Harvest and back up
those credentials for all six bulbs immediately after onboarding**, stored outside HA's config
entry.

This is the lesson of every dead-cloud bulb project, applied one device *earlier*. When a vendor
dies, its keys and onboarding die with it, and recovery becomes a community reverse-engineering
effort — if it happens at all. Here the equivalent secrets are obtainable **right now, while the
vendor is alive**, and only now. Backing them up converts a permanent vendor dependency into a
one-time errand.

**Practical notes:** use a throwaway AiDot account — the app is unavoidable, your real identity is
not. Give each bulb a **DHCP reservation**, since the integration maps by IP and manual-IP mode
needs statics anyway. UDP broadcast discovery does not cross subnets, so if HA is not on the same
segment as the bulbs, expect to configure IPs manually.

**Honest bottom line:** Path B does not meet "fully local" as strictly as Matter does. If your
bulbs turn out to be non-Matter and you want true zero-cloud, the best move is almost certainly to
**return them and buy the explicitly Matter-labelled Consciot SKU** (e.g. B0C4YDSSGQ, B0CGMDX8VJ),
which reaches the ideal end state for the same money.

---

## 9. Flashing — ruled out

**On the Matter branch, flashing is not a fallback. It is destruction.**

Each Matter unit is factory-provisioned with a unique **DAC (Device Attestation Certificate)** and
operational keys in protected flash. Overwriting the firmware **destroys the DAC irrecoverably** —
no rebuild restores it, and the bulb can never rejoin *any* Matter fabric again. You would be
trading a fully-local, standards-based, multi-ecosystem bulb for a strictly worse one, to solve a
problem the bulb does not have. Matter devices also commonly ship with secure boot and flash
encryption enabled, so it frequently isn't even possible.

**On the non-Matter branch** (Path B), flashing is the only true zero-cloud route — but there is
**no public teardown of any AiDot / Linkind / Consciot bulb**, so the SoC is unidentified and there
is no prior art to lean on. It costs six disassemblies and six soldering jobs on unknown silicon.
Not recommended; if you attempt it anyway, do **one** bulb as a scout first.

<details>
<summary>Silicon notes — only relevant if the bulbs turn out to be non-Matter (unconfirmed)</summary>

**Hard exclusion:** Matter over Wi-Fi requires Wi-Fi *and* BLE. That rules out **ESP8266/ESP8285**
and **RTL8710BN** outright — neither has BLE — and effectively rules out plain **BK7231N/T**.

FCC internal photos of an AiDot bulb filing show module pad labels:

```
NC · TX · RX · CEN · SL_2 · SL_1 · GND        ADC · PWM · IO16 · 3.3V
```

🔑 **`CEN` is the tell.** Espressif parts label chip-enable **`EN`**; **`CEN`** is Beken/Realtek
nomenclature — which argues against an ESP32-C3 despite the C3 being the market-leading Matter bulb
chip. Ranked candidates: **Beken BK7238** (~40%, Beken's Matter part, OpenBeken-supported),
**Realtek RTL8720CF / Ameba Z2** (~30%), **ESP32-C3** (~20%).

Countervailing lead: the blakadder template database lists two **Linkind wall switches** on
**ESP32-SOLO-1**, suggesting AiDot may be an Espressif house. That is an inference across product
lines, not a fact about this bulb.

**None of this is confirmed, and on the Matter branch none of it matters.**
</details>

> ### ⚠️ Mains safety — if you open a bulb anyway
> An A19 bulb's driver board sits directly on **mains potential** — there is no isolation
> transformer. The board can hold a lethal charge in its bulk capacitor **after** it is unplugged.
> Never open a bulb connected to mains, never probe a powered board, and discharge the bulk
> capacitor before touching anything. Use **3.3 V logic only**. If you are not already comfortable
> working on non-isolated mains circuitry, do not start here.

---

## 10. Open questions

- [ ] 🚧 **Is this exact ASIN the Matter SKU?** The CSA record proves a Consciot A19 is certified;
      confirming this box is that SKU is pending an owner check. *This is the only thing that
      changes the recommendation.* → [§2](#2--which-sku-do-you-have)
- [ ] **Exact HA UI wording for BLE-proxy commissioning** — the feature and architecture are
      confirmed; the precise click-path is inferred from the standard add-device flow.
- [ ] **Does matter.js 9.x need an interface hint on a multi-NIC host?** Expected: no.
- [ ] **Silicon** — unconfirmed, and moot unless Path B applies.
- [ ] **Does it implement Matter OTA?** Affects whether firmware updates surface in HA.
- [ ] **Credential persistence in `hass-AiDot` across restarts** — Path B only; resolved
      empirically by the firewall test in §8.

*Note on the CSA record:* one search snippet showed certification ID `CSA2526DMAT45503-24` while
the product page showed `CSA2609OMAT49756-24` — consistent with AiDot holding multiple bulb
certificates. The VID, PID and device type are the load-bearing fields, and they are consistent.

---

## 11. Prior art & credits

**What makes the recommended path possible**

- **[Home Assistant](https://www.home-assistant.io/)'s [Matter integration](https://www.home-assistant.io/integrations/matter/)**
  and the [Python Matter Server](https://github.com/home-assistant-libs/python-matter-server) /
  [Matter Server add-on](https://github.com/home-assistant/addons/blob/master/matter_server/DOCS.md)
  — the local fabric controller doing the actual work, including phone-free BLE-proxy commissioning.
- **[Connectivity Standards Alliance](https://csa-iot.org/)** — Matter itself, and the public
  [certified-products database](https://csa-iot.org/csa_product/consciot-smart-light-bulb/) that
  settled the identification question with a primary source instead of guesswork.
- **[project-chip/connectedhomeip](https://github.com/project-chip/connectedhomeip)** — the
  reference SDK and `chip-tool` diagnostics.

**Path B tooling**

- **[Home Assistant `aidot` integration](https://www.home-assistant.io/integrations/aidot)** — the
  official, built-in option.
- **[sulibot/hass-AiDot](https://github.com/sulibot/hass-AiDot)** — the community fork, whose
  `protocol_documentation.md` is the best public description of the AiDot local protocol.

**Investigated and *not* applicable**

- **[tuya-cloudcutter](https://github.com/tuya-cloudcutter/tuya-cloudcutter)** — excellent work,
  wrong vendor. Zero Consciot profiles in 1,149. Listed so the next person does not spend an
  evening rediscovering that.
- **[tuya-convert](https://github.com/ct-Open-Source/tuya-convert)** — deprecated upstream, and
  inapplicable for the same reason.
- **[ESPHome](https://esphome.io/) / [OpenBeken](https://github.com/openshwprojects/OpenBK7231T_App)**
  — outstanding projects, but see [§9](#9-flashing--ruled-out): flashing a Matter bulb destroys it.

---

## Disclaimer

Independent interoperability research on hardware the author purchased. No affiliation with
Consciot, AiDot, Leedarson, Amazon, or the Connectivity Standards Alliance.

The recommended path (§4) involves no disassembly and no warranty impact. Opening a mains-powered
bulb voids its warranty and carries a real risk of electric shock and fire; §9 is at your own risk.

## License

[MIT](LICENSE) © 2026 JP ([@jphein](https://github.com/jphein))
