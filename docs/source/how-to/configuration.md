# ⚙️ Configuration

Magic Areas configuration is divided into four main sections, plus additional configuration options for enabled features.

Each section allows you to fine-tune how areas behave, how presence is detected, and how states are managed.

## 🏠 Basic Area Options

These options control the general behavior of the area.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **Area type** | `string` | `interior` | Defines the area type. Options: `interior`, `exterior`. Used for meta-area calculations. |
| **Include entities** | `list<entity>` | `[]` | Force-add entities to the area, even if not assigned to it in Home Assistant. |
| **Exclude entities** | `list<entity>` | `[]` | Force-remove entities from the area. Useful if you want them in Home Assistant but excluded from Magic Areas calculations. |
| **Automatic reload on registry updates** | `bool` | `true` | Automatically reloads the area if a new device or entity is added/removed. |
| **Ignore diagnostic/config entities** | `bool` | `true` | Prevents Magic Areas from using diagnostic/config sensors (e.g., CPU temperature) that could skew aggregates. |

## 🚶 Presence Tracking Options

These options define how presence is detected and maintained within an area.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **Platforms** | `list<string>` | `media_player`, `binary_sensor` | Platforms used for presence sensing. Options: `media_player`, `binary_sensor`, `device_tracker`, `remote`. |
| **Presence sensor device classes** | `list<string>` | `motion`, `occupancy`, `presence` | Device classes of binary sensors considered as presence sensors. Supports all binary sensor classes. |
| **Keep-only entities** | `list<entity>` | `[]` | Entities that will only be considered if the area is already occupied (triggered by another sensor). |
| **Clear timeout** | `int (minutes)` | `1` | Time to wait before clearing the area after no presence is detected. |

## 🧠 Advanced Area State Tracking

Area states go beyond basic presence (`occupied`/`clear`) and allow secondary states such as `dark`, `sleep`, or `extended`.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **Area light sensor** | `entity` | – | Binary sensor of type `light` or `sun.sun`. Used to determine whether the area is `dark`. Recommended: `sun.sun` or an exterior light sensor to avoid feedback loops. |
| **Accented state entity** | `entity` | – | Sets the area to `accented` when this entity is `on`. |
| **Sleep state entity** | `entity` | – | Sets the area to `sleep` when this entity is `on`. |
| **Extended state time required** | `int (minutes)` | `5` | Time after which the area enters the `extended` state if still occupied. |
| **Clear timeout (sleep)** | `int (minutes)` | `1` | Timeout before clearing the area when in `sleep` state. |
| **Clear timeout (extended)** | `int (minutes)` | `1` | Timeout before clearing the area when in `extended` state. |

## ✨ Feature Selection

This section provides checkboxes in the UI for enabling or disabling specific Magic Areas features.

!!! info
    📖 See the [Features](../features/index.md) page for the full list of available features.

## 🔧 Feature-Specific Configuration

Once features are enabled, each comes with its own configuration options.

!!! info
    📘 Refer to the corresponding feature documentation under [Features](../features/index.md) for detailed setup instructions.

✅ That’s it! You now have a flexible configuration system where you can start simple and layer in advanced states and features as needed.
