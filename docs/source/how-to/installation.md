# Installation

Magic Areas can be installed in two ways: through [HACS](https://hacs.xyz) (recommended), or manually.

## 🚀 Installing via HACS (Recommended)

Magic Areas is available in the [HACS default repository](https://hacs.xyz/). Just follow these steps:

1. Open HACS in your Home Assistant interface.
2. Go to **Integrations**.
3. Click the **+ Explore & Download Repositories** button.
4. Search for `Magic Areas`.
5. Click **Download** to install.

Once downloaded, restart Home Assistant.

## 🛠️ Manual Installation

Prefer to install manually? Here's how:

1. Download the `magic_areas` integration folder from the [GitHub repository](https://github.com/jseidl/magic-areas).
2. Copy the entire `magic_areas` folder into your Home Assistant's `custom_components/` directory:

```
<config>/custom_components/magic_areas
```

3. Restart Home Assistant.

## ⚙️ Setting Up Magic Areas

Once installed, setup is done entirely through the **Integrations UI**:

1. Go to **Settings > Devices & Services > Integrations**
2. Click **+ Add Integration**
3. Search for `Magic Areas`
4. Select the integration, choose an area to configure, and submit

Magic Areas will now appear on your **Integrations** page. You can click **Configure** at any time to adjust its options. See each [feature](../features/index.md) for information on the configuration options for each.

## 🐛 Enabling Debug Logs (Optional)

Having trouble or want to dive deeper? You can enable debug logs by adding the following to your `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.magic_areas: debug
```

Then restart Home Assistant. Debug messages will now appear in your logs.

## ✅ What’s Next?
Once Magic Areas is installed and running, check out the [Getting Started](getting-started.md) guide to learn how to make your first area magical and our [Implementation Ideas](implementation-ideas.md) to learn how to make every other area in your home just as magical!
