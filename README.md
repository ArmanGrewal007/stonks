# Mainboard IPO Tracker (Free)

This project updates a local Excel file with Mainboard IPO data using a free public source.

It fills fields like:
- Company name
- Open date
- Close date
- Allotment date
- Listing date
- Lot size
- Price band
- Invested (`higher price band * lot size`)
- Output (`listing price * lot size`, once listed)
- Issue size
- Subscription stats
- Listing gain fields (when available)

Status color coding in Excel:
- `Open`: yellow
- `Upcoming`: light blue
- `Listed`: light green
- `Closed`: gray

## Why this works even if your laptop was off

The script is **idempotent** and does a fresh pull each run. If your laptop is off during a scheduled time, it will catch up the next time it runs.

## Source

- `https://www.moneycontrol.com/ipo/` (embedded page JSON)

No paid API is required.

## Project structure

- `src/ipo_tracker.py`: fetch + parse + merge script
- `data/mainboard_ipos.xlsx`: tracker data with colors and filters
- `data/source_snapshot.json`: raw source snapshot for debugging
- `.github/workflows/update-ipo.yml`: optional free cloud automation via GitHub Actions
- `scripts/install_launchd.sh`: local automation on macOS

## Dependencies with uv

```bash
uv sync
```

## Run once

```bash
uv run src/ipo_tracker.py
```

Optional custom paths:

```bash
uv run src/ipo_tracker.py --snapshot data/source_snapshot.json --excel data/mainboard_ipos.xlsx
```

## Local automation on macOS (free)

Runs at login and every 6 hours while laptop is on:

```bash
bash scripts/install_launchd.sh
```

To stop it:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.local.ipotracker.plist"
```

## Fully automatic even when laptop is off (free)

Use GitHub Actions (already configured):

1. Create a GitHub repo and push this folder.
2. Enable Actions in the repo.
3. Workflow `.github/workflows/update-ipo.yml` will run on schedule and commit updates.

You can also trigger it manually from the Actions tab.

## Open in Excel / Google Sheets

- Open `data/mainboard_ipos.xlsx` for color-coded status and filters.

## Notes

- Data format on source site can change; if it changes, parser updates may be required.
- This script only keeps `ipo_type == Mainline` records.
- Rows are append/update only (existing rows are never removed by source disappearance).
- Sorting is by `allotment_date` ascending.
