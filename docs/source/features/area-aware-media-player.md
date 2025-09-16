# Area-Aware Media Player

The **Area-Aware Media Player** 🏠 is a virtual `media_player` entity that **automatically routes `play_media` actions** to actual `media_player` devices in **occupied areas only**.

This is especially useful for:

- 📢 **TTS notifications** ([Text-to-Speech](https://www.home-assistant.io/integrations/notify.tts/))
- 🔔 **Context-aware alerts**
- 🧘 Preventing disruptions in quiet or empty rooms

Instead of broadcasting audio throughout your home, this feature ensures messages are **only played where someone is present**.

!!! tip
    Works great with [Home Assistant Alerts](https://www.home-assistant.io/integrations/alert/) and other notification automations.

## 🎛️ Configuration Options

!!! warning
    This feature must be **enabled per area**. If an area has it disabled, it will not participate in media routing—even if it's occupied.

### 🔊 Notification Devices

Select which `media_player` entities in an area will be used for playback.

- Leave blank to include **all media players in the area** (default)
- Or choose specific ones (e.g., only cast devices or smart speakers)

### 🕒 Notify States

Define which area states allow notifications to be played in that area.

- **Default:** `extended`
  (Only plays in areas that have been occupied for a while)
- You may include any of the following:
  - `occupied`
  - `accented`
  - `extended`
  - `sleep` *(use with caution)*
  - Or any custom-defined secondary state

💡 *Use `occupied` for immediate feedback, or restrict to `extended` for less frequent areas like bedrooms.*

## 🚀 How It Works

When you send a `play_media` command to `media_player.magic_areas_area_aware_media_player_global`, Magic Areas will:

1. **Check each area** to see if it's eligible (feature enabled, state allowed, devices available)
2. **Send the media** to all appropriate devices in those areas

### ✅ Playback Rules

- Only **occupied areas** matching the configured states will receive audio
- Media is **duplicated** across multiple areas if more than one qualifies
- **No playback** occurs in sleeping, empty, or excluded areas

## 📣 Example: TTS Notification

```yaml
service: media_player.play_media
target:
  entity_id: media_player.magic_areas_area_aware_media_player_global
data:
  media_content_type: "music"
  media_content_id: "media-source://tts/google_translate?message=The+garage+door+was+left+open"
```

This will play the message **only in occupied areas** using configured media players.


## 🗣️ Example: Notify TTS Integration

You can use this feature as a **TTS notification target** by configuring a `notify` service in your `configuration.yaml`:

```yaml
notify:
  - platform: tts
    name: area_aware_notify
    entity_id: tts.piper
    media_player: media_player.magic_areas_area_aware_media_player_global
```

Then you can use it in your automations like this:

```yaml
service: notify.area_aware_notify
data:
  message: "There's a problem in the laundry room."
```

This will speak the message **only where people are present**.


## 🔗 Related

- See [Area Health](health-sensor.md) for how you can combine this with intelligent alerting.
- Read more about [TTS notifications](https://www.home-assistant.io/integrations/notify.tts/).
