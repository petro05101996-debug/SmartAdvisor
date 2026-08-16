#!/usr/bin/env python3
"""Fetch long official total-return, FX and gold histories missing from ISS candles."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FROM = os.environ.get("MOEX_FROM", "2000-01-01")
TILL = os.environ.get("MOEX_TILL", date.today().isoformat())
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data_extended"
RAW = OUT / "raw"


def get(url: str, retries: int = 6, timeout: int = 90) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "digital-broker-v7-research/1.0", "Accept": "*/*"})
            with urlopen(req, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(12, 2**attempt))
    raise RuntimeError(f"download failed: {url}: {last}")


def table(payload: dict, key: str) -> list[dict]:
    obj = payload.get(key, {})
    cols, data = obj.get("columns", []), obj.get("data", [])
    return [dict(zip(cols, row)) for row in data if len(row) == len(cols)]


def month_last(rows: list[tuple[str, float]]) -> list[tuple[str, float]]:
    by_month: dict[str, tuple[str, float]] = {}
    for raw_date, value in rows:
        if value is None:
            continue
        key = raw_date[:7]
        if key not in by_month or raw_date > by_month[key][0]:
            by_month[key] = (raw_date, float(value))
    return [by_month[key] for key in sorted(by_month)]


def fetch_moex_history(secid: str) -> tuple[list[tuple[str, float]], list[dict]]:
    rows: list[tuple[str, float]] = []
    requests: list[dict] = []
    start = 0
    while True:
        params = {
            "from": FROM,
            "till": TILL,
            "start": start,
            "iss.meta": "off",
            "iss.only": "history,history.cursor",
            "history.columns": "TRADEDATE,CLOSE",
        }
        url = f"https://iss.moex.com/iss/history/engines/stock/markets/index/securities/{secid}.json?{urlencode(params)}"
        raw = get(url)
        payload = json.loads(raw)
        batch = table(payload, "history")
        for item in batch:
            if item.get("TRADEDATE") and item.get("CLOSE") is not None:
                rows.append((str(item["TRADEDATE"]), float(item["CLOSE"])))
        cursor = table(payload, "history.cursor")
        requests.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(batch)})
        if not batch:
            break
        if cursor:
            total = int(cursor[0].get("TOTAL", 0) or 0)
            page = int(cursor[0].get("PAGESIZE", len(batch)) or len(batch))
            if start + page >= total:
                break
            start += page
        else:
            start += len(batch)
            if len(batch) < 100:
                break
    return month_last(rows), requests


def cbr_dates() -> tuple[str, str]:
    start = datetime.strptime(FROM, "%Y-%m-%d").strftime("%d/%m/%Y")
    end = datetime.strptime(TILL, "%Y-%m-%d").strftime("%d/%m/%Y")
    return start, end


def fetch_cbr_usd() -> tuple[list[tuple[str, float]], list[dict]]:
    start, end = cbr_dates()
    url = "https://www.cbr.ru/scripts/XML_dynamic.asp?" + urlencode({
        "date_req1": start, "date_req2": end, "VAL_NM_RQ": "R01235"
    })
    raw = get(url)
    root = ET.fromstring(raw)
    rows = []
    for rec in root.findall(".//Record"):
        dt = datetime.strptime(rec.attrib["Date"], "%d.%m.%Y").date().isoformat()
        nominal = float((rec.findtext("Nominal") or "1").replace(",", "."))
        value = float((rec.findtext("Value") or "nan").replace(",", ".")) / nominal
        rows.append((dt, value))
    return month_last(rows), [{"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(rows)}]


def fetch_cbr_gold() -> tuple[list[tuple[str, float]], list[dict]]:
    start_year = datetime.strptime(FROM, "%Y-%m-%d").year
    end_year = datetime.strptime(TILL, "%Y-%m-%d").year
    all_rows: list[tuple[str, float]] = []
    requests: list[dict] = []
    for year in range(start_year, end_year + 1):
        first = max(datetime.strptime(FROM, "%Y-%m-%d").date(), date(year, 1, 1))
        last = min(datetime.strptime(TILL, "%Y-%m-%d").date(), date(year, 12, 31))
        if first > last:
            continue
        url = "https://www.cbr.ru/scripts/xml_metall.asp?" + urlencode({
            "date_req1": first.strftime("%d/%m/%Y"), "date_req2": last.strftime("%d/%m/%Y")
        })
        raw = get(url)
        root = ET.fromstring(raw)
        n = 0
        for rec in root.findall(".//Record"):
            if str(rec.attrib.get("Code")) != "1":
                continue
            values = []
            for tag in ("Buy", "Sell"):
                text = rec.findtext(tag)
                if text:
                    values.append(float(text.replace(",", ".")))
            if not values:
                continue
            dt = datetime.strptime(rec.attrib["Date"], "%d.%m.%Y").date().isoformat()
            all_rows.append((dt, sum(values) / len(values)))
            n += 1
        requests.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": n})
    return month_last(all_rows), requests


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    evidence: dict[str, list[dict]] = {}
    sources = {}
    for secid in ("MCFTR", "MCFTRR"):
        rows, reqs = fetch_moex_history(secid)
        sources[secid] = rows
        evidence[secid] = reqs
        print(secid, len(rows), rows[0][0] if rows else None, rows[-1][0] if rows else None, flush=True)
    rows, reqs = fetch_cbr_usd()
    sources["CBR_USDRUB"] = rows
    evidence["CBR_USDRUB"] = reqs
    print("CBR_USDRUB", len(rows), rows[0][0] if rows else None, rows[-1][0] if rows else None, flush=True)
    rows, reqs = fetch_cbr_gold()
    sources["CBR_GOLD_RUB_G"] = rows
    evidence["CBR_GOLD_RUB_G"] = reqs
    print("CBR_GOLD_RUB_G", len(rows), rows[0][0] if rows else None, rows[-1][0] if rows else None, flush=True)

    for secid, rows in sources.items():
        for dt, close in rows:
            all_rows.append({"date": dt, "secid": secid, "close": close})
    all_rows.sort(key=lambda x: (x["date"], x["secid"]))
    out_csv = OUT / "extended_monthly.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["date", "secid", "close"])
        writer.writeheader()
        writer.writerows(all_rows)
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "date_from": FROM,
        "date_to": TILL,
        "rows": len(all_rows),
        "series": {key: len(value) for key, value in sources.items()},
        "csv_sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest(),
        "requests": evidence,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if len(sources["MCFTRR"]) < 200 or len(sources["CBR_USDRUB"]) < 250 or len(sources["CBR_GOLD_RUB_G"]) < 250:
        raise SystemExit(f"insufficient extended history: {manifest['series']}")
    print(json.dumps(manifest["series"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
