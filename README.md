![Build Status][ci-status] [![GitHub Release][releases-shield]][releases] [![License][license-shield]](LICENSE) [![GitHub Last Commit][last-commit-shield]][commits]
![Project Maintenance][maintenance-shield] [![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![HACS][hacs-shield]][hacs] ![integration-usage-shield] [![Discord][discord-shield]][discord]

![ma-logo]

# Magic Areas for Home Assistant
> Your areas so smart it's almost magic! 🪄

Ever had your lights turn off while you're still in the room?

**Magic Areas** fixes that. It turns Home Assistant's built-in Areas into **intelligent, presence-aware zones**, automatically detecting when someone is in a room — and when they’ve left — using your existing motion, presence, or occupancy sensors.

No more motion-only logic that fails when you sit still. Magic Areas intelligently tracks presence and adds powerful automations like light control, fan activation, and climate presets — all managed through a clean UI.

Works out of the box. Fully customizable if you want it.

## How It Works

* Detects sensors in your areas automatically (motion, presence, BLE, etc.)
* Tracks room presence with a smart `area_state` sensor
* Adds secondary states like `dark`, `sleep`, and `extended`
* Includes built-in, automation-like features: light control, fan groups, climate preset switching, and more
* Fully configurable through the UI

## Features

### 💡 Smart Light Groups

Automatically groups your lights by purpose — overhead, task, accent, and sleep — and controls them based on presence state. Lights can be set to trigger only in the dark or after extended occupancy.

➡️ Group `light` entities like `Kitchen Overhead Lights`, `Bedroom Accent Lights`

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Light-Groups)

---

### 🌡️ Climate Control

Map area states to climate device presets. For example: set your HVAC to `eco` when empty, and back to `comfort` when occupied or in sleep mode.

➡️ Works best in meta-areas like Interior or Floor

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Climate-Control)

---

### 🧠 Wasp in a Box

Reliable presence sensing that accounts for people entering/leaving rooms with doors. Combines motion and door/garage sensors to prevent lights from turning off while you’re still inside.

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Wasp-in-a-Box)

---

### 🕰️ Smart Presence Timeouts

Each area has a configurable timeout for clearing presence after the last motion. If motion is detected again within the timeout, it resets — no abrupt shutoffs.

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Presence-Timeout)

---

### 🕯️ Secondary States

Define subtle room states for more nuanced automations:

* `dark` / `bright`: Based on light sensors or sun
* `sleep`: Tracked by any entity
* `extended`: When a room has been occupied beyond a set time
* `accented`: Track presence based on entertainment like media players

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Secondary-States)

---

### 🔥 Fan Groups

Auto-creates a `fan` group entity for each area and lets you control it using an aggregated value like temperature, humidity, or CO₂. Great for exhaust fans, ceiling fans, or air quality fans.

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Fan-Groups)

---

### 📶 Area-Aware Media Player

Play media (like TTS alerts) only in rooms that are currently occupied. Forward notifications to the right areas — not empty ones.

➡️ Configurable per area: pick devices, states, and behavior

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Area-Aware-Media-Player)

---

### 🧮 Sensor Aggregates

Aggregates all `sensor` and `binary_sensor` entities in the area by `device_class` and `unit_of_measurement`. Great for dashboards, alerts, and logic.

➡️ Auto-generates `sensor.area_temperature` or `binary_sensor.area_motion` style entities

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Aggregates)

---

### 🚨 Health Sensors

Auto-aggregated binary sensors for safety-related device classes:

* `gas`, `smoke`, `moisture` (leaks), `problem`, `safety`

➡️ Works in all areas including meta-areas

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Health-Sensors)

---

### ✋ Presence Hold

Creates a switch to manually override presence in an area. Useful if sensors aren’t fully reliable yet or for guests.

➡️ Optional timeout to reset the hold automatically

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Presence-Hold)

---

### 📡 BLE Tracker Integration

Track text-based BLE sensors (like ESPresense, Bermuda, or Room Assistant) directly. Magic Areas will convert their values into usable presence sensors automatically.

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/BLE-Tracker-Sensor)

---

### 🎮 Media Player Groups

Creates `media_player` group entities automatically per area with all media players. Forwards all `play_media` actions to them.

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Media-Player-Groups)

