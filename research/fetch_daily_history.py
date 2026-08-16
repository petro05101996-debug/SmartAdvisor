from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

FROM = os.environ.get("MOEX_FROM", "2000-01-01")
TILL = os.environ.get("MOEX_TILL", dt.date.today().isoformat())
OUT = Path("research/data_daily")
OUT.mkdir(parents=True, exist_ok=True)

INDEX_SERIES = [
    "IMOEX", "MCFTR", "MCFTRR",
    "MOEXOG", "MOEXMM", "MOEXFN", "MOEXEU", "MOEXTL", "MOEXCN", "MOEXCH", "MOEXTN", "MOEXIT",
    "MEOGTRR", "MEMMTRR", "MEFNTRR", "MEEUTRR", "METLTRR", "MECNTRR", "MECHTRR", "METNTRR", "MEITTRR",
    "RGBITR", "RUGBITR1Y", "RUGBITR3Y", "RUGBITR5Y", "RUGBITR10Y", "RUSFARIND", "GLDRUB_TOM",
]

HEADERS = {"User-Agent": "SmartAdvisor-v7-research/1.0"}


def get_bytes(url: str, attempts: int = 6) -> bytes:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001
            error = exc
            time.sleep(min(12, 1.5 ** attempt))
    raise RuntimeError(f"Failed URL after {attempts} attempts: {url}") from error


def fetch_candles(secid: str) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    start = 0
    while True:
        params = urllib.parse.urlencode({
            "from": FROM,
            "till": TILL,
            "interval": 24,
            "start": start,
            "iss.meta": "off",
            "candles.columns": "begin,close",
        })
        url = f"https://iss.moex.com/iss/engines/stock/markets/index/securities/{secid}/candles.json?{params}"
        payload = json.loads(get_bytes(url))
        block = payload.get("candles", {})
        data = block.get("data", [])
        columns = block.get("columns", [])
        if not data:
            break
        for item in data:
            rec = dict(zip(columns, item))
            close = rec.get("close")
            begin = rec.get("begin")
            if begin and close is not None:
                rows.append({"date": str(begin)[:10], "secid": secid, "close": float(close), "source": "MOEX_ISS_CANDLES"})
        start += len(data)
        if len(data) < 500:
            break
        time.sleep(0.05)
    return rows


def fetch_history(secid: str) -> list[dict[str, str | float]]:
    endpoints = [
        f"https://iss.moex.com/iss/history/engines/stock/markets/index/securities/{secid}.json",
        f"https://iss.moex.com/iss/history/engines/stock/markets/index/boards/RTSI/securities/{secid}.json",
    ]
    best: list[dict[str, str | float]] = []
    for endpoint in endpoints:
        rows: list[dict[str, str | float]] = []
        start = 0
        while True:
            params = urllib.parse.urlencode({
                "from": FROM,
                "till": TILL,
                "start": start,
                "iss.meta": "off",
                "history.columns": "TRADEDATE,CLOSE,CURRENTVALUE",
            })
            payload = json.loads(get_bytes(f"{endpoint}?{params}"))
            block = payload.get("history", {})
            data = block.get("data", [])
            columns = block.get("columns", [])
            if not data:
                break
            for item in data:
                rec = dict(zip(columns, item))
                close = rec.get("CLOSE")
                if close is None:
                    close = rec.get("CURRENTVALUE")
                date = rec.get("TRADEDATE")
                if date and close is not None:
                    rows.append({"date": str(date), "secid": secid, "close": float(close), "source": "MOEX_ISS_HISTORY"})
            start += len(data)
            if len(data) < 100:
                break
            time.sleep(0.05)
        if len(rows) > len(best):
            best = rows
    return best


def fetch_cbr_usd() -> list[dict[str, str | float]]:
    d1 = dt.datetime.strptime(FROM, "%Y-%m-%d").strftime("%d/%m/%Y")
    d2 = dt.datetime.strptime(TILL, "%Y-%m-%d").strftime("%d/%m/%Y")
    query = urllib.parse.urlencode({"date_req1": d1, "date_req2": d2, "VAL_NM_RQ": "R01235"})
    root = ET.fromstring(get_bytes(f"https://www.cbr.ru/scripts/XML_dynamic.asp?{query}"))
    rows = []
    for rec in root.findall("Record"):
        date = dt.datetime.strptime(rec.attrib["Date"], "%d.%m.%Y").date().isoformat()
        value = float(rec.findtext("Value", "").replace(",", "."))
        nominal = float(rec.findtext("Nominal", "1").replace(",", "."))
        rows.append({"date": date, "secid": "CBR_USDRUB", "close": value / nominal, "source": "CBR_XML"})
    return rows


def fetch_cbr_gold() -> list[dict[str, str | float]]:
    d1 = dt.datetime.strptime(FROM, "%Y-%m-%d").strftime("%d/%m/%Y")
    d2 = dt.datetime.strptime(TILL, "%Y-%m-%d").strftime("%d/%m/%Y")
    query = urllib.parse.urlencode({"date_req1": d1, "date_req2": d2})
    root = ET.fromstring(get_bytes(f"https://www.cbr.ru/scripts/xml_metall.asp?{query}"))
    rows = []
    for rec in root.findall("Record"):
        if rec.attrib.get("Code") != "1":
            continue
        date = dt.datetime.strptime(rec.attrib["Date"], "%d.%m.%Y").date().isoformat()
        value = float(rec.findtext("Buy", "").replace(",", "."))
        rows.append({"date": date, "secid": "CBR_GOLD_RUB_G", "close": value, "source": "CBR_XML"})
    return rows


def deduplicate(rows: Iterable[dict[str, str | float]]) -> list[dict[str, str | float]]:
    by_key: dict[tuple[str, str], dict[str, str | float]] = {}
    priority = {"MOEX_ISS_HISTORY": 3, "MOEX_ISS_CANDLES": 2, "CBR_XML": 3}
    for row in rows:
        key = (str(row["date"]), str(row["secid"]))
        old = by_key.get(key)
        if old is None or priority.get(str(row["source"]), 0) >= priority.get(str(old["source"]), 0):
            by_key[key] = row
    return sorted(by_key.values(), key=lambda r: (str(r["date"]), str(r["secid"])))


def main() -> None:
    all_rows: list[dict[str, str | float]] = []
    counts: dict[str, int] = {}
    for n, secid in enumerate(INDEX_SERIES, start=1):
        rows = fetch_candles(secid)
        if secid in {"MCFTR", "MCFTRR"}:
            extended = fetch_history(secid)
            rows = deduplicate([*rows, *extended])
        counts[secid] = len(rows)
        all_rows.extend(rows)
        print(f"[{n:02d}/{len(INDEX_SERIES)}] {secid}: {len(rows)}", flush=True)

    for fetcher, secid in [(fetch_cbr_usd, "CBR_USDRUB"), (fetch_cbr_gold, "CBR_GOLD_RUB_G")]:
        rows = fetcher()
        counts[secid] = len(rows)
        all_rows.extend(rows)
        print(f"{secid}: {len(rows)}", flush=True)

    all_rows = deduplicate(all_rows)
    csv_path = OUT / "official_daily_snapshot.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["date", "secid", "close", "source"])
        writer.writeheader()
        writer.writerows(all_rows)

    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest = {
        "from": FROM,
        "till": TILL,
        "rows": len(all_rows),
        "series": counts,
        "sha256": digest,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
