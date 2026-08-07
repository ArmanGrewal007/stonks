#!/usr/bin/env python3
"""NSE-only IPO client for automation-friendly normalized output.

Use this when you want an API-first, no-scraping feed.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)

NSE_API = "https://www.nseindia.com/api/all-upcoming-issues?category=ipo"


def fetch_json(url: str) -> Any:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive",
        },
    )
    with urlopen(req, timeout=30) as resp:  # nosec B310
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def parse_price_band(text: str) -> tuple[int | None, int | None]:
    nums = re.findall(r"\d+(?:\.\d+)?", text or "")
    if len(nums) >= 2:
        return int(round(float(nums[0]))), int(round(float(nums[1])))
    if len(nums) == 1:
        v = int(round(float(nums[0])))
        return v, v
    return None, None


def normalize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in records:
        if str(r.get("series") or "").strip().upper() != "EQ":
            continue
        low, high = parse_price_band(str(r.get("issuePrice") or ""))
        status = str(r.get("status") or "").strip().lower()
        out.append(
            {
                "company_name": r.get("companyName"),
                "open_date": r.get("issueStartDate"),
                "close_date": r.get("issueEndDate"),
                "price_band_low": low,
                "price_band_high": high,
                "apply_price": high,
                "status": "Open" if status == "active" else "Upcoming",
                "symbol": r.get("symbol"),
                "source": "NSE_API",
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch IPO records from NSE API")
    parser.add_argument("--out", default="data/nse_ipo_feed.json", help="Output JSON file path")
    args = parser.parse_args()

    payload = fetch_json(NSE_API)
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected NSE payload type; expected list")

    normalized = normalize(payload)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=True, indent=2)

    print(f"Fetched records: {len(payload)}")
    print(f"Normalized records: {len(normalized)}")
    print(f"Saved feed: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
