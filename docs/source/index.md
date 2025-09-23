# 🪄 Magic Areas for Home Assistant

Magic Areas is a [Home Assistant](https://www.home-assistant.io/) custom integration that brings context-aware, state-driven automation to your smart home.

Instead of configuring each entity manually, Magic Areas leverages **areas**, **meta-areas**, and **presence sensing** to create smart groups and advanced automations. It turns Home Assistant's built-in Areas into **intelligent, presence-aware zones**, automatically detecting when someone is in a room — and when they’ve left — using your existing motion, presence, or occupancy sensors.

Magic Areas intelligently tracks presence and adds powerful automations like light control, fan activation, and climate presets — all managed through a clean UI.

Smart areas that just works, everytime, out of the box. Fully customizable if you want it.

[![Open your Home Assistant instance and open the Adaptive Lighting integration inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jseidl&repository=magic-areas&category=integration)

## ✨ What Magic Areas Does

* Detects presence in each area using multiple sources (motion sensors, media players, device trackers, BLE beacons, and more).
* Creates smart groups (lights, fans, climate, media players) that respond to an area’s state automatically.
* Supports secondary states like dark, sleep, and extended for context-aware automation.
* Provides meta-areas (e.g., Interior, Exterior, Global, Floors) to coordinate multiple areas at once.
* Includes built-in, automation-like features: light control, fan groups, climate preset switching, and more

## 📖 Documentation Structure

The docs are split into **concepts**, **how-tos**, and **feature references** so you can dive in depending on what you need:

### 🧠 Concepts

Learn the key ideas that power Magic Areas:

* [Presence Sensing](concepts/presence-sensing.md)
* [Area States](concepts/area-states.md)
* [Meta-Areas](concepts/meta-areas.md)

### 🛠️ How-To Guides

Step-by-step instructions to get started and troubleshoot:

* [Installation](how-to/installation.md)
* [Getting Started](how-to/getting-started.md)
* [Configuration explained](how-to/configuration.md)
* [Troubleshooting](how-to/troubleshooting.md)

And also a library of implementation examples:

* [Making every room magic](how-to/library/implementation-ideas-for-every-room.md)
* [Using energy aggregates on the energy dashboard](how-to/library/energy-aggregates.md)
* [Automatic lights brightness control](how-to/library/automatic-light-brightness-control.md)
* [Perfecting climate comfort with Climate Control](how-to/library/perfecting-climate-comfort.md)

... and others!

### ⚡ Features

Detailed documentation for each [feature](features/index.md).

## 🚀 How to get into magic?

1. [Install Magic Areas](how-to/installation.md) via HACS or manually.
2. Follow the [Getting Started](how-to/getting-started.md) guide to set up your first areas.
3. Explore the [Features](features/index.md) to unlock the full potential of your smart home.

!!! question "Need help?"
    💬 Join the [Magic Areas Discord](https://discord.gg/tvaS4BG5) or open an [issue on GitHub](https://github.com/jseidl/magic-areas/issues).
