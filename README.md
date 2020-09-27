# Magic Areas custom_component for Home Assistant
Tired of writing the same automations, over and over, for each of your rooms? Annoyed that some entities can't be tied to `Areas` in the `Area Registry`? Would like to have a single `motion` sensor that is grouped to all your other motion sensors in that area? 

**Magic Areas** is here for you!

## Features
* Uses multiple type of sensors for determining presence on an area.
	* `media_player`,  `binary_sensors` (`motion`,`presence`,`occupancy`and `door`) are supported.
* Loads areas from `Area Registry` -- _No need of handling them elsewhere!_.
* Support inclusion of non-device-tied entities (non-discovery MQTT/Template sensors).
* Support exclusion of entities.
* Automatic turn lights on! (All or user-defined).
* Automatic turn of lights, climate and media devices.
* Creates a `Health` sensor (triggered by `binary_sensors` with `problem`,`smoke`,`moisture`,`safety` and `gas` device classes) for each area
* Creates a `Presence Hold` switch to manually override area presence
* Creates aggregation sensors for:
	* Motion sensors
	* Door sensors
	* Window sensors
	* Leak sensors

## Installation

Copy `custom_components/magic_areas` folder into your Home Assistant's `custom_component` folder, then include the following into your `configuration.yaml` file (or in a `package`):
```
magic_areas:
```
That is all you need for using the default parameters and `Area Registry`-tied devices only. See below for configuration options.

## Configuration

Configuration options for `Magic Areas` are on a per-area basis. The `YAML` keys for each area are their `slugify`'ed names (see area's `entity_id` on the generated `binary_sensors`).

Example configuration:
```
magic_areas:
  living_room:
    automatic_lights:
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
|`control_lights`|Automatically turn lights on/off on presence state change            |`True`             |
|`control_climate`|Automatically turn climate on/off on presence state change            |`True`             |
|`control_media`|Automatically turn media devices off on presence state clear            |`True`             |
|`automatic_lights`|List of lights `entity_id`s that will turn on when presence is detected in the area            |`empty` (All lights in the area)            |
|`include_entities`|List of `entity_id`s that will be considered from this area. Useful for non-discovery MQTT and Template entities.            |`empty` (Area registry-tied entities only)            |
|`exclude_entities`|List of `entity_id`s that will __NOT__ be considered from this area. Useful for excluding entities brought in by the Area Registry.            |`empty` (None)            |
|`presence_sensor_device_class`|List of `device_class` of `binary_sensors` that will be considered as presence sensors. This override the default, does not adds on top. Make sure to list __ALL__ the `device_class` needed.            | `['motion','occupancy','presence']`            |
|`clear_timeout`|Seconds the area should wait since the last presence sensor goes `off` until changing state to `clear`.            |`60`             |
|`update_interval`|How often to check on the presence sensors (if `event_state_change` callback was missed).            |`15`             |
|`on_states`|Which states are considered `on`.            |`['on','playing','home','open']`             |
|`icon`|Area presence `binary_sensor` icon.            |`mdi:texture-box"`             |

## Problems/bugs, questions?

Open up a ticket!

