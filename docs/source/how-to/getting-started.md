# Getting Started

You’ve already [[installed|Installation]] Magic Areas—awesome! 🎉
Now let’s walk through how to set up your home with Magic Areas to make every room *magical*.

## 🏠 Step 1: Define Your Areas

If you haven’t paid much attention to Home Assistant’s **Area Registry** before, now is the time!

Go to **Settings > Areas** and make sure every room or zone in your home is represented as an area. Since you're here, if your home is multi-story, configure the each Floor and assign areas to them.

Once you’ve created your areas, go to **Settings > Devices & Services > Integrations**, click **+ Add Integration**, search for **Magic Areas**, and create a Magic Area for each of your defined areas.

## ⚙️ Step 2: Configure Each Magic Area

After creating a Magic Area, go back to the **Integrations** page, find the Magic Areas entry for that area, and click **Configure**.

All options are available in the UI, and every setting includes a helpful description.

> 💬 Not sure what a setting means? Join us on [Discord](https://discord.gg/3yu2F7bSaT)—we’d love to help!

## 📥 Step 3: Include or Exclude Entities

Magic Areas uses entities assigned to areas in Home Assistant to determine presence and apply features.

However, not all entities can be assigned to areas (e.g., those without a `unique_id`). No worries! You can:

- Use the `Include Entities` setting to manually assign unsupported entities to your Magic Area.
- Use the `Exclude Entities` setting to remove entities from *all* Magic Areas features (useful if something is incorrectly triggering presence or behavior).

!!! note
    Includes/excludes apply globally across all features. Feature-specific exclusions are not currently supported.

## ✨ Step 4: Enable Features

Magic Areas includes many powerful [[features|Features]]—from presence-based lighting to climate control and media routing.

After the basic configuration, you’ll be prompted to select which features you want to enable for the area. The next screens will let you customize them in detail. Each setting includes descriptions to help you choose what fits best.

## 🛠️ Something’s Not Right?

No worries! Try the following:

- Visit our [[Troubleshooting]] guide
- Join our [Discord server](https://discord.gg/3yu2F7bSaT) for real-time help
- Or [open an issue](https://github.com/jseidl/hass-magic_areas/issues) on GitHub

---

Now go forth and bring your house to life—with Magic Areas ✨
