# Fan Groups

Fan Groups work similarly to a simpler version of the [Generic Thermostat](https://www.home-assistant.io/integrations/generic_thermostat/). This feature groups all fans within an area—whether you have one or many—and allows you to monitor an [[aggregate sensor|Aggregation]] of a selected `device_class` such as `temperature` 🌡️, `humidity` 💧, or `co2` 🫁.

The fans will automatically turn `on` 🔛 when the tracked sensor’s value rises above a configured `setpoint`, and turn `off` 🔘 when it falls below.

## 🛠️ Use Cases

* Turning fans on when it’s too hot 🔥
* Activating bathroom exhaust fans when humidity is too high 💦
* Turning on ventilation fans if CO2 levels become elevated 🏭
