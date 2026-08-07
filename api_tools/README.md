# IPO API Automation (Separate Tools)

This folder is independent of your main tracker logic.

## What works right now

From this environment, the NSE IPO API is reachable and returns structured JSON:
- `https://www.nseindia.com/api/all-upcoming-issues?category=ipo`
- `https://www.nseindia.com/api/ipo-current-issue`

Moneycontrol can intermittently return anti-bot `Access Denied`, so treat it as non-primary for automation.

## Files

- `api_tools/ipo_api_probe.py`: checks multiple IPO endpoints and tells you which are usable now.
- `api_tools/ipo_nse_client.py`: fetches NSE IPO API and saves normalized JSON for automation.

## Steps

1. Probe endpoints:

```bash
UV_CACHE_DIR=.uv-cache uv run api_tools/ipo_api_probe.py
```

2. Build normalized NSE feed:

```bash
UV_CACHE_DIR=.uv-cache uv run api_tools/ipo_nse_client.py
```

3. Use `data/nse_ipo_feed.json` in your automation pipeline.

## Next automation path

1. Run probe first.
2. If NSE endpoints are `OK`, run NSE client and use that feed.
3. Validate required fields for your strategy (company, open/close, price band high).
4. Plug feed into your scheduler/workflow.

## Notes

- This is data automation only, not broker order placement.
- For auto-IPO apply, your broker must support IPO application APIs and UPI mandate flow.
