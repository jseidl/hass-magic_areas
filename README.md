# Magic Areas custom_component for Home Assistant

Tired of writing the same automations, over and over, for each of your rooms? You wish Home Assistant just figured out all entities you have in an area and **magically** started being smarter about them? Annoyed that some entities can't be tied to `Areas` in the `Area Registry`? Would like to have a single `motion` sensor that is grouped to all your other motion sensors in that area? What if all (most) of your `sensor` and `binary_sensor` entities had aggregates (grouping/average), PER AREA?

If you think all of the above features are freaking awesome, **Magic Areas** is here for you!
## Features

* Uses multiple type of sensors for determining presence on an area.
*  `media_player`, `binary_sensors` ([all listed types](https://www.home-assistant.io/integrations/binary_sensor/)) are supported
* Loads areas from `Area Registry` -- _No need of handling them elsewhere!_.
* Support exclusion of entities.
* Support inclusion of entities not in the Area Registry (i.e. integrations that don't define an `unique_id`).
* Automatic turn climates and lights on! (All or user-defined).
* Specify a `disable_entity` for when lights *shouldn't* turn on (e.g. daytime, high luminance etc)
* Specify a `sleep_entity` and `sleep_lights` to have only your accent lights turn on late in night
* Automatic turn off lights, climate and media devices when a room is clear
* Creates a `Health` sensor (triggered by `binary_sensors` with `problem`, `smoke`, `moisture`, `safety` and `gas` device classes) for each area
* Creates a `Presence Hold` switch to manually override area presence
* Creates aggregation sensors for your `binary_sensor` such as:
* Motion sensors
* Door sensors
* Window sensors
* Leak sensors
* Creates average (and sums) sensors for all your `sensor` needs
* Creates global (interior/exterior) aggregate and average sensors
* Area-Aware Media Player: Forward `media_play` events to media player entities in occupied areas only!
* Light Groups: Automatically creates light groups for all ligths in an area

## Installation

### HACS

Go to HACS > Integrations > Click the `+` button > Search `magic areas` > Click on it > Click `Add Repository`.

### Manual mode

Copy `custom_components/magic_areas` folder into your Home Assistant's `custom_component` folder.

Then include the following into your `configuration.yaml` file (or in a `package`):

```
magic_areas:
```

That is all you need for using the default parameters and `Area Registry`-tied devices only. See below for configuration options.

## Configuration
Configuration options for `Magic Areas` are on a per-area basis.

### Config Flow (Preferred)
Go to **Configuration** > **Integrations**. You shall see the *Magic Areas* integration and be able to click each area on the list to show the configuration form. 

Configuration options have a descriptive name.

### YAML (Legacy)
The `YAML` keys for each area are their `slugify`'ed names (see area's `entity_id` on the generated `binary_sensors`).

_Example configuration:_

```
magic_areas:
living_room:
main_lights:
- light.living_room_lamp
include_entities:
- binary_sensor.motion_sensor_lr_1
- binary_sensor.motion_sensor_lr_2
- light.living_room_ceiling

kitchen:
include_entities:
- binary_sensor.motion_sensor_kitchen
```

Below are the full config options:

| Option         |Description                    |Default value                |
|----------------|-------------------------------|-----------------------------|
|`features`|List of features to enable for the area. |`empty (none)` |
|`include_entities`|List of `entity_id`s that will be considered from this area. Useful for entities that can't be added to Areas through Home Assistant. |`empty` (Area registry-tied entities only) |
|`exclude_entities`|List of `entity_id`s that will __NOT__ be considered from this area. Useful for excluding entities brought in by the Area Registry. |`empty` (None) |
|`presence_sensor_device_class`|List of `device_class` of `binary_sensors` that will be considered as presence sensors. This override the default, does not adds on top. Make sure to list __ALL__ the `device_class` needed. | `['motion','occupancy','presence']` |
|`type`| Mark area as exterior (patios, backyards, etc) or interior for global aggregates. |`interior` |
|`clear_timeout`|Seconds the area should wait since the last presence sensor goes `off` until changing state to `clear`. |`60` |
|`update_interval`|How often to check on the presence sensors (if `event_state_change` callback was missed). |`15` |
|`icon`|Area presence `binary_sensor` icon. |`mdi:texture-box"` |
|`on_states`|Which states are considered `on`. |`['on','playing','home','open']` |
|`notification_devices`|Which `media_player` entities to use for notifications on that area. |`empty` (All) |
|`notify_on_sleep`|Whether Area-Aware Media Player should consider this area if it's sleeping or not. |`False`|
|`aggregates_min_entities`|Minimum number of entities of the same type to be considered for aggregation. |`2`|
|`main_lights`|List of entity_ids of lights to turn on. |`empty` (All) |
|`night_entity`|Entity ID to disable automatic light control. |`None` |
|`night_state`|Entity state to disable automatic light control. |`on` |
|`sleep_entity`|Entity ID to enable sleep-mode for automatic light control. |`None` |
|`sleep_state`|Entity state to enablle sleep-mode for automatic light control. |`on` |
|`sleep_lights`|List of entity_ids of lights to turn on when on sleep-mode. |`empty` (Required if `sleep_entity` is defined) |
|`sleep_timeout`|Seconds the area should wait since the last presence sensor goes `off` until changing state to `clear` when sleep mode is activated. |`None (Always use clear_timeout)` |

## Problems/bugs, questions, feature requests?

Please enable debug logging by putting this in `configuration.yaml`:

```yaml
logger:
    default: warning
    logs:
        custom_components.magic_areas: debug
```

As soon as the issue occurs capture the contents of the the log (`/config/home-assistant.log`) and open up a [ticket](https://github.com/jseidl/hass-magic_areas/issues)!