# Simply Magic Areas for Home Assistant

This is a fork of https://github.com/jseidl/hass-magic_areas building on this base.

![Simple Magic Areas](https://raw.githubusercontent.com/home-assistant/brands/master/custom_integrations/simply_magic_areas/icon.png)

![Build Status](https://github.com/pinkfish/hass-simply-magic-areas/actions/workflows/validation.yaml/badge.svg) ![Test Status](https://github.com/pinkfish/hass-simply-magic-areas/actions/workflows/test.yaml/badge.svg) [![Latest release](https://img.shields.io/github/v/release/pinkfish/hass-simply-magic-areas.svg)](https://github.com/pinkfish/hass-simply-magic-areas/releases) [![GitHub latest commit](https://badgen.net/github/last-commit/pinkfish/hass-simply-magic-areas)](https://github.com/pinkfish/hass-simply-magic-areas/commit/) [![GitHub contributors](https://badgen.net/github/contributors/pinkfish/hass-simply-magic-areas)](https://GitHub.com/pinkfish/hass-simply-magic-areas/graphs/contributors/)

Tired of writing the same automations, over and over, for each of your rooms? You wish Home Assistant just figured out all entities you have in an area and **magically** started being smarter about them? 

Simply Magic Areas is the batteries that were missing! Would like to have a single `motion` sensor that is grouped to all your other motion sensors in that area? What if all (most) of your `sensor` and `binary_sensor` entities had aggregates (grouping/average), PER AREA? Would you like for lights and climate devices to turn on and off **MAGICALLY** whenever an area is occupied/clear?

If you think all of the above features are freaking awesome, **Simply Magic Areas** is here for you!

## Features

* Uses multiple type of sensors for determining presence on an area.
*  `media_player`, `binary_sensors` ([all listed types](https://www.home-assistant.io/integrations/binary_sensor/)) are supported, humidity
* Support exclusion of entities you don't want to be considered.
* Support inclusion of entities not in the Area Registry (i.e. integrations that don't define an `unique_id`).
* Automatically turn climates and lights on! (All or user-defined).
* Control light dim based on illuminance in the room
* Automatically turn off lights, climate and media devices when a room is clear
* Automatically turn on/off fans when the area is in extended mode.
* Automatically turn on/off fans when the humidy changes and use this to control occupancy.
* Creates a `Health` sensor (triggered by `binary_sensors` with `problem`, `smoke`, `moisture`, `safety` and `gas` device classes) for each area
* Creates a `Presence Hold` switch to manually override area presence
* Creates lights groups which reacts to different area states!
* Creates aggregation sensors for your `binary_sensor` such as:
  * Motion sensors
  * Door sensors
  * Window sensors
  * Leak sensors
* Creates average (and sums) sensors for all your `sensor` needs
* Creates global (interior/exterior) aggregate and average sensors
* Area-Aware Media Player: Forward `media_play` events to media player entities in occupied areas only!

## Installation

_Simply Magic Areas_ is (not yet) available on HACS! For installation instructions check the installation [wiki](https://github.com/pinkfish/hass-simply-magic-areas/wiki/Installation).

## Configuration
Configuration options for `Simply Magic Areas` are on a per-area basis.

> ⚠️ Before you start: Please make sure you understand all the **Concepts** on the [wiki](https://github.com/pinkfish/hass-simply-magic-areas/wiki).

> 💡 Light Groups won't control any lights unless the `Light Control` switch for that area is turned `on`!

Go to **Configuration** > **Integrations**. You shall see the *Simply Magic Areas* integration and configure each area (and [Meta-Areas](https://github.com/pinkfish/hass-simply-magic-areas/wiki/Meta-Areas)!). 

See all configuration options in the [wiki](https://github.com/pinkfish/hass-simply-magic-areas/wiki/Configuration).

## Differences from Magic Areas

* Use illuminance in the room to control when to turn on the lights, if the illuminance is too high, no lights.
* Change from dark to bright for tracking the room, if a bright entity is set then the room lights are not turned on.
* Configuration flow has a lot less options in the standard flow
* Control dim in the various states, by default sleep is 30% and occupied is 100%
* Move to one state, not two, that are exposed with a select that can be used in automation
* Create humidity and illuminance sensors to use for control of occupancy and fans
* Control fans in the room when the humidity changes or the state for the room is extended.
* Moved the inclusion/exclusion options and other more complicated settings in an advanced light setting group.

## Problems/bugs, questions, feature requests?

Please enable debug logging by putting this in `configuration.yaml`:

```yaml
logger:
    default: warning
    logs:
        custom_components.simply_magic_areas: debug
```

As soon as the issue occurs capture the contents of the the log (`/config/home-assistant.log`) and open up a [ticket](https://github.com/pinkfish/hass-simply-magic-areas/issues)!
