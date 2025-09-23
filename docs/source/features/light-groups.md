# 💡 Light Groups

The **Light Groups** feature in Magic Areas helps you organize and automate your lights intelligently and contextually—starting with automatic [light group](https://www.home-assistant.io/integrations/light.group/) creation and adding state-aware behavior for smarter automation.

## ✅ Basic Functionality

At its simplest, this feature automatically creates a Home Assistant light group for each area using all `light` entities assigned to it.

!!! warning
    No group will be created if there are no `light` entities in the area.

## 🌈 Available Light Groups

You can classify your lights into **predefined groups** for specific purposes:

- **Overhead Lights** – Main ceiling lights for general illumination.
- **Accent Lights** – Decorative or highlight lighting (e.g., under cabinets, wall sconces).
- **Task Lights** – Focused lights for workspaces, desks, or reading.
- **Sleep Lights** – Dim lighting suitable for nighttime or bedtime use.

Each of these groups—when populated—automatically gets a dedicated `light.group` in Home Assistant.
They can also be linked to an area's **secondary states** (e.g., `sleep`, `accented`, `extended`) for smarter automation.

!!! warning
    🧠 To enable automation, turn on the `Light Control ($Area)` switch created by Magic Areas.

## ⚙️ Configuration Options

| Option                              | Type             | Default      | Description                                                                                      |
|------------------------------------|-----------------|-------------|--------------------------------------------------------------------------------------------------|
| Overhead lights                     | entity list      | blank       | Lights assigned to this group.                                                                  |
| States which this group should be on (Overhead lights) | list | `occupied` | Area states that trigger this group.                                                           |
| When should we control this light? (Overhead lights) | multi-choice  | occupancy + state | `occupancy` triggers on clear → occupied; `state` triggers on secondary state changes.         |
| Sleep lights                        | entity list      | blank       | Lights assigned to this group.                                                                  |
| States which this group should be on (Sleep lights) | list | `occupied` | Area states that trigger this group.                                                           |
| When should we control this light? (Sleep lights) | multi-choice  | occupancy + state | Same behavior explanation as above.                                                            |
| Accent lights                       | entity list      | blank       | Lights assigned to this group.                                                                  |
| States which this group should be on (Accent lights) | list | `occupied` | Area states that trigger this group.                                                           |
| When should we control this light? (Accent lights) | multi-choice  | occupancy + state | Same behavior explanation as above.                                                            |
| Task lights                          | entity list      | blank       | Lights assigned to this group.                                                                  |
| States which this group should be on (Task lights) | list | `occupied` | Area states that trigger this group.                                                           |
| When should we control this light? (Task lights) | multi-choice  | occupancy + state | Same behavior explanation as above.                                                            |

!!! warning "💡 **Control Timing Notes:** "
    - **Occupancy only:** Light group reacts when entering the room (clear → occupied) but not if the area enters a secondary state while already occupied.
    - **State only:** Light group reacts when a secondary state changes but **not** when first entering the room.
    - **Both selected (default):** Reacts on room entry **and** secondary state changes.

## 🔁 Automatic Control

Magic Areas can automatically turn lights on or off based on:

- **Primary presence state**: `occupied` or `clear`
- **Secondary states**: `dark`, `extended`, `sleep`, etc.

### 🌒 The `dark` State

If a `dark` sensor is configured:

- Lights turn on only when the area is both **occupied** _and_ **dark**.
- Otherwise, lights turn on anytime the area becomes occupied.

!!! note
    ✅ If the area becomes dark while already occupied, lights will turn on immediately.

#### Dark State Behavior Matrix

| Area State | Dark Configured? | Dark State | Lights Will… |
|------------|-----------------|------------|--------------|
| `occupied` | ❌ No           | N/A        | Turn on      |
| `occupied` | ✅ Yes          | `off`      | Do nothing   |
| `occupied` | ✅ Yes          | `on`       | Turn on      |
| `clear`    | ❌ No           | N/A        | Turn off     |
| `clear`    | ✅ Yes          | `off`      | Turn off     |
| `clear`    | ✅ Yes          | `on`       | Turn off     |

### 💡 Automatically Turning Off Lights

When an area becomes `clear`, **all lights are turned off**, regardless of secondary state.
Disable **Light Control** to override.

## 🚀 How it Works

Light groups are tied to area states:

- **States:** Each group activates only when the area is in selected states (primary or secondary).
- **Control timing:** Decide if groups react on **occupancy**, **secondary state changes**, or both (recommended).

**Example:**
- `Sleep Lights` set to **occupancy only**: will turn on when you enter a bedroom at night, but not if `sleep` state activates while already inside.
- `Accent Lights` set to **state only**: will turn on whenever the `extended` state is activated, even if already inside.

## 🧠 Usage Examples

### 🛋️ TV ambiance with accent lights

- **Group:** Accent Lights
- **State:** `accented`
- **Trigger Mode:** `state` (media player, for exmaple)
- **Why:** Soft lighting during movie nights or relaxing evenings.

### 💤 Nighttime routine in bedrooms

- **Group:** Sleep Lights
- **State:** `sleep`
- **Trigger Mode:** `occupancy`
- **Why:** Turn on softer lights when entering the room at night.

## 🎚️ Brightness and Color Temperature

Magic Areas **does not control brightness or color temperature**.
Use integrations like:

- [Adaptive Lighting](https://github.com/basnijholt/adaptive-lighting/)
- [Circadian Lighting](https://github.com/claytonjn/hass-circadian_lighting)

These handle brightness/temperature better and are fully compatible with Magic Areas.
