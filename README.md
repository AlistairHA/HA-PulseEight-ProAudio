<p align="center"><a href="https://www.pulse-eight.com/p/215/proaudio-8"><img src="https://www.pulse-eight.com/generated-assets/products/0000598_555.png" alt="Pulse-Eight ProAudio 8, front and rear" width="520"></a></p>

# Pulse-Eight ProAudio for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories) [![Release](https://img.shields.io/github/v/release/AlistairHA/HA-PulseEight-ProAudio)](https://github.com/AlistairHA/HA-PulseEight-ProAudio/releases) ![Home Assistant 2025.1+](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-03A9F4.svg) ![Local control](https://img.shields.io/badge/IoT-local%20only-4CAF50.svg)

Run your **Pulse-Eight ProAudio** multi-zone audio matrix from Home Assistant: see what's playing where, drag zones onto sources, set volumes, mute and power zones, and recall whole-house presets with one tap. It talks to the unit directly over your LAN (TCP port 50005), with no cloud or extra hardware.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AlistairHA&repository=HA-PulseEight-ProAudio&category=integration)

## Highlights

- **Routing panel** with colour-coded lines from every input to its zones; drag to route, drop an input on *Disconnect* to clear it, undo anything.
- **Handles big systems**: zone groups, a compact view, search and a sticky inputs column for 40+ zones.
- **Presets** such as *AMB Source → Whole house / Upstairs / Master Bedroom*, with volume, power-on and exclusive options.
- **Zone entities** (media player, volume, mute, power) for dashboards, voice assistants and automations.
- **Status**: model, firmware, network, protocol flags and digital-input signal type.

![Routing](docs/routing.png)

## Supported hardware

<p align="center">
  <a href="https://www.pulse-eight.com/p/215/proaudio-8"><img src="https://www.pulse-eight.com/generated-assets/products/0000580_555.png" alt="ProAudio 8" height="110"></a>
  <a href="https://www.pulse-eight.com/p/210/proaudio-16"><img src="https://www.pulse-eight.com/generated-assets/products/0000582_555.png" alt="ProAudio 16" height="110"></a>
  <a href="https://www.pulse-eight.com/p/213/proaudio-3248"><img src="https://www.pulse-eight.com/generated-assets/products/0000589_555.png" alt="ProAudio 3248" height="110"></a>
</p>

