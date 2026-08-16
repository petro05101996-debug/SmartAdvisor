#!/usr/bin/env python3
"""Fetch official daily MOEX evidence for Digital Broker v8.

Purpose:
* validate month-end signals using next-month first-session OPEN prices;
* reconstruct daily close-to-close drawdowns for the frozen 2019-2026 holdout;
* obtain current index constituents for a deterministic stock-basket implementation.

Only public MOEX ISS endpoints are used. Every request and SHA-256 is recorded.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE = "https://iss.moex.com/iss"
DATE_FROM = os.environ.get("MOEX_DAILY_FROM", "2018-01-01")
DATE_TO = os.environ.get("MOEX_DAILY_TILL", "2026-08-16")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "daily_output"
RAW = OUT / "raw"

INDEX_IDS = [
    "MCFTRR", "MEOGTRR", "MEMMTRR", "MEFNTRR", "MEEUTRR", "METLTRR",
    "MECNTRR", "MECHTRR", "METNTRR", "MEITTRR", "MESMTR", "MRBCTR",
    "RUGBITR1Y", "RUGBITR5+", "RUSFARIND",
]
TRADED_IDS = [
    ("currency", "selt", "GLDRUB_TOM"),
]
CONSTITUENT_INDEX_IDS = [
    "MOEXOG", "MOEXMM", "MOEXFN", "MOEXEU", "MOEXTL", "MOEXCN",
    "MOEXCH", "MOEXTN", "MOEXIT", "MOEXBMI", "MRBC",
]


def get(url: str, retries: int = 6, timeout: int = 90) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "digital-broker-v8-audit/1.0",
            })
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


def fetch_candles(engine: str, market: str, secid: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    start = 0
    seen: set[tuple[str, str]] = set()
    while True:
        params = {
            "from": DATE_FROM,
            "till": DATE_TO,
            "interval": 24,
            "start": start,
            "iss.meta": "off",
        }
        path = (
            f"engines/{quote(engine, safe='')}/markets/{quote(market, safe='')}"
            f"/securities/{quote(secid, safe='')}/candles.json"
        )
        url = f"{BASE}/{path}?{urlencode(sorted(params.items()))}"
        raw = get(url)
        payload = json.loads(raw)
        page = table(payload, "candles")
        requests.append({
            "url": url,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "rows": len(page),
        })
        if not page:
            break
        added = 0
        for row in page:
            key = (str(row.get("begin") or ""), str(row.get("end") or ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "secid": secid,
                "engine": engine,
                "market": market,
                "begin": row.get("begin"),
                "end": row.get("end"),
                "open": row.get("open"),
                "close": row.get("close"),
                "high": row.get("high"),
                "low": row.get("low"),
                "value": row.get("value"),
                "volume": row.get("volume"),
            })
            added += 1
        if added == 0 or len(page) < 500:
            break
        start += len(page)
        if start > 20000:
            raise RuntimeError(f"pagination runaway for {secid}")
    rows.sort(key=lambda x: str(x["begin"]))
    return rows, requests


def fetch_constituents(index_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {"limit": 500, "iss.meta": "off"}
    path = f"statistics/engines/stock/markets/index/analytics/{quote(index_id, safe='')}.json"
    url = f"{BASE}/{path}?{urlencode(sorted(params.items()))}"
    raw = get(url)
    payload = json.loads(raw)
    rows: list[dict[str, Any]] = []
    for name, obj in payload.items():
        if not isinstance(obj, dict) or not isinstance(obj.get("columns"), list):
            continue
        for row in table(payload, name):
            normalized = {str(k).lower(): v for k, v in row.items()}
            normalized["source_table"] = name
            normalized["index_id"] = index_id
            rows.append(normalized)
    return rows, {"url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows)}


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
    RAW.mkdir(parents=True, exist_ok=True)
    daily: list[dict[str, Any]] = []
    request_log: dict[str, Any] = {"candles": {}, "constituents": {}}

    assets = [("stock", "index", secid) for secid in INDEX_IDS] + TRADED_IDS
    for pos, (engine, market, secid) in enumerate(assets, 1):
        rows, requests = fetch_candles(engine, market, secid)
        daily.extend(rows)
        request_log["candles"][secid] = {
            "rows": len(rows),
            "start": rows[0]["begin"] if rows else None,
            "end": rows[-1]["end"] if rows else None,
            "requests": requests,
        }
        print(f"daily [{pos:02d}/{len(assets):02d}] {secid}: {len(rows)}", flush=True)

    constituents: list[dict[str, Any]] = []
    for pos, index_id in enumerate(CONSTITUENT_INDEX_IDS, 1):
        rows, meta = fetch_constituents(index_id)
        constituents.extend(rows)
        request_log["constituents"][index_id] = meta
        print(f"constituents [{pos:02d}/{len(CONSTITUENT_INDEX_IDS):02d}] {index_id}: {len(rows)}", flush=True)

    daily.sort(key=lambda x: (str(x["begin"]), str(x["secid"])))
    constituents.sort(key=lambda x: (str(x.get("index_id")), str(x.get("secid") or x.get("ticker") or "")))
    daily_path = OUT / "daily_candles.csv"
    constituents_path = OUT / "current_index_constituents.csv"
    write_csv(daily_path, daily)
    write_csv(constituents_path, constituents)

    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "daily_rows": len(daily),
        "constituent_rows": len(constituents),
        "daily_sha256": hashlib.sha256(daily_path.read_bytes()).hexdigest(),
        "constituents_sha256": hashlib.sha256(constituents_path.read_bytes()).hexdigest(),
        "requests": request_log,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: manifest[k] for k in ["daily_rows", "constituent_rows", "daily_sha256", "constituents_sha256"]}, indent=2))
    return 0 if daily else 2


if __name__ == "__main__":
    raise SystemExit(main())
