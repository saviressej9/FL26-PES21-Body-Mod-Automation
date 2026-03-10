# FL26 Mod Automation

A Windows desktop app for automatically assigning FC 26 body-model mods to players — grip socks, regular socks, pants, gloves, and handtape — with full control over percentages, random seeding, and manual player selection.

---

## Features

- **Percentage-based assignment** — assign any mod to X% of your player database, randomly but reproducibly via a seed
- **Manual player selection** — search by name or ID and pin specific players to specific mods
- **Per-section Dry Run / Apply** — test each mod category individually before committing
- **Global Dry Run All / Run All** — process every enabled mod in one click
- **Grip Sox brands** — balanced or random distribution across Adidas, Nike, TruSox, and more
- **Gloves brands** — same balanced/random system, with Real Madrid and Bayern Munich excluded by default
- **Handtape** — skin-color-aware assignment from your PESEditor appearance CSV
- **Duplicate validation** — automatically checks for conflicts across mod groups after each run
- **Settings persistence** — config saved to JSON; DB and appearance files backed up automatically

---

## Requirements

- Windows 10 or later
- FC 26 with [Sider](https://github.com/juce/sider) + the **PRDX Body Model Add-On V2.5** mod pack installed
- A player database file (`.txt` format: `ID - Name` per line, exported from your FL26 DB tool)
- A PESEditor appearance CSV (required for Handtape only)

---

## Installation

1. Download `FL26_ModAutomation_Setup.exe` from the [Releases](../../releases) page
2. Run the installer and follow the wizard — no Python required
3. Launch **FL26 Mod Automation** from your Start Menu or Desktop shortcut

---

## Quick Start

1. **Set Mod Root Folder** — point the app to your `PRDX_Body Model-Add On V2.5` folder
2. **Load Player DB** — select your exported player `.txt` or `.csv` file
3. **Configure each mod** — choose Percentage or Manual mode, set your values
4. **Dry Run All** — review what *would* be assigned in the log
5. **Run All** — confirm and apply

---

## Mod Categories

| Category | Mods | Notes |
|---|---|---|
| Grip Socks | Dual Color, Long, Short, Brands | Players are only assigned to one grip sox type |
| Socks | Holes, Middle High, Short Group | Players are only assigned to one sock type |
| Pants | Baggy, Extra Baggy, Shorter | Players are only assigned to one pants type |
| Gloves | Brands | Balanced or random across available brands |
| Handtape | Left / Right hand | Requires PESEditor appearance CSV for skin color |

---

## Configuration

Settings are saved to `FL26_ModAutomation.config.json` in the install folder. You can edit this directly if needed, but the UI handles everything.

Key fields:

```json
{
  "seed": 26,
  "modRootPath": "C:/FL26/SiderAddons/...",
  "mods": {
    "gripSoxBrands": {
      "enabled": true,
      "percent": 40,
      "mode": "Balanced",
      "brands": ["Adidas", "Nike", "TruSox", "..."]
    }
  }
}
```

Changing `seed` will produce a different random distribution while remaining fully reproducible.

---

## Building from Source

If you want to run or modify the source directly:

```bash
# Install dependencies
pip install customtkinter pillow

# Run the app
python FL26_ModAutomation.py
```

To build the standalone exe yourself:

```bash
pip install pyinstaller
pyinstaller FL26_ModAutomation.spec
```

Then compile `FL26_ModAutomation_Setup.iss` with [Inno Setup 6](https://jrsoftware.org/isinfo.php) to produce the installer.

---

## File Structure

```
FL26_ModAutomation/
├── FL26_ModAutomation.py          # Main UI (customtkinter)
├── FL26_ModAutomation.config.json # Saved settings
├── PlayerIds.csv                  # Generated from your DB file
├── Run-FL26-ModAutomation.ps1     # Master PowerShell runner
├── Assign-GripSox-Single.ps1
├── Assign-GripSox-Brands.ps1
├── Assign-Socks.ps1
├── Assign-Pants.ps1
├── Assign-Gloves.ps1
├── Assign-Handtape.ps1
├── Validate-Assignments.ps1
└── DB and Appearances/            # Auto-created backup folder
```

---

## Notes & Warnings

- **Handtape** will overwrite arm texture data for a player. Do **not** use it on players with in-game arm tattoos.
- All assignment scripts skip players that already have a folder on disk (no overwrite by default), so re-running is safe.
- The app is Windows-only — PowerShell is required for the backend scripts.

---

## License

MIT — free to use, modify, and distribute.
