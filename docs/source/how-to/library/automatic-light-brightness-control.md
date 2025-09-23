# 💡 Automatic Brightness Control

Magic Areas focuses on **when** lights should turn on or off, not **how bright** they should be.
By design, it does not handle brightness levels — that’s best left to dedicated integrations that already do an excellent job and allow for personal preference.

## 🛠 Use the right tool for brightness

If you want automatic brightness control, you’ll need to pair Magic Areas with another integration. A popular choice is [Adaptive Lighting](https://github.com/basnijholt/adaptive-lighting), which can smoothly adjust light levels throughout the day.

!!! tip
    Adaptive Lighting includes a **Sleep Mode** switch, which pairs perfectly with Magic Areas’ **Sleep state**.

## 🌙 Example setup

- Use Adaptive Lighting’s **Sleep Mode** switch as the *Sleep entity* for each area.
- Create automations that toggle the switch depending on your use cases.
- For bedrooms, control each room individually. (e.g. time of day, bed presence, physical button press)
- For shared spaces / common areas, control them together using a `group` of Sleep switches. (e.g. time of day or if bedrooms are on `sleep` mode)

This way, Magic Areas handles the logic of when to turn lights on/off, while Adaptive Lighting decides how bright they should be.

## 🔎 Other options

You don’t have to stick with Adaptive Lighting — there are other integrations worth trying:

- [Adaptive Lighting](https://github.com/basnijholt/adaptive-lighting) (recommended)
- [Flux](https://www.home-assistant.io/integrations/flux/)
- [Lightener](https://github.com/fredck/lightener)
- [Circadian Lighting](https://github.com/claytonjn/hass-circadian_lighting)

You can even combine them if you want to experiment with different effects.

## ✅ Takeaway

Magic Areas doesn’t reinvent brightness control — it lets specialized tools do what they do best.
Pick your favorite brightness integration, connect it with Magic Areas states, and enjoy lighting that’s automatic, adaptive, and tailored to your needs.