---

### 🪟 Cover Groups

Groups covers (blinds, shades, garage doors) per area into `cover` groups.

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Cover-Groups)

---

## 🏠 Meta-Areas and Hierarchies

Tag areas as **interior**, **exterior**, or assign them to **floors**. Magic Areas will create meta-areas to track grouped presence (e.g., upstairs occupied). Presence logic and secondary states are inherited and calculated automatically.

📖 [Learn more](https://github.com/jseidl/hass-magic_areas/wiki/Meta-Areas)

## 🧙 Demo / How can Magic Areas help me?

Check out the wiki cookbook [Magic Areas in every room](https://github.com/jseidl/hass-magic_areas/wiki/Magic-Areas-in-every-room) to see how you can apply Magic Areas to make every room in your house, magic!

## 🚀 Getting Started

1. Install via [HACS](https://hacs.xyz/) → Magic Areas
2. Go to Settings → Devices & Services → Magic Areas
3. Start adding your Areas and tweaking settings

📖 Visit the [Wiki](https://github.com/jseidl/hass-magic_areas/wiki/Configuration) for complete guides, examples, and tips.

## 🌐 Magic Areas in your language!

Magic Areas has full translation support, meaning even your entities will be translated and is available in the following languages:

<a href="https://hosted.weblate.org/engage/magic-areas/">
<img src="https://hosted.weblate.org/widget/magic-areas/multi-auto.svg" alt="Translation status" />
</a>

Help to translate Magic Areas into your language from your web browser! We use [Hosted Weblate](https://hosted.weblate.org/engage/magic-areas/) so you don't need to fool around with pull requests nor JSON files!

## 🛠️ Problems/bugs, questions, feature requests?

### Questions?

Come talk to me on the `#support` channel at my [Discord server](https://discord.gg/8vxJpJ2vP4) or pop a question on our [Q&A Discussions page](https://github.com/jseidl/hass-magic_areas/discussions/categories/q-a)!

### Issues?

Please enable debug logging by putting this in `configuration.yaml`:

```yaml
logger:
    default: warning
    logs:
        custom_components.magic_areas: debug
```

As soon as the issue occurs capture the contents of the log (`/config/home-assistant.log`) and open up a [ticket](https://github.com/jseidl/hass-magic_areas/issues) or join the `#support` channel on my [Discord server](https://discord.gg/8vxJpJ2vP4)!

### Feature requests

Please do not open issues for feature requests. Use the [Feature Request discussions area](https://github.com/jseidl/hass-magic_areas/discussions/categories/ideas-feature-requests) to contribute with your ideas!

### Contributions are welcome!

If you would like to contribute to Magic Areas please read the [Contribution guidelines](CONTRIBUTING.md).

---

Enjoy smarter automations — and lights that finally understand you're still in the room ✨

***

[magic_areas]: https://github.com/jseidl/hass-magic_areas
[buymecoffee]: https://www.buymeacoffee.com/janseidl
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/jseidl/hass-magic_areas.svg?style=for-the-badge
[commits]: https://github.com/jseidl/hass-magic_areas/commits/main
[discord]: https://discord.gg/tvaS4BG5
[hacs]: https://github.com/hacs/integration
[discord-shield]: https://img.shields.io/discord/928386239789400065?style=for-the-badge&label=Discord
[license-shield]: https://img.shields.io/github/license/jseidl/hass-magic_areas.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jan%20Seidl%20%40jseidl-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jseidl/hass-magic_areas.svg?style=for-the-badge
[releases]: https://github.com/jseidl/hass-magic_areas/releases
[ci-status]: https://img.shields.io/github/actions/workflow/status/jseidl/hass-magic_areas/validation.yaml?style=for-the-badge
[last-commit-shield]: https://img.shields.io/github/last-commit/jseidl/hass-magic_areas?style=for-the-badge
[ma-logo]: https://raw.githubusercontent.com/home-assistant/brands/master/custom_integrations/magic_areas/logo.png
[contributors-badge]: https://flat.badgen.net/github/contributors/jseidl/hass-magic_areas
[integration-usage-shield]: https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.magic_areas.total&style=for-the-badge
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
