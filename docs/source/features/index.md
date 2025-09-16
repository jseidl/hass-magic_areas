# ✨ Feature List

Magic Areas can do a lot more than [[presence sensing|Presence-Sensing]]! Below is a list of built-in features grouped by category.

## 🧠 Smart Groups
Entities grouped with presence-aware automation logic.

* 💡 [[Light Groups|Light-Groups]]
  Automatically controls lights per area using presence, darkness, sleep, and more.

* 🌀 [[Fan Groups|Fan-Groups]]
  Dynamically manages fans in each area based on presence and occupancy. Includes support for multi-speed fans.

* 🌡️ [[Climate Groups|Climate-Groups]]
  Automatically turns climate devices on/off and maps area states to climate presets.

## 🧱 Simple Groups
Passive entity grouping for easier control.

* 🪟 [[Cover Groups|Cover-Groups]]
  Groups all `cover` entities (e.g. blinds, shades, garage doors) using [cover.group](https://www.home-assistant.io/integrations/cover.group/).

* 📺 [[Media Player Groups|Media-Player-Groups]]
  Groups all `media_player` entities using [media_player.group](https://www.home-assistant.io/integrations/media_player.group/).


## 📊 Sensor Features
Sensor logic, tracking, and hazard detection.

* 📍 [[BLE Tracker Sensors|BLE-Tracker-Sensor]]
  Adds support for BLE presence sensors (e.g., Bermuda, ESPresence, Room Assistant). Automatically maps tracked devices to areas.

* 📊 [[Aggregation|Aggregation]]
  Creates aggregate `sensor` or `binary_sensor` for supported device classes (e.g., temperature, humidity, occupancy).

* 🚨 [[Health Sensors|Health-Sensors]]
  Creates a binary sensor per area to represent health problems (e.g., leaks, smoke, gas).

* 🐝 [[Wasp in a Box|Wasp-in-a-box]]
  Adds intelligent presence logic using motion + door sensors to infer room occupancy even when closed.

## 🔊 Notifications

* 🔉 [[Area-Aware Media Player|Area-Aware-Media-Player]]
  A smart proxy `media_player` that plays TTS only in **occupied** areas. Great for room-aware voice alerts.

## ✋ Overrides

* ⏸️ [[Presence Hold|Presence-Hold]]
  Adds a manual `switch` to override presence state to `occupied`, with optional auto-reset timer.
