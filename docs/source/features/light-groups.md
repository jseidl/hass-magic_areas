The **Light Groups** feature in Magic Areas helps you organize and automate your lights more intelligently and contextually—starting with automatic [light group](https://www.home-assistant.io/integrations/light.group/) creation and adding rich, state-aware behavior for smarter automation.

## ✅ Basic Functionality

At its simplest, this feature automatically creates a Home Assistant light group for each area using all `light` entities assigned to it.

!!! warning
    No group will be created if there are no `light` entities in the area.

## 🌈 Secondary Light Groups

You can further classify your lights into **secondary groups** with specific purposes:

- **Overhead Lights** – Main ceiling lights for general illumination.
- **Accent Lights** – Decorative or highlight lighting (e.g., under cabinets, wall sconces).
- **Task Lights** – Focused lights for workspaces, desks, or reading.
- **Sleep Lights** – Dim lighting suitable for nighttime or bedtime use.

Each of these groups—when populated—will automatically have their own dedicated `light` group created in Home Assistant.

These groups can also be linked to an area's **secondary states** (e.g., `sleep`, `accented`, `extended`) for smarter automation based on context.

!!! warning
    🧠 To enable automation, turn on the `Light Control ($Area)` switch entity that Magic Areas creates for each instance.

## 🔁 Automatic Control

Magic Areas can **automatically turn lights on or off** based on:

- The area's **primary presence state**: `occupied` or `clear`
- The area's **secondary states**: `dark`, `extended`, `sleep`, etc.

### 🌒 The `dark` State

If you've configured a `dark` sensor for the area, lights will only turn on **when the area is both occupied _and_ dark**. Otherwise, lights will turn on anytime the area becomes occupied.

!!! note
    ✅ If the area becomes dark **while already occupied**, lights will turn on immediately.

#### Dark State Behavior Matrix

| Area State | Is `dark` configured? | Dark State | Lights will...   |
|------------|-----------------------|------------|------------------|
| `occupied` | ❌ No                 | N/A        | Turn on          |
| `occupied` | ✅ Yes               | `off`      | Do nothing       |
| `occupied` | ✅ Yes               | `on`       | Turn on          |
| `clear`    | ❌ No                 | N/A        | Turn off         |
| `clear`    | ✅ Yes               | `off`      | Turn off         |
| `clear`    | ✅ Yes               | `on`       | Turn off         |

### 💡 Automatically Turning Off Lights

When an area becomes `clear`, **all lights are turned off**, regardless of secondary state.
If you want to prevent this, you can disable **Automatic Control** for the area.

## 🧩 Advanced: Secondary Light Group Control

Secondary light groups can be tied to specific **area states** (primary or secondary). A group will only turn on if the area is currently in one of the selected states.

### 🔘 Define Triggering States for Each Group

Each light group can be associated with one or more states that should trigger it. These may include:

- `occupied` (default)
- `sleep`
- `extended`
- `accented`
- Or any other defined secondary state

!!! warning
    ❗Light group categories (Overhead, Accent, Task, Sleep) are **not automatically mapped** to states. For example, a "Sleep Light" does **not** turn on automatically during the `sleep` state unless you explicitly configure it to do so.

💡 *If you want a light group to remain active across multiple states (e.g., `occupied` and `extended`), make sure to select all relevant states.*

### 🔄 When Should the Light Group React?

You can specify **when** a light group should respond to area state changes:

- `occupancy` – The group only activates when the area transitions from `clear` to `occupied`.
- `state` – The group reacts to changes in the **specific secondary state** (e.g., whenever the `sleep` state is entered or exited).

For example:
- You might want `sleep` lights to turn on **only** when first entering the room (`occupancy`).
- You might want `accent` lights to respond **whenever** the state changes (`state`).

## 🧠 Usage Examples

### 🛋️ Evening ambiance with accent lights

Configure your `Accent Lights` group to turn on during the `extended` state in the living room.

- **Why**: You want soft lighting during movie nights or relaxing evenings.
- **How**: Tie the `accent` group to the `extended` state using `state` trigger mode.

### 💤 Nighttime routine in bedrooms

Use `Sleep Lights` tied to the `sleep` state and set to activate only via `occupancy`.

- **Why**: You want dim lights to turn on when someone enters a room at night.
- **How**: Map `sleep` lights to the `sleep` state and trigger them only on `occupancy` so they don’t toggle unnecessarily.

### 💼 Focus lighting for work areas

Assign `Task Lights` in your home office to respond to the `occupied` state.

- **Why**: When someone enters the office, the desk lamp should turn on automatically.
- **How**: Link the `task` group to the `occupied` state using either `occupancy` or `state` depending on behavior preference.

### 🧹 Cleaning mode lighting

Tie all `Overhead Lights` in a floor meta-area to the `cleaning` state (if configured).

- **Why**: Maximize brightness when cleaning is underway.
- **How**: Map `overhead` lights to the `cleaning` state using `state` mode for immediate reaction.

## 🎚️ Brightness and Color Temperature

Magic Areas **does not control brightness or color temperature** of lights.

This is by design, and you are encouraged to use existing integrations like:

- [Adaptive Lighting](https://github.com/basnijholt/adaptive-lighting/)
- [Circadian Lighting](https://github.com/claytonjn/hass-circadian_lighting)

These handle brightness and temperature more effectively and are fully compatible with Magic Areas.
