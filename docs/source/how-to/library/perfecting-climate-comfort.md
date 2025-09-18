# 🌡 Perfecting Climate Comfort

Have you ever noticed that your temperature sensors don’t match how your home actually feels?
After some research, I found that even when my HVAC setpoint was consistent, the same setpoint **felt colder at night than during the day**, which intrigued me and prompted a deeper look.

This tutorial walks through my approach to measuring a more realistic **“Indoor Feels Like” temperature** using Home Assistant, Magic Areas aggregates, and template sensors — and how this lets us tune HVAC presets for better comfort and energy efficiency.

!!! info
    If all your areas are conditioned and you don’t have upstairs exterior spaces or unconditioned rooms, most of this can be skipped. You can jump straight to the **Indoor Feels Like** section.

    Using Magic Areas aggregates makes this easier, but you can do it with manually created sensors as well. The goal is to have more meaningful humidity and temperature readings for interior and each floor.

## ❓ The problem

My home has areas that skew aggregate readings:

- **Interior unconditioned spaces**, like the garage or laundry room
- **Exterior upstairs areas**, like a balcony

Including these in floor-level aggregates made temperature and humidity readings less representative of how conditioned areas actually feel.
Additionally, I noticed that even with a constant HVAC setpoint, **comfort perception changed between day and night**, which standard sensors did not explain.

## 🛠 Separating unconditioned areas

First, I created two groups containing sensors to **exclude**:

- **Unconditioned Areas Temperature** (temperature aggregate entities)
- **Unconditioned Areas Humidity** (humidity aggregate entities)

These groups are used in later template sensors to filter out unconditioned areas from calculations.

## 📊 Conditioned Areas Template Sensors

Next, I created template sensors for **humidity and temperature** for each floor, excluding the unconditioned areas.

Example: **Downstairs Conditioned Areas Humidity**

```jinja
{% set downstairs = expand('sensor.magic_areas_aggregates_downstairs_aggregate_humidity') %}
{% set unconditioned = expand('sensor.unconditioned_areas_humidity') %}
{% set conditioned = downstairs | rejectattr('entity_id', 'in', unconditioned | map(attribute='entity_id') | list) | list %}
{% set temps = conditioned | map(attribute='state') | map('float', default=none) | select('!=', none) | list %}
{{ (temps | average) if temps | length > 0 else 'unknown' }}
```

The same logic is applied to **temperature** and to **upstairs areas**.

## 🏗 Aggregating Conditioned Areas Globally

After creating per-floor conditioned sensors, I grouped them to produce:

- **Conditioned Areas Humidity** (global)
- **Conditioned Areas Temperature** (global)

This gives a single reliable measurement for all conditioned interior areas.

## 🌬 Calculating “Indoor Feels Like”

Finally, I created a template sensor to calculate **Indoor Feels Like**, based on:

- Conditioned interior temperature
- Conditioned interior humidity
- Exterior temperature

```jinja
{% set modifier = 1 %}
{% set humidity_interior = states('sensor.conditioned_areas_humidity')|float(0) %}
{% set humidity_modifier = 0 %}
{% if humidity_interior >= 60 %}
  {% set humidity_modifier = modifier %}
{% elif humidity_interior <= 30 %}
  {% set humidity_modifier = modifier*-1 %}
{% endif %}

{% set temperature_modifier = 0 %}
{% set exterior_temperature = states('sensor.magic_areas_aggregates_exterior_aggregate_temperature')|float(0) %}
{% if exterior_temperature >= 85 %}
  {% set temperature_modifier = modifier %}
{% elif exterior_temperature <= 50 %}
  {% set temperature_modifier = modifier*-1 %}
{% endif %}

{% set interior_temperature = states('sensor.conditioned_areas_temperature')|float(0) %}
{{ interior_temperature + humidity_modifier + temperature_modifier | float | round(2) }}
```

- **Humidity modifier**: adds/subtracts based on interior humidity (high humidity feels warmer, low feels cooler)
- **Temperature modifier**: accounts for extreme exterior temperatures influencing perceived comfort
- `modifier` can be tuned; after testing, **+1 °F** gave the most accurate results

## 📈 Observations

- Filtering out unconditioned areas (garage, laundry) and exterior upstairs areas (balcony) gives a much more realistic interior temperature and humidity.
- Using the **Indoor Feels Like** sensor explained why the same HVAC setpoint felt colder at night than during the day.
- Users with all conditioned interior areas and no exterior upstairs areas can skip directly to the Indoor Feels Like calculation.
- Magic Areas aggregates make this easier, but the same principle can be applied manually.
- Now, I have **more meaningful humidity and temperature sensors** for interior and each floor, which improves comfort analysis and automation.

## ⚙️ HVAC Presets and Automation

With reliable Indoor Feels Like readings, it’s now possible to **tune HVAC presets** intelligently:

- Climate Control can automatically switch to a **more relaxed temperature range during `sleep` hours**
- Comfort is maintained without unnecessary energy use
- Automations can adjust setpoints based on actual conditioned area conditions, rather than raw aggregates

## ✅ Takeaways

By combining:

- Conditioned area aggregates
- Template sensors to filter out unconditioned areas
- A “feels like” calculation factoring humidity and exterior temperature

…it’s possible to get an **Indoor Feels Like** sensor that closely matches actual comfort.
This provides actionable insights to **tune HVAC schedules**, improve night-time comfort, and achieve **better energy efficiency** in your home.
