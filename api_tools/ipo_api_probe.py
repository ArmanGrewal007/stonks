#!/usr/bin/env python3
"""Probe IPO data APIs/endpoints and report what is currently usable.

This script does NOT update your tracker files. It only checks endpoint health,
response shape, and whether required IPO fields are present for automation.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)


@dataclass
class Endpoint:
    name: str
    url: str
    expected: str  # json-list | json-object | html
    required_fields: list[str]


ENDPOINTS: list[Endpoint] = [
    Endpoint(
        name="NSE all-upcoming-issues",
        url="https://www.nseindia.com/api/all-upcoming-issues?category=ipo",
        expected="json-list",
        required_fields=["companyName", "issueStartDate", "issueEndDate", "issuePrice", "status"],
    ),
    Endpoint(
        name="NSE ipo-current-issue",
        url="https://www.nseindia.com/api/ipo-current-issue",
        expected="json-list",
        required_fields=["companyName", "issueStartDate", "issueEndDate", "issuePrice", "status"],
    ),
    Endpoint(
        name="Moneycontrol IPO page",
        url="https://www.moneycontrol.com/ipo/",
        expected="html",
        required_fields=["__NEXT_DATA__"],
    ),
]


def fetch(url: str, accept: str = "*/*") -> tuple[int, str, str]:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://www.nseindia.com/",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:  # nosec B310
            code = resp.getcode() or 0
            body = resp.read().decode("utf-8", errors="ignore")
            return code, body, ""
    except HTTPError as e:
        return e.code, "", f"HTTPError: {e}"
    except URLError as e:
        return 0, "", f"URLError: {e}"
    except TimeoutError as e:
        return 0, "", f"Timeout: {e}"


def check_endpoint(ep: Endpoint) -> dict[str, Any]:
    accept = "application/json,text/plain,*/*" if ep.expected.startswith("json") else "text/html,*/*"
    started = time.time()
    code, body, err = fetch(ep.url, accept=accept)
    elapsed_ms = int((time.time() - started) * 1000)

    result: dict[str, Any] = {
        "name": ep.name,
        "url": ep.url,
        "http_code": code,
        "ok": False,
        "latency_ms": elapsed_ms,
        "error": err,
        "records": None,
        "missing_fields": [],
        "notes": "",
    }

    if code != 200 or not body:
        result["notes"] = "Endpoint not reachable from current network/runtime."
        return result

    if ep.expected == "html":
        # Moneycontrol can return Access Denied HTML without data payload.
        if "Access Denied" in body or "You don't have permission" in body:
            result["notes"] = "Blocked by anti-bot layer (Access Denied)."
            return result
        missing = [f for f in ep.required_fields if f not in body]
        result["missing_fields"] = missing
        result["ok"] = len(missing) == 0
        if result["ok"]:
            result["notes"] = "HTML contains required marker(s)."
        else:
            result["notes"] = "HTML loaded but required marker(s) missing."
        return result

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        result["notes"] = f"Invalid JSON: {e}"
        return result

    if ep.expected == "json-list" and not isinstance(payload, list):
        result["notes"] = "JSON type mismatch: expected list."
        return result
    if ep.expected == "json-object" and not isinstance(payload, dict):
        result["notes"] = "JSON type mismatch: expected object."
        return result

    first = payload[0] if isinstance(payload, list) and payload else {}
    missing = [f for f in ep.required_fields if f not in first]
    result["missing_fields"] = missing
    result["records"] = len(payload) if isinstance(payload, list) else 1
    result["ok"] = len(missing) == 0
    result["notes"] = "Ready for automation." if result["ok"] else "Reachable but missing required field(s)."
    return result


def recommend(results: list[dict[str, Any]]) -> str:
    good = [r for r in results if r.get("ok")]
    if not good:
        return "No endpoint is currently fully usable."
    nse = [r for r in good if r["name"].startswith("NSE")]
    if nse:
        return "Recommended source: NSE API (stable JSON and required fields present)."
    return f"Recommended source: {good[0]['name']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe IPO APIs and report availability")
    parser.add_argument(
        "--out",
        default="data/ipo_api_probe_report.json",
        help="Write detailed probe report to this JSON file",
    )
    args = parser.parse_args()

    results = [check_endpoint(ep) for ep in ENDPOINTS]
    summary = {
        "checked_at_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "results": results,
        "recommendation": recommend(results),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=True, indent=2)

    print("IPO API Probe Summary")
    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        print(f"- {status} | {r['name']} | code={r['http_code']} | latency={r['latency_ms']}ms")
        if r["notes"]:
            print(f"  note: {r['notes']}")
        if r["missing_fields"]:
            print(f"  missing_fields: {', '.join(r['missing_fields'])}")
    print(summary["recommendation"])
    print(f"Saved report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
