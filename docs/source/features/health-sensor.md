# Area Health Sensors

The **Area Health** feature monitors the safety and integrity of an area by aggregating signals from critical sensor types—alerting you when something might be wrong.

These sensors work similarly to [[aggregate|Aggregation]] binary sensors but specifically target key **health-related device classes**.

## 🩺 What it tracks

The Area Health feature combines the following `binary_sensor.device_class` types into a single `binary_sensor.magic_areas_health_$area_health_problem` entity:

- `gas` – Detects gas leaks (e.g., natural gas, propane)
- `smoke` – Detects smoke or fire
- `moisture` – Detects water leaks
- `problem` – Generic problem indicators (e.g., device errors)
- `safety` – General safety-related sensors

!!! failure
    If you use the `moisture` device class for non-leak purposes, make sure to **exclude** those sensors manually to avoid false alarms.

These aggregated sensors are available per-area and supported in **meta-areas** like `Interior`, `Exterior`, or `Global`, giving you a comprehensive view of your home's status.

## 🔔 Sample Use Case: Notifications

Use the Area Health sensor to trigger automations that notify you if a problem is detected anywhere in your home.

### 🛠️ Sample Automation

```yaml
alias: Notify on degraded area health
description: ""
triggers:
  - platform: state
    entity_id: binary_sensor.magic_areas_health_global_health_problem
    from: "off"
    to: "on"
  - platform: time_pattern
    hours: "/1"
conditions:
  - condition: state
    entity_id: binary_sensor.magic_areas_health_global_health_problem
    state: "on"
actions:
  - service: notify.residents_mobile_app
    data:
      title: Area Issue!
      message: >-
        {% for m_entity in state_attr('binary_sensor.magic_areas_health_global_health_problem', 'entity_id') %}
        {%- if 'health_problem' not in m_entity or not is_state(m_entity, 'on') %}{% continue %}{% endif -%}
        {% set entities = state_attr(m_entity, 'entity_id') -%}
        {% if entities %}
        {{ state_attr(m_entity, 'friendly_name')|replace(' Area Health','') }}
        {%- for entity in entities %}
        {%- if is_state(entity, 'on') %}
        - {{ state_attr(entity, 'friendly_name') }}
        {% endif %}
        {% endfor %}
        {% endif %}
        {% endfor %}
mode: single
```

This automation:

- Sends a notification whenever a health issue is detected globally.
- Continues sending hourly reminders while the issue is unresolved.
- Lists each affected area and the specific triggered sensors in the message.

!!! tip
    🗣️ If you’re using TTS notification service tied to an [Area-Aware Media Player](https://github.com/jseidl/hass-magic_areas/wiki/Area-Aware-Media-Player), you can add a `tts.notify_area_aware` service call in the `actions` block to **speak the warning aloud** in the appropriate area.

## 💡 Why use Area Health?

- Get **real-time alerts** for important safety issues.
- Avoid manually checking dozens of sensors—let Magic Areas watch them for you.
- Build automations that respond to **area-level** issues, not just individual devices.

!!! tip
    You can use individual area health sensors for room-level automations, or use meta-areas (like `Interior`) for whole-home monitoring.
