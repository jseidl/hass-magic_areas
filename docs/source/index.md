# 🪄 Magic Areas for Home Assistant

Welcome to the **Magic Areas** documentation!
Magic Areas is a [Home Assistant](https://www.home-assistant.io/) custom integration that brings **context-aware, state-driven automation** to your smart home.

Instead of configuring each entity manually, Magic Areas leverages **areas**, **meta-areas**, and **presence sensing** to create smart groups and advanced automations — with **zero YAML required**.

---

## ✨ What Magic Areas Does

* Detects **presence** in each area using multiple sources (motion sensors, media players, device trackers, BLE beacons, and more).
* Creates **smart groups** (lights, fans, climate, media players) that respond to an area’s state automatically.
* Supports **secondary states** like `dark`, `sleep`, and `extended` for context-aware automation.
* Provides **meta-areas** (e.g., *Interior*, *Exterior*, *Global*, *Floors*) to coordinate multiple areas at once.
* Adds **advanced features** like:
  * 📊 Aggregation sensors
  * 🛡️ Area health monitoring
  * 🎶 Area-aware media routing
  * 🐝 Wasp-in-a-box logic
  * ⏱️ Presence hold switches
  * 🛰️ BLE tracker support

---

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
* [Troubleshooting](how-to/troubleshooting.md)

### ⚡ Features

Detailed documentation for each feature:

* [Features Overview](features/index.md)
* Smart Groups:
  * [Light Groups](features/light-groups.md)
  * [Fan Groups](features/fan-groups.md)
  * [Climate Control](features/climate-control.md)
* Simple Groups:
  * [Cover Groups](features/cover-groups.md)
  * [Media Player Groups](features/media-player-groups.md)
* Sensors & Tracking:
  * [Aggregation](features/aggregation.md)
  * [Health Sensors](features/health-sensor.md)
  * [BLE Tracker Sensors](features/ble-tracker-monitor.md)
  * [Wasp in a Box](features/wasp-in-a-box.md)
* Utilities:
  * [Area-Aware Media Player](features/area-aware-media-player.md)
  * [Presence Hold](features/presence-hold.md)

---

## 🚀 Next Steps

1. [Install Magic Areas](how-to/installation.md) via HACS or manually.
2. Follow the [Getting Started](how-to/getting-started.md) guide to set up your first areas.
3. Explore the [Features](features/index.md) to unlock the full potential of your smart home.

💬 Need help? Join the [Magic Areas Discord](https://discord.gg/tvaS4BG5) or open an [issue on GitHub](https://github.com/jseidl/hass-magic_areas/issues).

---
