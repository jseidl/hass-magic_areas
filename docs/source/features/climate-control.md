# Climate Control

Climate control allows you to map area states to climate device presets.

When configuring Climate Control, you will first be asked to select a climate device which Magic Areas will then pull the available presets for mapping in the next screen.

!!! tip
    🧠 Climate control is best used in meta-areas such as Interior or Floor-meta areas. Meta-areas’ secondary states (such as sleep 🛌) are calculated from child areas. Secondary state calculation method for meta-areas is available in the UI.

## ⚙️ How it works

Pretty simple: when the state changes (either primary [`occupied`/`clear`] or secondary [`sleep` / `dark` / `extended`]), the configured climate device will be set to the mapped preset.

!!! warning
    If you leave a preset mapping blank, climate control will not change any presets.
    This is useful if you don’t want climate preset to change immediately, but only after being occupied for an `extended` time ⏳.

## 🧠 Usage Examples

### 🛌 Lower temperature at night

Map the `sleep` state to a cooler preset like `sleep` or `eco`.

- **Why**: Many people sleep better at lower temperatures.
- **How**: When the meta-area enters the `sleep` state, Magic Areas sets the climate to your `sleep` preset automatically.

### 🌅 Resume comfort in the morning

Map the `occupied` state to a `home` or `comfort` preset.

- **Why**: As the home becomes active in the morning, you want a warmer or cooler preset for comfort.
- **How**: As soon as presence is detected (i.e., `occupied`), Magic Areas switches the climate back to the desired preset.

### ⏳ Delay climate change until extended occupancy

Leave the `occupied` state preset blank, but set a preset for `extended`.

- **Why**: Avoid premature heating/cooling for brief visits in areas like a study or guest room.
- **How**: The preset only changes after the area has been occupied for an extended period.

### 🌇 Reduce energy use when no one’s home

Map the `clear` state to an energy-saving preset like `away` or `eco`.

- **Why**: No one's home, no need to run HVAC at full blast.
- **How**: When the entire meta-area becomes `clear`, Magic Areas switches the climate system to a lower-energy mode.

### 🏠 Floor-level climate control

Use climate control on a `floor` meta-area instead of per-room.

- **Why**: Helps prevent conflicting presets if individual rooms are occupied while the floor as a whole is still considered `clear`.
- **How**: Configure the floor-level meta-area to manage the climate device, using secondary states calculated from child rooms.

!!! warning
    ✅ Make sure your climate devices support the required presets (`home`, `away`, `eco`, `sleep`, etc.), or customize them according to your climate integration.
