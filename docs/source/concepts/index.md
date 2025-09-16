# 🧠 Concepts

Before diving into the features of Magic Areas, it’s important to understand the **core concepts**. These lay the groundwork for how the integration works and why it’s so powerful.

Magic Areas extends Home Assistant’s built-in **Areas** model with advanced logic and automation. It does this by sensing **presence**, calculating **states**, and even creating **meta-areas** that combine multiple rooms or zones.

---

## 📍 Presence Sensing
Presence sensing is at the heart of Magic Areas.
By monitoring entities such as motion sensors, device trackers, and media players, Magic Areas determines if an area is **occupied** or **clear**.

➡️ Learn more: [Presence Sensing](presence-sensing.md)

---

## 🏠 Area States
Beyond simple presence, Magic Areas tracks **secondary states** like `dark`, `sleep`, and `extended`. These states allow automations to adapt to context—for example, using different lighting at night versus during the day.

➡️ Learn more: [Area States](area-states.md)

---

## 🌍 Meta-Areas
Meta-Areas are **virtual areas** that represent collections of physical areas. Examples include:

* **Interior** (all indoor areas)
* **Exterior** (all outdoor areas)
* **Floors** (all rooms on a specific floor)
* **Global** (the entire home)

Meta-areas unlock powerful whole-home automations such as turning off all lights, setting climate modes, or routing notifications.

➡️ Learn more: [Meta-Areas](meta-areas.md)

---

✨ With these concepts in mind, you’ll be ready to explore the full power of Magic Areas and start building smarter, more context-aware automations in your home.
