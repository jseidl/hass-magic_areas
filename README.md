# Magic Areas for Home Assistant
![Magic Areas](https://raw.githubusercontent.com/home-assistant/brands/master/custom_integrations/magic_areas/icon.png)

![Build Status](https://github.com/jseidl/hass-magic_areas/actions/workflows/combined.yaml/badge.svg) [![Discord](https://img.shields.io/discord/928386239789400065.svg?color=768AD4&label=Discord)](https://discord.gg/8vxJpJ2vP4) [![Latest release](https://img.shields.io/github/v/release/jseidl/hass-magic_areas.svg)](https://github.com/jseidl/hass-magic_areas/releases) [![GitHub latest commit](https://badgen.net/github/last-commit/jseidl/hass-magic_areas)](https://GitHub.com/jseidl/hass-magic_areas/commit/) [![GitHub contributors](https://badgen.net/github/contributors/jseidl/hass-magic_areas)](https://GitHub.com/jseidl/hass-magic_areas/graphs/contributors/)

Tired of writing the same automations, over and over, for each of your rooms? You wish Home Assistant just figured out all entities you have in an area and **magically** started being smarter about them? 

Magic Areas is the batteries that were missing! Would like to have a single `motion` sensor that is grouped to all your other motion sensors in that area? What if all (most) of your `sensor` and `binary_sensor` entities had aggregates (grouping/average), PER AREA? Would you like for lights and climate devices to turn on and off **MAGICALLY** whenever an area is occupied/clear?

If you think all of the above features are freaking awesome, **Magic Areas** is here for you!

## Features

* Uses multiple type of sensors for determining presence on an area.
*  `media_player`, `binary_sensors` ([all listed types](https://www.home-assistant.io/integrations/binary_sensor/)) are supported
* Loads areas from `Area Registry` -- _No need of handling them elsewhere!_.
* Support exclusion of entities you don't want to be considered.
* Support inclusion of entities not in the Area Registry (i.e. integrations that don't define an `unique_id`).
* Automatic turn climates and lights on! (All or user-defined).
* Creates lights groups which reacts to different area states!
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

## Installation

_Magic Areas_ is available on HACS! For installation instructions check the installation [wiki](https://github.com/jseidl/hass-magic_areas/wiki/Installation).

## Configuration
Configuration options for `Magic Areas` are on a per-area basis.

> Before you start: Please make sure you understand all the **Concepts** on the [wiki](https://github.com/jseidl/hass-magic_areas/wiki).

Go to **Configuration** > **Integrations**. You shall see the *Magic Areas* integration and configure each area (and [Meta-Areas](https://github.com/jseidl/hass-magic_areas/wiki/Meta-Areas)!). 

See all configuration options in the [wiki](https://github.com/jseidl/hass-magic_areas/wiki/Configuration).

## Problems/bugs, questions, feature requests?

Please enable debug logging by putting this in `configuration.yaml`:

```yaml
logger:
    default: warning
    logs:
        custom_components.magic_areas: debug
```

As soon as the issue occurs capture the contents of the the log (`/config/home-assistant.log`) and open up a [ticket](https://github.com/jseidl/hass-magic_areas/issues)!
