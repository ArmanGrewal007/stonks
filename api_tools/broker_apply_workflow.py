#!/usr/bin/env python3
"""Prepare (and optionally simulate) IPO broker application intents.

This module is intentionally separate from the tracker and feed collectors.
It consumes normalized NSE feed output and a lot-size mapping file.

Default behavior is DRY RUN: no real broker actions are performed.
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATE_FMT = "%d-%b-%Y"
LIVE_CONFIRMATION_TEXT = "I_UNDERSTAND_LIVE_TRADING"


@dataclass
class BrokerOrderIntent:
    company_name: str
    symbol: str
    status: str
    open_date: str
    close_date: str
    apply_price: int
    lot_size: int
    lots: int
    quantity: int
    invested_amount: int
    upi_id: str


class MockBrokerClient:
    """Simulation-only client.

    Replace this with your broker-specific implementation once API access is enabled.
    """

    def place_ipo_application(self, intent: BrokerOrderIntent) -> dict[str, Any]:
        return {
            "ok": True,
            "broker": "mock",
            "broker_order_id": f"SIM-{uuid.uuid4().hex[:10].upper()}",
            "symbol": intent.symbol,
            "quantity": intent.quantity,
            "price": intent.apply_price,
            "invested_amount": intent.invested_amount,
            "submitted_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }


class UpstoxIpoClient:
    """Minimal Upstox live adapter scaffold.

    Endpoint payloads can vary by account/app setup. This client accepts a
    per-symbol payload template map and auto-fills common fields.
    """

    def __init__(self, access_token: str, endpoint_url: str):
        self.access_token = access_token
        self.endpoint_url = endpoint_url

    def place_ipo_application(
        self,
        intent: BrokerOrderIntent,
        payload_map: dict[str, Any],
    ) -> dict[str, Any]:
        sym = intent.symbol.strip().upper()
        template = payload_map.get(sym)
        if not isinstance(template, dict):
            return {
                "ok": False,
                "broker": "upstox",
                "symbol": intent.symbol,
                "error": "missing payload template for symbol",
            }

        payload = dict(template)
        payload.setdefault("symbol", intent.symbol)
        payload.setdefault("quantity", intent.quantity)
        payload.setdefault("price", intent.apply_price)
        payload.setdefault("upi_id", intent.upi_id)

        req = Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            },
            method="POST",
        )

        try:
            with urlopen(req, timeout=30) as resp:  # nosec B310
                body = resp.read().decode("utf-8", errors="ignore")
                parsed: Any
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = body
                return {
                    "ok": 200 <= (resp.getcode() or 0) < 300,
                    "broker": "upstox",
                    "http_code": resp.getcode(),
                    "symbol": intent.symbol,
                    "request_payload": payload,
                    "response": parsed,
                    "submitted_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                }
        except HTTPError as e:
            msg = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
            return {
                "ok": False,
                "broker": "upstox",
                "http_code": e.code,
                "symbol": intent.symbol,
                "request_payload": payload,
                "error": msg or str(e),
            }
        except URLError as e:
            return {
                "ok": False,
                "broker": "upstox",
                "symbol": intent.symbol,
                "request_payload": payload,
                "error": str(e),
            }


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)


def parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.strptime(text, DATE_FMT)
    except ValueError:
        return None


def is_within_window(row: dict[str, Any], today: datetime) -> bool:
    open_dt = parse_date(str(row.get("open_date") or ""))
    close_dt = parse_date(str(row.get("close_date") or ""))
    if not open_dt or not close_dt:
        return False
    return open_dt.date() <= today.date() <= close_dt.date()


def key_candidates(row: dict[str, Any]) -> list[str]:
    symbol = str(row.get("symbol") or "").strip().upper()
    company = str(row.get("company_name") or "").strip().upper()
    return [k for k in [symbol, company] if k]


def resolve_lot_size(row: dict[str, Any], lot_map: dict[str, Any]) -> int | None:
    for k in key_candidates(row):
        v = lot_map.get(k)
        if isinstance(v, int) and v > 0:
            return v
        if isinstance(v, str) and v.isdigit() and int(v) > 0:
            return int(v)
    return None


def build_intents(
    feed_rows: list[dict[str, Any]],
    lot_map: dict[str, Any],
    lots_per_ipo: int,
    upi_id: str,
    require_status_open: bool,
    require_window_open: bool,
    max_invested: int | None,
) -> tuple[list[BrokerOrderIntent], list[dict[str, Any]]]:
    today = datetime.now()
    intents: list[BrokerOrderIntent] = []
    skipped: list[dict[str, Any]] = []

    for row in feed_rows:
        status = str(row.get("status") or "").strip()
        if require_status_open and status.lower() != "open":
            skipped.append(
                {
                    "symbol": row.get("symbol"),
                    "company_name": row.get("company_name"),
                    "reason": f"status={status} (requires Open)",
                }
            )
            continue

        if require_window_open and not is_within_window(row, today):
            skipped.append(
                {
                    "symbol": row.get("symbol"),
                    "company_name": row.get("company_name"),
                    "reason": "outside apply window",
                }
            )
            continue

        lot_size = resolve_lot_size(row, lot_map)
        if lot_size is None:
            skipped.append(
                {
                    "symbol": row.get("symbol"),
                    "company_name": row.get("company_name"),
                    "reason": "lot_size missing in lot-size map",
                }
            )
            continue

        apply_price = row.get("apply_price")
        if not isinstance(apply_price, int) or apply_price <= 0:
            skipped.append(
                {
                    "symbol": row.get("symbol"),
                    "company_name": row.get("company_name"),
                    "reason": "invalid apply_price",
                }
            )
            continue

        quantity = lot_size * lots_per_ipo
        invested_amount = quantity * apply_price
        if max_invested is not None and invested_amount > max_invested:
            skipped.append(
                {
                    "symbol": row.get("symbol"),
                    "company_name": row.get("company_name"),
                    "reason": f"invested_amount {invested_amount} > max_invested {max_invested}",
                }
            )
            continue

        intent = BrokerOrderIntent(
            company_name=str(row.get("company_name") or ""),
            symbol=str(row.get("symbol") or ""),
            status=status,
            open_date=str(row.get("open_date") or ""),
            close_date=str(row.get("close_date") or ""),
            apply_price=apply_price,
            lot_size=lot_size,
            lots=lots_per_ipo,
            quantity=quantity,
            invested_amount=invested_amount,
            upi_id=upi_id,
        )
        intents.append(intent)

    return intents, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/simulate IPO broker apply intents")
    parser.add_argument("--feed", default="data/nse_ipo_feed.json", help="Input normalized feed JSON")
    parser.add_argument(
        "--lot-map",
        default="data/ipo_lot_sizes.json",
        help="JSON map of SYMBOL/company_name to lot size",
    )
    parser.add_argument("--out", default="data/ipo_apply_intents.json", help="Output intents JSON")
    parser.add_argument("--result", default="data/ipo_apply_result.json", help="Output run result JSON")
    parser.add_argument("--upi-id", default="demo@upi", help="UPI ID for IPO applications")
    parser.add_argument(
        "--broker",
        choices=["mock", "upstox"],
        default="mock",
        help="Broker mode: mock for simulation, upstox for live adapter",
    )
    parser.add_argument(
        "--upstox-endpoint",
        default="",
        help="Full Upstox IPO application endpoint URL for your app",
    )
    parser.add_argument(
        "--upstox-payload-map",
        default="data/upstox_symbol_payloads.json",
        help="Symbol to payload-template map for Upstox live submissions",
    )
    parser.add_argument(
        "--confirm-live",
        default="",
        help=f"Must equal {LIVE_CONFIRMATION_TEXT} to allow live submission",
    )
    parser.add_argument("--lots-per-ipo", type=int, default=1, help="How many lots per IPO")
    parser.add_argument(
        "--max-invested",
        type=int,
        default=None,
        help="Skip IPOs where total invested amount exceeds this value",
    )
    parser.add_argument(
        "--allow-non-open-status",
        action="store_true",
        help="Allow statuses other than Open",
    )
    parser.add_argument(
        "--skip-window-check",
        action="store_true",
        help="Do not enforce open_date <= today <= close_date",
    )
    parser.add_argument(
        "--execute-mock",
        action="store_true",
        help="Simulate placement using mock broker client",
    )
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Submit live requests to selected broker adapter",
    )
    args = parser.parse_args()

    feed_path = Path(args.feed)
    lot_path = Path(args.lot_map)
    if not feed_path.exists():
        raise FileNotFoundError(f"Feed file not found: {feed_path}")

    feed = read_json(feed_path)
    if not isinstance(feed, list):
        raise RuntimeError("Feed file must contain a list")

    lot_map: dict[str, Any] = {}
    if lot_path.exists():
        loaded = read_json(lot_path)
        if isinstance(loaded, dict):
            lot_map = {str(k).strip().upper(): v for k, v in loaded.items()}

    intents, skipped = build_intents(
        feed_rows=feed,
        lot_map=lot_map,
        lots_per_ipo=max(args.lots_per_ipo, 1),
        upi_id=args.upi_id,
        require_status_open=not args.allow_non_open_status,
        require_window_open=not args.skip_window_check,
        max_invested=args.max_invested,
    )

    intents_payload = [intent.__dict__ for intent in intents]
    write_json(Path(args.out), intents_payload)

    mode = "dry-run"
    if args.execute_live:
        mode = f"execute-live:{args.broker}"
    elif args.execute_mock:
        mode = "execute-mock"

    result: dict[str, Any] = {
        "mode": mode,
        "checked_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "feed_count": len(feed),
        "intent_count": len(intents_payload),
        "skipped": skipped,
        "submitted": [],
        "notes": [
            "Dry-run mode is default and safe.",
            "Live mode requires explicit confirmation and broker credentials.",
        ],
    }

    if args.execute_mock and intents:
        client = MockBrokerClient()
        for intent in intents:
            result["submitted"].append(client.place_ipo_application(intent))

    if args.execute_live and intents:
        if args.confirm_live != LIVE_CONFIRMATION_TEXT:
            raise RuntimeError(
                f"Live submission blocked. Pass --confirm-live {LIVE_CONFIRMATION_TEXT} to proceed."
            )

        if args.broker == "mock":
            raise RuntimeError("Live submission requires a real broker adapter. Use --broker upstox.")

        if args.broker == "upstox":
            token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
            if not token:
                raise RuntimeError("Missing UPSTOX_ACCESS_TOKEN environment variable for live submission.")
            if not args.upstox_endpoint.strip():
                raise RuntimeError("Missing --upstox-endpoint for live submission.")

            payload_map_path = Path(args.upstox_payload_map)
            payload_map: dict[str, Any] = {}
            if payload_map_path.exists():
                loaded = read_json(payload_map_path)
                if isinstance(loaded, dict):
                    payload_map = {str(k).strip().upper(): v for k, v in loaded.items()}

            client = UpstoxIpoClient(access_token=token, endpoint_url=args.upstox_endpoint.strip())
            for intent in intents:
                result["submitted"].append(client.place_ipo_application(intent, payload_map=payload_map))

    write_json(Path(args.result), result)

    print(f"Feed rows: {len(feed)}")
    print(f"Eligible intents: {len(intents_payload)}")
    print(f"Skipped rows: {len(skipped)}")
    print(f"Saved intents: {args.out}")
    print(f"Saved result: {args.result}")
    if skipped:
        print("Top skip reasons:")
        for row in skipped[:5]:
            print(f"- {row.get('symbol') or row.get('company_name')}: {row.get('reason')}")
    if args.execute_live:
        ok_count = sum(1 for x in result["submitted"] if bool(x.get("ok")))
        fail_count = len(result["submitted"]) - ok_count
        print(f"Live submission results: ok={ok_count}, fail={fail_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
