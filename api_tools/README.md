# IPO API Automation (Separate Tools)

This folder is independent of your main tracker logic.

## What works right now

From this environment, the NSE IPO API is reachable and returns structured JSON:
- `https://www.nseindia.com/api/all-upcoming-issues?category=ipo`
- `https://www.nseindia.com/api/ipo-current-issue`

Moneycontrol can intermittently return anti-bot `Access Denied`, so treat it as non-primary for automation.

## Broker choice

- You are currently on Groww, but public developer APIs for automated order workflows are not clearly exposed for this use-case.
- Recommended path: Upstox developer API stack for automation, because it has public API docs, sandbox workflow, and an IPO section in trading docs.
- Pricing can change frequently, so validate current brokerage/account charges on the broker pricing page before going live.

## Files

- `api_tools/ipo_api_probe.py`: checks multiple IPO endpoints and tells you which are usable now.
- `api_tools/ipo_nse_client.py`: fetches NSE IPO API and saves normalized JSON for automation.
- `api_tools/broker_apply_workflow.py`: builds IPO application intents and simulates broker submissions.
- `api_tools/ipo_lot_sizes.example.json`: example symbol-to-lot-size mapping.
- `data/upstox_symbol_payloads.example.json`: example symbol-to-payload template map for Upstox live submissions.

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

4. Add lot sizes (required for quantity and invested amount):

```bash
cp api_tools/ipo_lot_sizes.example.json data/ipo_lot_sizes.json
```

5. Build dry-run broker application intents:

```bash
UV_CACHE_DIR=.uv-cache uv run api_tools/broker_apply_workflow.py
```

6. Optional: simulate submission responses (mock broker):

```bash
UV_CACHE_DIR=.uv-cache uv run api_tools/broker_apply_workflow.py --execute-mock
```

7. Prepare Upstox payload map for live mode:

```bash
cp data/upstox_symbol_payloads.example.json data/upstox_symbol_payloads.json
```

8. Live mode (guarded):

```bash
UPSTOX_ACCESS_TOKEN="<token>" UV_CACHE_DIR=.uv-cache uv run api_tools/broker_apply_workflow.py \
	--broker upstox \
	--execute-live \
	--upstox-endpoint "<upstox-ipo-endpoint-from-your-app-docs>" \
	--confirm-live I_UNDERSTAND_LIVE_TRADING
```

## Next automation path

1. Run probe first.
2. If NSE endpoints are `OK`, run NSE client and use that feed.
3. Validate required fields for your strategy (company, open/close, price band high).
4. Plug feed into your scheduler/workflow.
5. Generate broker intents from feed + lot size map.
6. Replace mock broker client with your broker API SDK when ready.

## Notes

- This is data automation only, not broker order placement.
- Live mode now supports an Upstox adapter scaffold, but you must fill symbol payload templates and endpoint details from your Upstox app docs.
- For auto-IPO apply, your broker must support IPO application APIs and UPI mandate flow.
- Output files from broker workflow:
	- `data/ipo_apply_intents.json`
	- `data/ipo_apply_result.json`
