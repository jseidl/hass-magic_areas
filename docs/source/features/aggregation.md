# Aggregation

This feature creates aggregates for all `sensor` and `binary_sensor` in a given area according to their `device_class` and `unit_of_measurement` tuple.

!!! note
    The entities are created with the following template `(binary_?)sensor.magic_areas_aggregates_{area}_aggregate_{device_class}`. An `_{unit_of_measurement}` suffix will be added if there are more than one `unit_of_measurement` for the same `device_class`.

The feature has an `Aggregate Min Entities` parameter (defaulted to `2`) which will only create aggregate entities if the entity count for a given tuple is greater than this number. If you want aggregates to be always created, set this value to `1`.

**This feature requires `unit_of_measurement` to be set for all entities to be aggregated**

## 📊 Aggregation methods

* Binary Sensor: If one of the entities is `on`, then the aggregate is `on`. Aggregate will be `off` if all entities are `off`.
* Sensor: All values will be mean averages, except for `power`, `current` and `energy` which will be sums.

## Example use cases

### 🔥 Temperature management

Instead of referencing individual temperature sensors in each room, use `sensor.magic_areas_aggregates_{area}_aggregate_temperature` to get the average temperature of an entire area. This is especially useful in:

* Automating climate systems based on a whole area's average temperature
* Comparing average temperatures across floors or wings of a building

### 💨 Air quality & ventilation

Aggregate `co2`, `humidity`, or `voc` levels into one sensor like `sensor.magic_areas_aggregates_{area}_aggregate_humidity` to:

* Trigger fans or dehumidifiers when humidity is too high
* Monitor and act on air quality trends over time without manually aggregating data

### ⚡ Power monitoring

Use `sensor.magic_areas_aggregates_{area}_aggregate_power` to monitor combined power consumption for all devices in an area:

* Automatically turn off non-essential devices when usage spikes
* Create dashboards that show power consumption per area (e.g., Kitchen vs. Living Room)

### 🧠 Simplified automations

Using aggregates makes automation logic cleaner and more resilient:

```yaml
- alias: Turn off humidifier when area unoccupied
  trigger:
    - platform: state
      entity_id: binary_sensor.magic_areas_presence_tracking_bedroom_area_state
      to: "off"
      for: "5m"
  action:
    - service: humidifier.turn_off
      target:
        entity_id: humidifier.bedroom_humidifier
```

Instead of checking multiple sensors individually, you just check the aggregate.
