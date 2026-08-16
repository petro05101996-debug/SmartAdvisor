#!/usr/bin/env python3
"""Build a genuine point-in-time Russian equity universe for Digital Broker v9.

The universe is reconstructed from month-end MOEX board-history snapshots, not
from today's surviving securities. Annual RFSD statements are attached later
using a conservative July-1-of-year+1 availability rule. This script only
fetches and records source evidence; it does not fit or select a strategy.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
OUT = ROOT / "pit_universe_output"
BOARDS = ("TQBR", "EQBR")

HISTORY_COLUMNS = (
    "BOARDID,TRADEDATE,SHORTNAME,SECID,NUMTRADES,VALUE,OPEN,LOW,HIGH,"
    "LEGALCLOSEPRICE,CLOSE,WAPRICE,MARKETPRICE2,MARKETPRICE3,ADMITTEDQUOTE"
)
RFSD_KEEP = [
    "inn", "year", "name", "short_name", "okved", "okved_section", "outlier",
    "eligible", "filed", "imputed", "line_1600", "line_1300", "line_1400",
    "line_1500", "line_1410", "line_1510", "line_1210", "line_1230",
    "line_1250", "line_2110", "line_2120", "line_2200", "line_2300",
    "line_2330", "line_2400", "line_4100", "line_4110", "line_4120",
]


def get(url: str, retries: int = 6, timeout: int = 90) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "digital-broker-v9-pit-universe/1.0",
            })
            with urlopen(req, timeout=timeout) as response:
                raw = response.read()
                if response.status >= 400:
                    raise RuntimeError(f"HTTP {response.status}")
                return raw
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(16, 2**attempt))
    raise RuntimeError(f"request failed: {url}: {last}")


def jget(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = get(url)
    payload = json.loads(raw)
    return payload, {
        "url": url,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def table(payload: dict[str, Any], name: str) -> list[dict[str, Any]]:
    block = payload.get(name)
    if not isinstance(block, dict):
        return []
    cols, data = block.get("columns"), block.get("data")
    if not isinstance(cols, list) or not isinstance(data, list):
        return []
    return [dict(zip(cols, row)) for row in data if len(row) == len(cols)]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields or ["empty"])
        writer.writeheader()
        writer.writerows(rows)


def month_ends() -> list[str]:
    end = datetime.fromisoformat(END_DATE).date()
    result: list[str] = []
    year, month = START_YEAR, 1
    while (year, month) <= (end.year, end.month):
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        result.append((next_month.fromordinal(next_month.toordinal() - 1)).isoformat())
        month += 1
        if month == 13:
            month, year = 1, year + 1
    return [x for x in result if x <= END_DATE]


def fetch_board_date(board: str, requested_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requests: list[dict[str, Any]] = []
    requested = datetime.fromisoformat(requested_date).date()
    for lag in range(11):
        actual = requested.fromordinal(requested.toordinal() - lag).isoformat()
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            params = {
                "date": actual,
                "start": start,
                "iss.meta": "off",
                "iss.only": "history",
                "history.columns": HISTORY_COLUMNS,
            }
            path = f"history/engines/stock/markets/shares/boards/{quote(board, safe='')}/securities.json"
            url = f"{MOEX}/{path}?{urlencode(sorted(params.items()))}"
            payload, meta = jget(url)
            page = table(payload, "history")
            requests.append({**meta, "kind": "history", "board": board, "requested_date": requested_date, "actual_date": actual, "start": start, "rows": len(page)})
            if not page:
                break
            rows.extend(page)
            if len(page) < 100:
                break
            start += len(page)
            if start > 5000:
                raise RuntimeError(f"history pagination runaway: {board} {actual}")
        if rows:
            normalized = []
            for row in rows:
                low = {str(k).lower(): v for k, v in row.items()}
                low["snapshot_month"] = requested_date
                low["snapshot_trade_date"] = actual
                low["source_board"] = board
                normalized.append(low)
            return normalized, requests
    return [], requests


def fetch_month(requested_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    for board in BOARDS:
        board_rows, board_requests = fetch_board_date(board, requested_date)
        rows.extend(board_rows)
        requests.extend(board_requests)
    # Prefer TQBR, then the row with the larger traded value.
    rows.sort(key=lambda r: (
        str(r.get("secid") or ""),
        1 if str(r.get("source_board")) == "TQBR" else 0,
        float(r.get("value") or 0.0),
    ))
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        secid = str(row.get("secid") or "").strip()
        if secid:
            unique[secid] = row
    return sorted(unique.values(), key=lambda r: str(r.get("secid"))), requests


def fetch_description(secid: str) -> tuple[dict[str, Any], dict[str, Any]]:
    params = {"iss.meta": "off", "iss.only": "description,boards"}
    url = f"{MOEX}/securities/{quote(secid, safe='')}.json?{urlencode(sorted(params.items()))}"
    payload, meta = jget(url)
    desc: dict[str, Any] = {}
    for row in table(payload, "description"):
        name = str(row.get("name") or "").lower()
        if name:
            desc[name] = row.get("value")
    boards = [{str(k).lower(): v for k, v in row.items()} for row in table(payload, "boards")]
    primary = sorted(boards, key=lambda r: (int(r.get("is_primary") or 0), int(r.get("is_traded") or 0)), reverse=True)
    return {
        "secid": secid,
        "name": desc.get("name"),
        "shortname": desc.get("shortname"),
        "isin": desc.get("isin"),
        "regnumber": desc.get("regnumber"),
        "issuesize": desc.get("issuesize"),
        "emitent_id": desc.get("emitent_id") or desc.get("emitter_id") or desc.get("emitterid"),
        "emitent_inn": desc.get("emitent_inn") or desc.get("inn") or desc.get("taxpayerid"),
        "type": desc.get("type"),
        "group": desc.get("group"),
        "primary_boardid": primary[0].get("boardid") if primary else None,
    }, {**meta, "kind": "description", "secid": secid, "description_keys": sorted(desc)}


def fetch_emitters() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    start = 0
    while True:
        params = {"start": start, "iss.meta": "off", "iss.only": "emitters"}
        url = f"{MOEX}/emitters.json?{urlencode(sorted(params.items()))}"
        payload, meta = jget(url)
        page = table(payload, "emitters")
        requests.append({**meta, "kind": "emitters", "start": start, "rows": len(page)})
        if not page:
            break
        rows.extend({str(k).lower(): v for k, v in row.items()} for row in page)
        if len(page) < 100:
            break
        start += len(page)
        if start > 100000:
            raise RuntimeError("emitter pagination runaway")
    return rows, requests


def clean_inn(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def discover_rfsd() -> tuple[str, str, dict[str, Any]]:
    url = f"{HF}/splits?{urlencode({'dataset': HF_DATASET})}"
    payload, meta = jget(url)
    splits = payload.get("splits") or []
    if not splits:
        raise RuntimeError("RFSD split discovery returned no split")
    return str(splits[0].get("config") or "default"), str(splits[0].get("split") or "train"), meta


def hf_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item in payload.get("rows") or []:
        if isinstance(item, dict) and isinstance(item.get("row"), dict):
            result.append(item["row"])
    return result


def fetch_rfsd(inns: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    config, split, split_meta = discover_rfsd()
    requests: list[dict[str, Any]] = [{**split_meta, "kind": "rfsd_splits"}]
    rows: list[dict[str, Any]] = []
    for batch_no, start in enumerate(range(0, len(inns), 12), 1):
        batch = inns[start:start + 12]
        offset = 0
        while True:
            clauses = [
                f'"inn" IN ({",".join(batch)})',
                f"inn IN ({','.join(batch)})",
                f'"inn" IN ({",".join(repr(x) for x in batch)})',
            ]
            page: list[dict[str, Any]] | None = None
            used_url = ""
            used_meta: dict[str, Any] = {}
            errors = []
            for where in clauses:
                params = {"dataset": HF_DATASET, "config": config, "split": split, "where": where, "offset": offset, "length": 100}
                url = f"{HF}/filter?{urlencode(params)}"
                try:
                    payload, used_meta = jget(url)
                    page = hf_rows(payload)
                    used_url = url
                    break
                except Exception as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")
            if page is None:
                requests.append({"kind": "rfsd_filter", "batch": batch, "offset": offset, "url": used_url, "errors": errors})
                break
            requests.append({**used_meta, "kind": "rfsd_filter", "batch_size": len(batch), "offset": offset, "rows": len(page)})
            if not page:
                break
            rows.extend({key: row.get(key) for key in RFSD_KEEP if key in row} for row in page)
            if len(page) < 100:
                break
            offset += len(page)
            if offset > 10000:
                raise RuntimeError("RFSD pagination runaway")
        print(f"RFSD batch {batch_no}/{(len(inns) + 11)//12}: total rows={len(rows)}", flush=True)
    unique = {}
    for row in rows:
        key = (clean_inn(row.get("inn")), row.get("year"))
        unique[key] = row
    return sorted(unique.values(), key=lambda r: (clean_inn(r.get("inn")), int(r.get("year") or 0))), requests, {"config": config, "split": split}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dates = month_ends()
    universe: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_month, month): month for month in dates}
        done = 0
        for future in as_completed(futures):
            month = futures[future]
            try:
                rows, req = future.result()
                universe.extend(rows)
                requests.extend(req)
            except Exception as exc:
                requests.append({"kind": "month", "requested_date": month, "error": f"{type(exc).__name__}: {exc}"})
            done += 1
            if done % 12 == 0:
                print(f"history months: {done}/{len(dates)}, rows={len(universe)}", flush=True)
    universe.sort(key=lambda r: (str(r.get("snapshot_month")), str(r.get("secid"))))
    write_csv(OUT / "monthly_equity_universe.csv", universe)

    secids = sorted({str(row.get("secid")) for row in universe if row.get("secid")})
    descriptions: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(fetch_description, secid): secid for secid in secids}
        done = 0
        for future in as_completed(futures):
            secid = futures[future]
            try:
                row, meta = future.result()
                descriptions.append(row)
                requests.append(meta)
            except Exception as exc:
                descriptions.append({"secid": secid, "error": f"{type(exc).__name__}: {exc}"})
                requests.append({"kind": "description", "secid": secid, "error": f"{type(exc).__name__}: {exc}"})
            done += 1
            if done % 50 == 0:
                print(f"descriptions: {done}/{len(secids)}", flush=True)

    emitters, req = fetch_emitters()
    requests.extend(req)
    emitter_map: dict[str, str] = {}
    for row in emitters:
        emitter_id = row.get("id") or row.get("emitent_id") or row.get("emitter_id")
        inn = clean_inn(row.get("inn") or row.get("emitent_inn") or row.get("taxpayerid"))
        if emitter_id is not None and inn:
            emitter_map[str(emitter_id)] = inn
    for row in descriptions:
        direct = clean_inn(row.get("emitent_inn"))
        row["inn"] = direct or emitter_map.get(str(row.get("emitent_id")), "")
    descriptions.sort(key=lambda r: str(r.get("secid")))
    write_csv(OUT / "security_master.csv", descriptions)
    write_csv(OUT / "emitters.csv", emitters)

    inns = sorted({row["inn"] for row in descriptions if row.get("inn")})
    rfsd, req, rfsd_meta = fetch_rfsd(inns)
    requests.extend(req)
    write_csv(OUT / "rfsd_fundamentals.csv", rfsd)

    months = sorted({row.get("snapshot_month") for row in universe if row.get("snapshot_month")})
    manifest = {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_year": START_YEAR,
        "end_date": END_DATE,
        "boards": list(BOARDS),
        "universe_rows": len(universe),
        "universe_months": len(months),
        "first_universe_month": months[0] if months else None,
        "last_universe_month": months[-1] if months else None,
        "unique_secids": len(secids),
        "mapped_inns": len(inns),
        "rfsd_rows": len(rfsd),
        "rfsd_unique_inns": len({clean_inn(row.get('inn')) for row in rfsd if clean_inn(row.get('inn'))}),
        "rfsd": rfsd_meta,
        "files": {},
        "requests": requests,
    }
    for name in ["monthly_equity_universe.csv", "security_master.csv", "emitters.csv", "rfsd_fundamentals.csv"]:
        path = OUT / name
        manifest["files"][name] = {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ["universe_rows", "universe_months", "first_universe_month", "last_universe_month", "unique_secids", "mapped_inns", "rfsd_rows", "rfsd_unique_inns"]}, ensure_ascii=False, indent=2), flush=True)
    return 0 if universe and inns else 2


if __name__ == "__main__":
    raise SystemExit(main())
