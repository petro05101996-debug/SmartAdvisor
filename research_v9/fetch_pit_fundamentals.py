#!/usr/bin/env python3
"""Fetch point-in-time MOEX index constituents, issuer INNs and RFSD fundamentals.

This is an evidence builder for Digital Broker v9. It never fabricates missing
history: every row records the requested constituent date and source URL.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

MOEX = "https://iss.moex.com/iss"
HF = "https://datasets-server.huggingface.co"
HF_DATASET = "irlspbru/RFSD"
START_YEAR = int(os.environ.get("PIT_START_YEAR", "2011"))
END_DATE = os.environ.get("PIT_END_DATE", date.today().isoformat())
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pit_output"
RAW = OUT / "raw"

INDEXES = {
    "BROAD": "MOEXBMI",
    "OIL_GAS": "MOEXOG",
    "METALS": "MOEXMM",
    "FINANCE": "MOEXFN",
    "UTILITIES": "MOEXEU",
    "TELECOM": "MOEXTL",
    "CONSUMER": "MOEXCN",
    "CHEMICALS": "MOEXCH",
    "TRANSPORT": "MOEXTN",
    "IT": "MOEXIT",
    "BLUECHIP": "MRBC",
}

RFSD_KEEP = [
    "inn", "year", "name", "short_name", "okved", "outlier",
    "line_1600", "line_1300", "line_1400", "line_1500", "line_1410", "line_1510",
    "line_1210", "line_1230", "line_1250", "line_2110", "line_2120", "line_2200",
    "line_2300", "line_2330", "line_2400", "line_4100", "line_4110", "line_4120",
]


def get(url: str, retries: int = 6, timeout: int = 90) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"Accept": "application/json", "User-Agent": "digital-broker-v9-pit/1.0"})
            with urlopen(req, timeout=timeout) as response:
                raw = response.read()
                if response.status >= 400:
                    raise RuntimeError(f"HTTP {response.status}")
                return raw
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(16, 2 ** attempt))
    raise RuntimeError(f"request failed: {url}: {last}")


def jget(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = get(url)
    payload = json.loads(raw)
    return payload, {"url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def table(payload: dict[str, Any], name: str) -> list[dict[str, Any]]:
    obj = payload.get(name)
    if not isinstance(obj, dict):
        return []
    cols, rows = obj.get("columns"), obj.get("data")
    if not isinstance(cols, list) or not isinstance(rows, list):
        return []
    return [dict(zip(cols, row)) for row in rows if len(row) == len(cols)]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys or ["empty"])
        writer.writeheader()
        writer.writerows(rows)


def quarter_dates() -> list[str]:
    out = []
    end = datetime.fromisoformat(END_DATE).date()
    for year in range(START_YEAR, end.year + 1):
        for month, day in [(3, 31), (6, 30), (9, 30), (12, 31)]:
            d = date(year, month, day)
            if d <= end:
                out.append(d.isoformat())
    if end.isoformat() not in out:
        out.append(end.isoformat())
    return sorted(set(out))


def fetch_constituents() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    dates = quarter_dates()
    for sleeve, index_id in INDEXES.items():
        for pos, asof in enumerate(dates, 1):
            params = {"date": asof, "limit": 500, "iss.meta": "off"}
            url = f"{MOEX}/statistics/engines/stock/markets/index/analytics/{quote(index_id, safe='')}.json?{urlencode(sorted(params.items()))}"
            try:
                payload, meta = jget(url)
                candidates = []
                for name, obj in payload.items():
                    if isinstance(obj, dict) and isinstance(obj.get("columns"), list):
                        for row in table(payload, name):
                            low = {str(k).lower(): v for k, v in row.items()}
                            if low.get("ticker") or low.get("secids") or low.get("secid"):
                                low["source_table"] = name
                                candidates.append(low)
                for row in candidates:
                    secid = str(row.get("ticker") or row.get("secid") or row.get("secids") or "").split(",")[0].strip()
                    if not secid:
                        continue
                    all_rows.append({
                        "requested_date": asof,
                        "sleeve": sleeve,
                        "index_id": index_id,
                        "secid": secid,
                        "weight": row.get("weight"),
                        "effective_from": row.get("from"),
                        "effective_till": row.get("till"),
                        "trade_date": row.get("tradedate") or row.get("trade_session_date"),
                        "shortnames": row.get("shortnames"),
                    })
                meta.update({"kind": "constituents", "sleeve": sleeve, "index_id": index_id, "date": asof, "rows": len(candidates)})
                requests.append(meta)
            except Exception as exc:
                requests.append({"kind": "constituents", "sleeve": sleeve, "index_id": index_id, "date": asof, "url": url, "error": f"{type(exc).__name__}: {exc}"})
            if pos % 16 == 0:
                print(f"{index_id}: {pos}/{len(dates)}", flush=True)
    unique = {}
    for row in all_rows:
        key = (row["requested_date"], row["sleeve"], row["secid"])
        unique[key] = row
    return sorted(unique.values(), key=lambda r: (r["requested_date"], r["sleeve"], r["secid"])), requests


def fetch_emitters() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    reqs: list[dict[str, Any]] = []
    start = 0
    while True:
        params = {"start": start, "iss.meta": "off", "iss.only": "emitters"}
        url = f"{MOEX}/emitters.json?{urlencode(sorted(params.items()))}"
        payload, meta = jget(url)
        page = table(payload, "emitters")
        reqs.append({**meta, "kind": "emitters", "rows": len(page), "start": start})
        if not page:
            break
        for row in page:
            rows.append({str(k).lower(): v for k, v in row.items()})
        if len(page) < 100:
            break
        start += len(page)
        if start > 100000:
            raise RuntimeError("emitter pagination runaway")
    return rows, reqs


def fetch_descriptions(secids: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    reqs: list[dict[str, Any]] = []
    for pos, secid in enumerate(secids, 1):
        params = {"iss.meta": "off", "iss.only": "description"}
        url = f"{MOEX}/securities/{quote(secid, safe='')}.json?{urlencode(sorted(params.items()))}"
        try:
            payload, meta = jget(url)
            desc = {}
            for row in table(payload, "description"):
                key = str(row.get("name") or "").lower()
                desc[key] = row.get("value")
            rows.append({
                "secid": secid,
                "emitter_id": desc.get("emitter_id") or desc.get("emitterid"),
                "isin": desc.get("isin"),
                "issuesize": desc.get("issuesize"),
                "name": desc.get("name"),
                "shortname": desc.get("shortname"),
            })
            reqs.append({**meta, "kind": "description", "secid": secid, "rows": len(desc)})
        except Exception as exc:
            rows.append({"secid": secid, "error": f"{type(exc).__name__}: {exc}"})
            reqs.append({"kind": "description", "secid": secid, "url": url, "error": f"{type(exc).__name__}: {exc}"})
        if pos % 50 == 0:
            print(f"descriptions: {pos}/{len(secids)}", flush=True)
    return rows, reqs


def hf_splits() -> tuple[str, str, dict[str, Any]]:
    url = f"{HF}/splits?{urlencode({'dataset': HF_DATASET})}"
    payload, meta = jget(url)
    splits = payload.get("splits") or []
    if not splits:
        raise RuntimeError("RFSD split discovery returned no splits")
    return str(splits[0].get("config") or "default"), str(splits[0].get("split") or "train"), meta


def hf_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for item in payload.get("rows") or []:
        if isinstance(item, dict) and isinstance(item.get("row"), dict):
            out.append(item["row"])
    return out


def fetch_rfsd(inns: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not inns:
        return [], [], {}
    config, split, split_meta = hf_splits()
    requests = [{**split_meta, "kind": "rfsd_splits"}]
    rows: list[dict[str, Any]] = []
    for batch_start in range(0, len(inns), 15):
        batch = inns[batch_start:batch_start + 15]
        offset = 0
        while True:
            where_variants = [
                f'"inn" IN ({",".join(batch)})',
                f"inn IN ({','.join(batch)})",
                f'"inn" IN ({",".join(repr(x) for x in batch)})',
            ]
            last_exc: Exception | None = None
            page: list[dict[str, Any]] = []
            used = None
            meta = None
            for where in where_variants:
                params = {"dataset": HF_DATASET, "config": config, "split": split, "where": where, "offset": offset, "length": 100}
                url = f"{HF}/filter?{urlencode(params)}"
                try:
                    payload, meta = jget(url)
                    page = hf_rows(payload)
                    used = where
                    break
                except Exception as exc:
                    last_exc = exc
            if meta is None:
                requests.append({"kind": "rfsd_filter", "batch": batch, "offset": offset, "error": f"{type(last_exc).__name__}: {last_exc}" if last_exc else "unknown"})
                break
            requests.append({**meta, "kind": "rfsd_filter", "batch_size": len(batch), "offset": offset, "rows": len(page), "where": used})
            if not page:
                break
            for row in page:
                rows.append({k: row.get(k) for k in RFSD_KEEP if k in row})
            if len(page) < 100:
                break
            offset += len(page)
            if offset > 10000:
                raise RuntimeError("RFSD pagination runaway")
        print(f"RFSD batch {batch_start // 15 + 1}/{(len(inns)+14)//15}: total {len(rows)}", flush=True)
    return rows, requests, {"config": config, "split": split}


def fetch_floater() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    reqs: list[dict[str, Any]] = []
    for secid in ["RUFLBITR", "RUFLCBRNTR3Y", "RUFLBTR"]:
        params = {"from": f"{START_YEAR}-01-01", "till": END_DATE, "interval": 31, "iss.meta": "off"}
        url = f"{MOEX}/engines/stock/markets/index/securities/{quote(secid, safe='')}/candles.json?{urlencode(sorted(params.items()))}"
        try:
            payload, meta = jget(url)
            page = table(payload, "candles")
            for row in page:
                rows.append({"secid": secid, **{str(k).lower(): v for k, v in row.items()}})
            reqs.append({**meta, "kind": "floater_candles", "secid": secid, "rows": len(page)})
        except Exception as exc:
            reqs.append({"kind": "floater_candles", "secid": secid, "url": url, "error": f"{type(exc).__name__}: {exc}"})
    return rows, reqs


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    constituents, requests = fetch_constituents()
    write_csv(OUT / "historical_index_constituents.csv", constituents)
    secids = sorted({r["secid"] for r in constituents if r.get("secid")})
    descriptions, req = fetch_descriptions(secids)
    requests += req
    emitters, req = fetch_emitters()
    requests += req
    write_csv(OUT / "security_descriptions.csv", descriptions)
    write_csv(OUT / "emitters.csv", emitters)
    id_to_inn = {}
    for row in emitters:
        emitter_id = row.get("id") or row.get("emitter_id") or row.get("emitterid")
        inn = row.get("inn") or row.get("taxpayerid") or row.get("taxpayer_id")
        clean = "".join(ch for ch in str(inn or "") if ch.isdigit())
        if emitter_id is not None and clean:
            id_to_inn[str(emitter_id)] = clean
    mapping = []
    for row in descriptions:
        inn = id_to_inn.get(str(row.get("emitter_id")))
        mapping.append({**row, "inn": inn})
    write_csv(OUT / "security_inn_map.csv", mapping)
    inns = sorted({r["inn"] for r in mapping if r.get("inn")})
    rfsd, req, rfsd_meta = fetch_rfsd(inns)
    requests += req
    write_csv(OUT / "rfsd_fundamentals.csv", rfsd)
    floaters, req = fetch_floater()
    requests += req
    write_csv(OUT / "floater_monthly.csv", floaters)
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_year": START_YEAR,
        "end_date": END_DATE,
        "index_count": len(INDEXES),
        "constituent_rows": len(constituents),
        "constituent_dates": len({r['requested_date'] for r in constituents}),
        "unique_secids": len(secids),
        "mapped_inns": len(inns),
        "rfsd_rows": len(rfsd),
        "floater_rows": len(floaters),
        "rfsd": rfsd_meta,
        "files": {},
        "requests": requests,
    }
    for name in ["historical_index_constituents.csv", "security_descriptions.csv", "emitters.csv", "security_inn_map.csv", "rfsd_fundamentals.csv", "floater_monthly.csv"]:
        path = OUT / name
        manifest["files"][name] = {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["constituent_rows", "constituent_dates", "unique_secids", "mapped_inns", "rfsd_rows", "floater_rows"]}, indent=2))
    return 0 if constituents else 2


if __name__ == "__main__":
    raise SystemExit(main())
