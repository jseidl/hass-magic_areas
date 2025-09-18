# 🧮 Aggregation

The **Aggregation** feature creates aggregate sensors for all `sensor` and `binary_sensor` entities in a given area, grouped by their `device_class` and `unit_of_measurement` tuple.

!!! note
    Entities are created with the template:
    ```
    (binary_?)sensor.magic_areas_aggregates_{area}_aggregate_{device_class}
    ```
    If multiple `unit_of_measurement` values exist for the same `device_class`, an `_{unit_of_measurement}` suffix is added.

This is especially useful for simplifying automations and dashboards, since you can reference a single "aggregate" instead of many individual sensors.

---

## ⚙️ Configuration Options

| Option                  | Type    | Default | Description |
|--------------------------|---------|---------|-------------|
| **Minimum number of entities** | Integer | `2`     | Minimum number of entities required for an aggregate sensor to be created. If you want aggregates always created (even with a single entity), set this to `1`. |
| **Binary sensor device classes**  | Device class list | N/A     | Device classes of [binary_sensor](https://www.home-assistant.io/integrations/binary_sensor/) to aggregate. |
| **Sensor device classes**  | Device class list | N/A     | Device classes of [sensor](https://www.home-assistant.io/integrations/binary_sensor/) to aggregate. |
| **Illuminance threshold**  | Integer | `0` (disabled)     | Magic Areas can automatically create a [threshold](https://www.home-assistant.io/integrations/threshold/) sensor of device class `light` that tracks the aggregated `illuminance` sensor. This is useful for using as an [Area light sensor](../concepts/area-states.md#secondary-states). |
| **Threshold sensor hysteresis**  | Integer | `0`     | [Hysteresis](https://www.home-assistant.io/integrations/threshold/#hysteresis) for the light threshold sensor (percentage of the threshold value). |

---

## 📊 Aggregation Methods

- **Binary Sensor** → Aggregate is `on` if any entity is `on`.
- **Sensor** → Values are averaged, except for `power`, `current`, and `energy`, which are summed.

---

## 💡 Example Use Cases

### 🔥 Temperature Management
Use `sensor.magic_areas_aggregates_{area}_aggregate_temperature` to get the average temperature of a room or floor:
- Automate HVAC systems based on area average temperature
- Compare temperatures across multiple areas

### 💨 Air Quality & Ventilation
Aggregate `co2`, `humidity`, or `voc` into a single sensor like `sensor.magic_areas_aggregates_{area}_aggregate_humidity`:
- Trigger fans or dehumidifiers when humidity rises
- Monitor long-term air quality trends

### ⚡ Power Monitoring
Use `sensor.magic_areas_aggregates_{area}_aggregate_power` to track power consumption for an area:
- Shut off non-essential devices when usage spikes
- Display dashboards comparing power usage per area

### 🧠 Simplified Automations
Aggregates make automation logic cleaner:

```
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