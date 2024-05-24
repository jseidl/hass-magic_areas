# Simple Magic Areas for Home Assistant

This is a fork of https://github.com/jseidl/hass-magic_areas building on this base.

![Simple Magic Areas](https://raw.githubusercontent.com/home-assistant/brands/master/custom_integrations/simple_magic_areas/icon.png)

![Build Status](https://github.com/pinkfish/hass-simple-magic-areas/actions/workflows/validation.yaml/badge.svg) ![Test Status](https://github.com/pinkfish/hass-simple-magic-areas/actions/workflows/test.yaml/badge.svg) [![Latest release](https://img.shields.io/github/v/release/pinkfish/hass-simple-magic-areas.svg)](https://github.com/pinkfish/hass-simple-magic-areas/releases) [![GitHub latest commit](https://badgen.net/github/last-commit/pinkfish/hass-simple-magic-areas)](https://github.com/pinkfish/hass-simple-magic-areas/commit/) [![GitHub contributors](https://badgen.net/github/contributors/pinkfish/hass-simple-magic-areas)](https://GitHub.com/pinkfish/hass-simple-magic-areas/graphs/contributors/)


[![GitHub latest commit](https://badgen.net/github/last-commit/pinkfish/hass-simple-magic-areas)](https://github.com/pinkfish/hass-simple-magic-areas/commit/)


[![GitHub contributors](https://badgen.net/github/contributors/pinkfish/hass-simple-magic-areas)](https://github.com/pinkfish/hass-simple-magic-areas/graphs/contributors/)

Tired of writing the same automations, over and over, for each of your rooms? You wish Home Assistant just figured out all entities you have in an area and **magically** started being smarter about them? 

Magic Areas is the batteries that were missing! Would like to have a single `motion` sensor that is grouped to all your other motion sensors in that area? What if all (most) of your `sensor` and `binary_sensor` entities had aggregates (grouping/average), PER AREA? Would you like for lights and climate devices to turn on and off **MAGICALLY** whenever an area is occupied/clear?

If you think all of the above features are freaking awesome, **Magic Areas** is here for you!

## Features

* Uses multiple type of sensors for determining presence on an area.
*  `media_player`, `binary_sensors` ([all listed types](https://www.home-assistant.io/integrations/binary_sensor/)) are supported
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

_Magic Areas_ is available on HACS! For installation instructions check the installation [wiki](https://github.com/pinkfish/hass-simple-magic-areas/wiki/Installation).

## Configuration
Configuration options for `Magic Areas` are on a per-area basis.

> ⚠️ Before you start: Please make sure you understand all the **Concepts** on the [wiki](https://github.com/pinkfish/hass-simple-magic-areas/wiki).

> 💡 Light Groups won't control any lights unless the `Light Control` switch for that area is turned `on`!

Go to **Configuration** > **Integrations**. You shall see the *Magic Areas* integration and configure each area (and [Meta-Areas](https://github.com/pinkfish/hass-simple-magic-areas/wiki/Meta-Areas)!). 

See all configuration options in the [wiki](https://github.com/pinkfish/hass-simple-magic-areas/wiki/Configuration).

## Problems/bugs, questions, feature requests?

Please enable debug logging by putting this in `configuration.yaml`:

```yaml
logger:
    default: warning
    logs:
        custom_components.magic_areas: debug
```

As soon as the issue occurs capture the contents of the the log (`/config/home-assistant.log`) and open up a [ticket](https://github.com/pinkfish/hass-simple-magic-areas/issues)!
