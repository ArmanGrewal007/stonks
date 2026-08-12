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

## GitHub Pages Dashboard + Excel Allotment Updates

This repo now includes a web dashboard in `docs/` and deployment workflow:

- Dashboard: `docs/index.html`
- Deploy workflow: `.github/workflows/deploy-pages.yml`
- Allotment update workflow: `.github/workflows/set-ipo-allotment.yml`

### Enable GitHub Pages

1. Push changes to `main`.
2. In GitHub repository settings, open **Pages**.
3. Set source to **GitHub Actions**.
4. Run `Deploy Dashboard to GitHub Pages` (or wait for push trigger).

### How the company button works

- In the dashboard, each `company_name` is a button.
- Click it and type one of: `yes`, `no`, `clear`.
- The dashboard dispatches `set-ipo-allotment.yml`.
- That workflow updates `got_ipo` in `data/mainboard_ipos.xlsx`, regenerates `docs/mainboard_ipos_web.json`, and commits both files.

### Token required in dashboard

The dashboard needs a GitHub token to dispatch workflows.
Use a fine-grained token scoped to this repo with:

- Actions: Read and write
- Contents: Read and write

### Test workflow dispatch from terminal

If dashboard dispatch fails, test with curl directly.

1. Export token in your terminal:

```bash
export GH_PAT="your_fine_grained_token"
```

2. Dispatch allotment workflow:

```bash
curl -i -X POST \
	-H "Accept: application/vnd.github+json" \
	-H "Authorization: Bearer $GH_PAT" \
	-H "Content-Type: application/json" \
	-H "X-GitHub-Api-Version: 2022-11-28" \
	"https://api.github.com/repos/ArmanGrewal007/stonks/actions/workflows/331286347/dispatches" \
	--data-raw '{"ref":"main","inputs":{"company_name":"LEAP India Ltd","got_ipo":"yes"}}'
```

Expected success response: `HTTP/2 204`.

### Manual XLSX edits and website sync

If you manually edit `data/mainboard_ipos.xlsx`, the website will not update until JSON is regenerated.

1. Edit Excel file:

- `data/mainboard_ipos.xlsx`

2. Run export:

```bash
UV_CACHE_DIR=.uv-cache uv run src/export_web_data.py
```

3. Commit and push both files:

- `data/mainboard_ipos.xlsx`
- `docs/mainboard_ipos_web.json`

4. GitHub Pages deploy workflow will publish the updated dashboard.
