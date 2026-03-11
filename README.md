# FL26 Mod Automation

A desktop tool for automating body model mod assignments in FC 26 (FIFA 26) using the [PRDX Body Model Add-On V2.5](https://www.pesmaster.com) via Sider.

---

## Requirements

- Windows 10 or 11
- [Sider](https://github.com/juce/sider) with PRDX Body Model Add-On V2.5 installed
- A PES/FC player database export (`.txt` format: `ID - Name`) or CSV

---

## Installation

No installation required.

1. Download `FL26_Mod_Automation_v[version].zip` from the [Releases](../../releases) page
2. Extract the zip anywhere — your desktop, a USB drive, wherever you like
3. Open the extracted folder and double-click **`FL26 Mod Automation.exe`**

That's it. No Python, no setup wizards, nothing else to install.

---

## First-Time Setup

1. **Mod Root Folder** — click Browse and select the root folder of your PRDX Body Model Add-On. This is the folder that contains subfolders like `Grip Sock-Long`, `Pants-Baggy`, etc.
2. **Player DB File** — click Browse and select your player database file (`.txt` or `.csv`). This is used to build the list of player IDs that mods can be assigned to.

Both settings are saved automatically and will be remembered next time you open the app.

---

## How It Works

Each mod section lets you assign that mod to a percentage of players (randomly selected using a fixed seed for reproducibility) or to a manually chosen list of specific players.

Mods that are mutually exclusive (e.g. you can't have two different grip sock styles on the same player) automatically exclude players already assigned elsewhere — no manual coordination needed.

### Mod Groups

| Group | Mods | Mutual Exclusion |
|---|---|---|
| Grip Sox | Dual Color, Extra Long, Long, Short, Brands | Within group only |
| Socks | Holes, Middle High, Short Group | Within group only |
| Pants | Baggy, Extra Baggy, Shorter | Within group only |
| Shirt | Baggy | Independent |
| Gloves | Brands | Independent |
| Sleeve Roll Up | Auto-detected variations | Independent |
| Sleeve Inner | Auto-detected variations | Independent |
| Wristtaping | Auto-detected variations | Independent |
| Handtape | Manual only | Independent |

Grouped sections (Sleeve Roll Up, Sleeve Inner, Wristtaping) auto-detect available variations by scanning your Mod Root Folder — no configuration needed.

### Assignment Modes

- **Percentage** — randomly assigns the mod to that percentage of all players in your DB, using the configured seed
- **Manual** — assign to specific players only, searched by name or ID
- **Per Variation** (brand/template mods) — set a separate percentage or manual list per variation (e.g. 10% Nike, 8% Adidas, specific players on TruSox)

### Dry Run

Every section has a **Dry Run** button that shows exactly what would be copied without touching any files. Always recommended before applying.

---

## Handtape

Handtape is manual-only and requires your PESEditor Appearance CSV to look up each player's skin colour. Select the CSV, add players by name or ID, choose left/right hand, then apply.

> ⚠️ Do not use handtape for players with in-game arm tattoos — it will overwrite them.

---

## Updating

To update to a new version, download the new zip from the Releases page and extract it to replace your existing folder. Your `FL26_ModAutomation.config.json` can be copied across to keep your settings.

---

## Building from Source

Requires Python 3.12+ and PyInstaller.

```
pip install customtkinter pillow pyinstaller
pyinstaller FL26_ModAutomation.spec
```

The built exe will be at `dist\FL26 Mod Automation.exe`.

To package a release zip, copy the following into a folder named `FL26 Mod Automation`:

```
FL26 Mod Automation.exe
FL26_ModAutomation.config.json
PlayerIds.csv
Run-FL26-ModAutomation.ps1
Assign-GripSox-Single.ps1
Assign-GripSox-Brands.ps1
Assign-Socks.ps1
Assign-Pants.ps1
Assign-Shirt.ps1
Assign-Gloves.ps1
Assign-Sleeve.ps1
Assign-Wristtaping.ps1
Assign-Handtape.ps1
Validate-Assignments.ps1
```

Then zip the folder and upload as a GitHub release asset.
