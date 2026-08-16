#!/usr/bin/env python3
"""Fetch current MOEX tradable instruments needed by Digital Broker v8.

The output is intentionally mechanical: current OFZ market snapshot from TQOB
and known exchange-traded fund snapshots. The robot then maps model sleeves to
real instruments without broker credentials or order submission.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://iss.moex.com/iss"
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "current_output"
KNOWN_FUNDS = ["LQDT", "SBMX", "TMOS", "BCSR", "GOLD", "TGLD", "SBGB"]


def get(url: str, retries: int = 6, timeout: int = 90) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"Accept": "application/json", "User-Agent": "digital-broker-v8-current/1.0"})
            with urlopen(req, timeout=timeout) as response:
                raw = response.read()
                if "json" not in (response.headers.get("Content-Type") or "").lower():
                    raise RuntimeError("non-JSON response")
                return raw
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(16, 2 ** attempt))
    raise RuntimeError(f"request failed: {url}: {last}")


def table(payload: dict[str, Any], name: str) -> list[dict[str, Any]]:
    obj = payload.get(name)
    if not isinstance(obj, dict):
        return []
    cols, data = obj.get("columns"), obj.get("data")
    if not isinstance(cols, list) or not isinstance(data, list):
        return []
    return [dict(zip(cols, row)) for row in data if len(row) == len(cols)]


def fetch_ofz() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    start = 0
    while True:
        params = {
            "start": start,
            "iss.meta": "off",
            "iss.only": "securities,marketdata",
            "securities.columns": "SECID,BOARDID,SHORTNAME,SECNAME,LOTSIZE,FACEVALUE,FACEUNIT,MATDATE,COUPONPERCENT,COUPONVALUE,NEXTCOUPON,ACCRUEDINT,LISTLEVEL,ISSUESIZE,REGNUMBER",
            "marketdata.columns": "SECID,BOARDID,BID,OFFER,LAST,MARKETPRICE,CLOSEPRICE,YIELD,YIELDATWAP,VALTODAY,NUMTRADES,DURATION,DURATIONWAPRICE",
        }
        url = f"{BASE}/engines/stock/markets/bonds/boards/TQOB/securities.json?{urlencode(sorted(params.items()))}"
        raw = get(url)
        payload = json.loads(raw)
        securities = table(payload, "securities")
        market = {str(r.get("SECID")): r for r in table(payload, "marketdata")}
        for sec in securities:
            secid = str(sec.get("SECID") or "")
            row = {str(k).lower(): v for k, v in sec.items()}
            row.update({str(k).lower(): v for k, v in market.get(secid, {}).items() if str(k).lower() not in row or row[str(k).lower()] is None})
            rows.append(row)
        requests.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(securities)})
        if len(securities) < 100:
            break
        start += len(securities)
        if start > 5000:
            raise RuntimeError("OFZ pagination runaway")
    return rows, requests


def fetch_fund(secid: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {
        "iss.meta": "off",
        "iss.only": "boards,securities,marketdata",
    }
    url = f"{BASE}/securities/{secid}.json?{urlencode(sorted(params.items()))}"
    raw = get(url)
    payload = json.loads(raw)
    rows = []
    for name in ["boards", "securities", "marketdata"]:
        for item in table(payload, name):
            row = {str(k).lower(): v for k, v in item.items()}
            row["source_table"] = name
            row["requested_secid"] = secid
            rows.append(row)
    return rows, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(rows)}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ofz, ofz_requests = fetch_ofz()
    fund_rows: list[dict[str, Any]] = []
    fund_requests: dict[str, Any] = {}
    for secid in KNOWN_FUNDS:
        rows, meta = fetch_fund(secid)
        fund_rows.extend(rows)
        fund_requests[secid] = meta
        print(f"fund {secid}: {len(rows)}", flush=True)
    write_csv(OUT / "current_ofz.csv", ofz)
    write_csv(OUT / "known_funds.csv", fund_rows)
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ofz_rows": len(ofz),
        "fund_rows": len(fund_rows),
        "ofz_sha256": hashlib.sha256((OUT / "current_ofz.csv").read_bytes()).hexdigest(),
        "funds_sha256": hashlib.sha256((OUT / "known_funds.csv").read_bytes()).hexdigest(),
        "requests": {"ofz": ofz_requests, "funds": fund_requests},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["ofz_rows", "fund_rows", "ofz_sha256", "funds_sha256"]}, indent=2))
    return 0 if ofz else 2


if __name__ == "__main__":
    raise SystemExit(main())
