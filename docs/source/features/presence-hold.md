# ⏸️ Presence Hold

The **Presence Hold** feature creates a dedicated [switch](https://www.home-assistant.io/integrations/switch/) for an area that acts as a **manual override presence sensor**.

This allows you to **force the area’s presence state to `occupied`** by toggling the switch on, regardless of other presence detections.

## ⚙️ Configuration Options

| Option                | Type    | Default | Description                                                                 |
|-----------------------|--------|---------|-----------------------------------------------------------------------------|
| Timeout | Integer   | `0` (disabled)     | If defined, presence hold will automatically turn off after this timeout expires (minutes). |

## 🚀 How it Works

The presence hold switch is automatically added as a "presence entity" in the area and will trigger the regular logic as any other presence entity.

- Turning the Presence Hold switch **`on`** forces the area presence to `occupied`
- When **`off`**, presence detection behaves normally based on configured sensors and logic
- If a `timeout` is set, the switch automatically turns off after the timeout period

## Use Cases

- Manually mark a room as occupied even if presence sensors don’t detect anyone (e.g., pets, guests)
- Keep an area “occupied” temporarily for testing automations or events
- Override presence during unusual circumstances like maintenance or cleaning

---

Simple and powerful, Presence Hold gives you manual control over presence states whenever you need it.