[ProAudio 8](https://www.pulse-eight.com/p/215/proaudio-8), [16](https://www.pulse-eight.com/p/210/proaudio-16), [16 RS](https://www.pulse-eight.com/p/242/proaudio-16-rs), [1632](https://www.pulse-eight.com/p/211/proaudio-1632), [32](https://www.pulse-eight.com/p/212/proaudio-32), [3248](https://www.pulse-eight.com/p/213/proaudio-3248) and [3264](https://www.pulse-eight.com/p/241/proaudio-3264) (and the Zektor-branded equivalents). The model is detected automatically, along with its number of inputs and zones.

## What you get

### ProAudio sidebar panel

| Tab | What it does |
|---|---|
| **Routing** | Inputs on the left, outputs on the right, with colour-coded lines showing where each input goes. To route, drag one or more outputs onto an input, or **drag a whole zone-group header** onto an input. **Drag an input onto Disconnect** to clear every zone it feeds, or use the ✕ on the input card; **drag an input onto another input** to move all its zones across. Every routing change shows an **Undo** toast, Clear all included. The inputs column stays put while you scroll a long output list. |
| **Zones** | One card per zone with a source picker, volume slider, mute and power. Cards are grouped by zone group, with On/Off/Mute buttons for each group and for all zones. |
| **Presets** | One-tap routing scenes such as *AMB Source → Whole house*, *AMB Source → Upstairs* or *AMB Source → Master Bedroom*. Each preset can power the zones on, unmute them and set a volume. It can also be **exclusive**, which disconnects any other zones playing that input (so "Master Bedroom only" really means only there). In the editor you can tick zones, mix inputs, or copy the current routing. |
| **Status** | Connection, model, firmware, serial number, power state, master volume, IP/mask/gateway/DHCP, protocol flags (ASY/ACK/ECO/XIO), and zones on/routed/muted. It shows **signal type on digital inputs** (No signal / PCM / Dolby-DTS) and a log of recent errors with their meanings. |
| **Settings** | Name every input and output, hide the ones you don't use, and arrange zones into **groups** (e.g. Ground floor, First floor, Outside). Names are used throughout Home Assistant. |

**Long zone lists (40+ outputs):**
- **Zone groups** collapse into one header, which shows how many zones are routed and on and the colours of the inputs feeding them. A collapsed group still gets routing lines.
- The **Compact** density puts each zone on a single line, roughly 40 zones per screen. It's the default on phones.
- **Output filters:** All, Routed, On or Unrouted.
- **Find zone** search matches zone names and input names.
- Collapsed groups and the density setting are remembered in each browser.

The panel has a master volume slider and a unit power button in the header. It updates live: changes made from the front panel, the unit's web page or another controller show up instantly. It works on desktop and in the HA phone app; on touch screens, **long-press an output to drag it**.

The same view is also available as a dashboard card:

```yaml
type: custom:proaudio-card
tab: routing        # routing | zones | presets | status | settings
# entry_id: ...     # only needed if you have more than one ProAudio
```

To use the card, first add `/pulse_eight_proaudio_static/proaudio-panel.js` as a JavaScript module under **Settings → Dashboards → ⋮ → Resources**.

| Compact, groups collapsed | Clear an input (drag onto Disconnect) | Dark | Phone |
|---|---|---|---|
| ![](docs/compact.png) | ![](docs/drag-input.png) | ![](docs/dark.png) | ![](docs/mobile.png) |

### Entities

- **One media player per zone.** Each zone is a separate device (e.g. "Kitchen"), so you can put it in an area. It supports source select, volume, mute and on/off, so it works with the standard media cards, voice and automations.
- **Master volume** (number, in dB: −100 = mute, 0 = unity, up to +24).
- **Unit power** (switch).
- **Buttons:** *Clear all routing*, *Re-sync*, and **one button per preset**. Preset buttons are added and removed automatically as you edit presets.
- **Sensors:** model, firmware, serial, IP address, zones on, zones routed, last error, and a connectivity sensor.

### Actions (for automations and scripts)

| Action | Example |
|---|---|
| `pulse_eight_proaudio.route` | `zones: [1, 3, 5]` and/or `group: "Upstairs"`, `source: "Spotify"` (an input name or a source number; `0` disconnects) |
| `pulse_eight_proaudio.apply_preset` | `preset: "AMB Source → Whole house"` |
| `pulse_eight_proaudio.clear_all` | |
| `pulse_eight_proaudio.zone_power` / `zone_mute` / `zone_volume` | `zones: [2]` or `group: "Outside"`, `on: true` / `mute: true` / `volume: 35` |
| `pulse_eight_proaudio.send_command` | `command: "BAZ @1,140"` returns `{error_code: 0}`. Factory reset and IP changes are blocked. |

## Install

**HACS (recommended)**

1. Click the button below, or in HACS open **⋮ → Custom repositories** and add `https://github.com/AlistairHA/HA-PulseEight-ProAudio` as type **Integration**.

   [![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AlistairHA&repository=HA-PulseEight-ProAudio&category=integration)
2. Download **Pulse-Eight ProAudio**, then restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → Pulse-Eight ProAudio**.
   Enter the unit's IP address (the port is 50005).
4. Open **ProAudio** in the sidebar. Start on the **Settings** tab to name your inputs and zones, hide the unused ones and arrange zone groups, then create your presets.

**Manual:** copy `custom_components/pulse_eight_proaudio` into `<config>/custom_components/` and restart Home Assistant.

Updates appear under **Settings → Updates** whenever a new release is published.

## How it talks to the unit

The integration follows the *ProAudio Universal Serial Protocol* (v1.1) and Pulse-Eight's open-source Control4 drivers.

- It keeps one persistent TCP connection and parses every `^=…$` frame, including the breakaway form `^=SZ.2 @001,003$` that the Control4 driver enables. With **ASY** on (the factory default), changes are pushed instantly. A full re-sync also runs every 30 s; you can change this under Configure.
- It works whether **ACK** is on or off. When another controller has turned ACKs off, errors (`^!n$`) are still detected and shown in the panel.
- **It never changes the unit's XS settings or saves anything to EEPROM**, so it can safely share the unit with Control4 or other controllers.
- Source numbers depend on the model and on **XIO** mode. Both are detected automatically. On a ProAudio32, sources are analog 1–32, coax 33–64 and optical 65–80.
- **Commands used:**
  - `V?`, `P`, `MV` and `XS?` for the unit;
  - `SZ` for routing;
  - `PZ` for zone power;
  - `VPZ` for volume as a percentage of each zone's min/max range;
  - `VMZ` for mute;
  - `MZ?` and `ATZ?` for status;
  - `IPAX?`, `IPMX?`, `IPGX?` and `IPSET?` for network details.

**Mute** uses `VMZ` (volume mute), as the protocol guide recommends. `MZ` is a hard disconnect and is only shown, not used for muting. **Clear all** sets every zone to source 0 (`SZ @1:N,0`).

Routing applies to the **analog** zone outputs. By default the coax outputs mirror them, so they follow automatically.

## Part of a family

These integrations share the same design, so their panels and entities look and behave alike:

| Integration | What it controls |
|---|---|
| [**neo:X+ matrix**](https://github.com/AlistairHA/HA-PulseEight-NeoX) | HDMI/HDBaseT video matrix: routing, CEC display control, link health |
| [**ProAmp8 amplifier**](https://github.com/AlistairHA/HA-PulseEight-ProAmp) | 8-zone amplifier: per-zone volume, mute and power mode, health |

## Development

```bash
pip install pytest-homeassistant-custom-component
pytest                                          # backend tests, using a fake unit over real TCP
python tests/fake_proaudio.py --port 50005      # simulator for UI work
```

`tests/fake_proaudio.py` is a protocol-accurate simulator. It supports ACK on/off, the breakaway suffix, async push to all clients, error codes and standby.

### Releasing

HACS installs from GitHub releases. To publish a change, bump `version` in `custom_components/pulse_eight_proaudio/manifest.json`, commit, then create a release with a matching tag (for example `v1.2.3`). The included *Release* workflow does this automatically when the version changes on `main` (if the `.github` folder is in the repo). Without any release, HACS shows *"'' is not a usable version"*.

---

Product images © Pulse-Eight Ltd, used with permission. This is an independent project and isn't made, supported or endorsed by Pulse-Eight or the Home Assistant project.
