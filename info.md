# Magic Areas custom_component for Home Assistant
Tired of writing the same automations, over and over, for each of your rooms? Annoyed that some entities can't be tied to `Areas` in the `Area Registry`? Would like to have a single `motion` sensor that is grouped to all your other motion sensors in that area? What if all (most) of your `sensor` and `binary_sensor` entities had aggregates (grouping/average), PER AREA?

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
