# 📍 Concepts

Magic Areas works by detecting presence within an area and triggering state changes or automations accordingly. It does this by monitoring presence-related events from specific Home Assistant entity types and interpreting their states to determine whether an area is occupied or clear.

## 🛰️ Supported Presence Sources

Magic Areas currently supports presence sensing from the following Home Assistant platforms:

- `media_player` (and `remote`)
- `binary_sensor`
- `device_tracker`

This may seem like a limited list, but it's intentional. Magic Areas relies on clear and predictable `states` and `device_class` values to automatically detect which entities can be used for presence sensing — with no manual configuration required in most cases.

### Presence logic examples:

- If a `media_player` is **playing** in an area → the area is considered **occupied**.
- If a `device_tracker` entity (e.g., your desktop computer) is **home** → the area is **occupied**.
- If a `binary_sensor` for motion or presence is **on** → the area is **occupied**.

## 🧠 Default Presence States

The following entity states are used by default to infer presence:

- `on`
- `home`
- `playing`

## 📡 Default `binary_sensor` Device Classes

Magic Areas automatically uses the following `device_class` values for `binary_sensor` entities:

- `motion`
- `occupancy`
- `presence`

These cover most sensors used for room occupancy detection.

You can also **extend this list** in the UI if you use other sensors that make sense for your setup — for example, using a `door` sensor on a frequently used door like your garage entry.

---

## ⚠️ Known Limitations

Some Home Assistant entities — such as `switch` or general-purpose `sensor` — don’t reliably convey presence information by default. However, you can easily work around this using Home Assistant’s flexible templating tools.

### 💡 Tips for Custom Presence Detection

You can create custom presence logic using these tools:

- **[Template Binary Sensors](https://www.home-assistant.io/integrations/template/)**
  Use them to turn power or status sensors into binary `on`/`off` presence indicators.

- **[Switch as X](https://www.home-assistant.io/integrations/switch_as_x/)**
  Useful for converting smart plugs into presence sensors by modeling them as something else.

### ✅ Example Use Cases:

- Detect TV usage by monitoring power draw with a smart plug, then create a template binary sensor to represent presence.
- Use a door contact sensor (`device_class: door`) to indicate occupancy when a specific door opens.
- Combine with external solutions like [Bermuda](https://github.com/agittins/bermuda), [ESPresence](https://espresense.com/) and [Room Assistant](https://github.com/mKeRix/room-assistant) to use Bluetooth-based room tracking.

---

With the right combination of sensors and logic, Magic Areas can reliably detect presence in every corner of your home — even in edge cases!
