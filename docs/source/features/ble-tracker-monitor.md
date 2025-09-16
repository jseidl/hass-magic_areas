# Bluetooth & Bluetooth LE (BLE) Tracker Monitor

The **BLE Tracker Monitor** feature streamlines presence detection using **text-based BLE sensors**, such as those from Bermuda, ESPresense, or Room Assistant.

## 📍 Why use it?

Normally, you’d need to manually create multiple [template binary sensors](https://www.home-assistant.io/integrations/template/)—one per area—to convert each tracker’s text state (e.g., `kitchen`, `bedroom`) into a usable `on`/`off` signal for presence detection.

Magic Areas eliminates this hassle by doing it automatically.

## ⚙️ How it works

When you reference a BLE tracker sensor in the area config, Magic Areas will:

- Automatically create a binary presence sensor.
- Track its state by checking whether it matches:
  - the **area name**
  - the **area ID**
  - the **area slug**
  (All compared in lowercase)

If there's a match, the area will be considered `occupied`.

This allows Magic Areas to **use the tracker directly for presence detection**, without needing custom templates.

> ✅ Any text-based sensor that reports an area name, ID, or slug can be used with this feature—not just BLE trackers.

## 🧠 Compatibility

This feature is known to work with:

- [Bermuda](https://github.com/agittins/bermuda) ✅
- [ESPresence](https://espresense.com/) ⚠️ (dependent on consistent naming)
- [Room Assistant](https://github.com/mKeRix/room-assistant) ⚠️ (untested, but should work)

> 💬 Have another system that reports presence as area names or IDs? It’ll likely work too.

## ⚠️ Flappy Sensors? Read This

!!! warning
    BLE trackers can be **flappy**—reporting incorrect or outdated values momentarily.
    To prevent incorrect `clear` states, it’s highly recommended to add them to the **"keep only sensors"** list in your area config.

This ensures their presence signal is only _added_ to detection logic and not used as the sole decider.

## 💡 Example Use Case

Let’s say your Bermuda tracker reports `"living_room"` when it detects a person in the Living Room.

Magic Areas will:

- Detect that `living_room` matches the area's slug
- Set the Living Room area to `occupied`
- No template sensors needed!
