# Magic Areas custom_component for Home Assistant
Tired of writing the same automations, over and over, for each of your rooms? Annoyed that some entities can't be tied to `Areas` in the `Area Registry`? Would like to have a single `motion` sensor that is grouped to all your other motion sensors in that area? What if all (most) of your `sensor` and `binary_sensor` entities had aggregates (grouping/average), PER AREA?

If you think all of the above features are freaking awesome, **Magic Areas** is here for you!

## Features
* Uses multiple type of sensors for determining presence on an area.
	* `media_player`,  `binary_sensors` (`motion`,`presence`,`occupancy`and `door`) are supported.
* Loads areas from `Area Registry` -- _No need of handling them elsewhere!_.
* Support inclusion of non-device-tied entities (non-discovery MQTT/Template sensors).
* Support exclusion of entities.
* Automatic turn climates and lights on! (All or user-defined).
  * Specify a `disable_entity` for when lights *shouldn't* turn on (e.g. daytime, high luminance etc)
  * Specify a `sleep_entity` and `sleep_lights` to have only your accent lights turn on late in night
* Automatic turn off lights, climate and media devices.
* Creates a `Health` sensor (triggered by `binary_sensors` with `problem`,`smoke`,`moisture`,`safety` and `gas` device classes) for each area
* Creates a `Presence Hold` switch to manually override area presence
* Creates aggregation sensors for your `binary_sensor`:
	* Motion sensors
	* Door sensors
	* Window sensors
	* Leak sensors
* Creates average sensors for all your `sensor`
* Creates global (interior/exterior) aggregate and average sensors 