# Wasp-in-a-Box Sensor

The **Wasp in a Box** 🐝📦 feature improves presence detection by adding **contextual logic** to motion-based sensors using an associated door or entry sensor.

It’s based on a simple concept:

## 🧠 How It Works

1. If we **see a wasp**, there is a wasp in the box.
2. If we **close the box** while the wasp is inside, the wasp stays inside.
3. If the box remains closed and the wasp **stops moving**, we **assume** it's still inside.
4. If the box is **opened again** and the wasp isn’t moving, we assume it’s **gone**.

> 🧪 This helps avoid false clears due to motion sensors timing out after you’ve already left the room—preserving presence state more accurately.

When enabled, Magic Areas will:

- Create a `binary_sensor` for each area using this logic.
- Automatically use it for presence tracking (replacing or supplementing your regular motion sensors).
- Use the area’s **aggregated wasp and box sensors** (see below).

## ⏱️ Delay Behavior

Wasp in a Box forces the sensor **off** during a "box event" (i.e., door/garage opens or closes), and only checks for wasps after a configurable `delay`.

This ensures:

- When leaving a room (motion still `on`, door opens), we **wait** before checking motion again, in case the door is closed before the motion sensor clears. (e.g. bathrooms)
- When entering and closing the door, we must **trigger motion again after the delay** to confirm occupancy.

> ✅ This avoids premature `clear` and deadlock (motion sensor still on when you leave the room and close the door behind you) states and provides more reliable presence when entering or exiting enclosed rooms.

!!! warning
    To tune the delay, trigger your motion sensor and immediately leave, see how long it takes to clear. Repeat this test multiple times and average out the results. Add a few seconds to be safe.

## ⏳ Wasp Timeout

Motion sensors might flicker when doors are closed, causing a false-positive deadlock. Setting a Wasp timeout will force the wasp out of the box after a period (configurable) of inactivity.

## 📦 Sensor Types Used

### Wasp Sensors 🐝 (Configurable)

These indicate movement inside the area:

- `motion` (default)
- `occupancy`
- `presence`

You can configure which device classes to treat as wasps.

### Box Sensors 📦 (Auto-detected)

These indicate entry/exit points (the "box"):

- `door`
- `garage_door`

These are automatically detected during setup — no configuration needed.

!!! failure
    If you have doors you use for presence sensing that are not room access doors (e.g. cabinet doors, fridge doors), those will not work with Wasp in a Box. Exclude this doors from the area and create template sensors of device class `presence` based on their state, then add those template sensors to the area.

## ✅ Presence Integration

Once enabled, Magic Areas will:

- Automatically create a `binary_sensor.magic_areas_wiab_$area`
- Use it for **presence tracking** in that area

!!! tip
    Use this feature for **enclosed spaces** like:

    - Bathrooms 🚻
    - Bedrooms 🚪
    - Offices with doors 🧑‍💻
    - Garages
    - Laundry rooms ...

---

For even more precise presence, pair Wasp in a Box with [BLE Tracker Monitor](ble-tracker-monitor.md) and other presence sources.
