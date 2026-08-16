#!/usr/bin/env python3
"""Repair MOEX emitter pagination and fetch RFSD rows for mapped Russian shares.

Runs after fetch_pit_universe_v2.py in the same workflow. It deliberately keeps
only common/preferred shares, resolves their emitter INNs from the complete
MOEX emitter catalogue, then queries RFSD with supported equality/OR predicates.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MOEX = "https://iss.moex.com/iss"
HF = "https://datasets-server.huggingface.co"
DATASET = "irlspbru/RFSD"
ROOT = Path(__file__).resolve().parent / "pit_universe_output"
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
            req = Request(url, headers={"Accept": "application/json", "User-Agent": "digital-broker-v9-repair/1.0"})
            with urlopen(req, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(16, 2 ** attempt))
    raise RuntimeError(f"request failed: {url}: {last}")


def jget(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = get(url)
    return json.loads(raw), {"url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def table(payload: dict[str, Any], name: str) -> list[dict[str, Any]]:
    block = payload.get(name)
    if not isinstance(block, dict):
        return []
    cols, data = block.get("columns"), block.get("data")
    if not isinstance(cols, list) or not isinstance(data, list):
        return []
    return [dict(zip(cols, row)) for row in data if len(row) == len(cols)]


def clean_inn(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return "".join(ch for ch in text if ch.isdigit())


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


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
        writer.writeheader(); writer.writerows(rows)


def fetch_emitter_page(start: int) -> tuple[int, list[dict[str, Any]], dict[str, Any], int | None, int | None]:
    params = {"start": start, "iss.meta": "off", "iss.only": "emitters,emitters.cursor"}
    url = f"{MOEX}/emitters.json?{urlencode(sorted(params.items()))}"
    payload, meta = jget(url)
    page = [{str(k).lower(): v for k, v in row.items()} for row in table(payload, "emitters")]
    cursor = table(payload, "emitters.cursor")
    total = int(cursor[0].get("TOTAL")) if cursor and cursor[0].get("TOTAL") is not None else None
    page_size = int(cursor[0].get("PAGESIZE")) if cursor and cursor[0].get("PAGESIZE") is not None else None
    return start, page, meta, total, page_size


def fetch_all_emitters() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    start, first, first_meta, total, page_size = fetch_emitter_page(0)
    requests = [{**first_meta, "kind": "emitters", "start": 0, "rows": len(first), "total": total, "page_size": page_size}]
    rows = list(first)
    size = page_size or max(len(first), 20)
    if total is None:
        next_start = size
        while True:
            st, page, meta, _, _ = fetch_emitter_page(next_start)
            requests.append({**meta, "kind": "emitters", "start": st, "rows": len(page)})
            if not page: break
            rows.extend(page); next_start += len(page)
            if next_start > 100000: raise RuntimeError("emitter pagination runaway")
    else:
        starts = list(range(size, total, size))
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(fetch_emitter_page, st): st for st in starts}
            done = 0
            for future in as_completed(futures):
                st, page, meta, _, _ = future.result()
                rows.extend(page)
                requests.append({**meta, "kind": "emitters", "start": st, "rows": len(page)})
                done += 1
                if done % 100 == 0: print(f"emitter pages {done}/{len(starts)}", flush=True)
    unique = {}
    for row in rows:
        key = row.get("emitter_id") or row.get("id") or row.get("emitent_id")
        if key is not None: unique[str(key)] = row
    return sorted(unique.values(), key=lambda r: int(r.get("emitter_id") or r.get("id") or 0)), requests


def discover_split() -> tuple[str, str, dict[str, Any]]:
    payload, meta = jget(f"{HF}/splits?{urlencode({'dataset': DATASET})}")
    splits = payload.get("splits") or []
    if not splits: raise RuntimeError("RFSD split discovery returned no rows")
    return str(splits[0].get("config") or "default"), str(splits[0].get("split") or "train"), meta


def hf_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [item["row"] for item in payload.get("rows") or [] if isinstance(item, dict) and isinstance(item.get("row"), dict)]


def fetch_rfsd_batch(batch: list[str], config: str, split: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []; reqs: list[dict[str, Any]] = []; offset = 0
    numeric = " OR ".join(f'\"inn\"={int(x)}' for x in batch)
    strings = " OR ".join(f'\"inn\"=\'{x}\'' for x in batch)
    while True:
        page = None; errors = []
        for where in (numeric, strings):
            params = {"dataset": DATASET, "config": config, "split": split, "where": where, "offset": offset, "length": 100}
            url = f"{HF}/filter?{urlencode(params)}"
            try:
                payload, meta = jget(url); page = hf_rows(payload)
                reqs.append({**meta, "kind": "rfsd_filter", "batch": batch, "offset": offset, "rows": len(page), "where": where})
                break
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        if page is None:
            reqs.append({"kind": "rfsd_filter", "batch": batch, "offset": offset, "errors": errors}); break
        if not page: break
        rows.extend({key: row.get(key) for key in RFSD_KEEP if key in row} for row in page)
        if len(page) < 100: break
        offset += len(page)
        if offset > 10000: raise RuntimeError("RFSD pagination runaway")
    return rows, reqs


def main() -> int:
    master_path = ROOT / "security_master.csv"; manifest_path = ROOT / "manifest.json"
    master = read_csv(master_path); manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shares = [row for row in master if str(row.get("type") or "") in {"common_share", "preferred_share"} or str(row.get("group") or "") == "stock_shares"]
    emitters, requests = fetch_all_emitters()
    emitter_map = {}
    for row in emitters:
        key = row.get("emitter_id") or row.get("id") or row.get("emitent_id")
        inn = clean_inn(row.get("inn") or row.get("emitent_inn") or row.get("taxpayerid"))
        if key is not None and inn: emitter_map[str(key)] = inn
    for row in master:
        direct = clean_inn(row.get("emitent_inn") or row.get("inn"))
        row["inn"] = direct or emitter_map.get(str(row.get("emitent_id") or ""), "")
    write_csv(master_path, master); write_csv(ROOT / "emitters.csv", emitters)
    mapped = sorted({clean_inn(row.get("inn")) for row in shares if clean_inn(row.get("inn"))})
    config, split, split_meta = discover_split(); requests.append({**split_meta, "kind": "rfsd_splits"})
    all_rows: list[dict[str, Any]] = []
    batches = [mapped[i:i+6] for i in range(0, len(mapped), 6)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_rfsd_batch, batch, config, split): batch for batch in batches}
        done = 0
        for future in as_completed(futures):
            rows, req = future.result(); all_rows.extend(rows); requests.extend(req); done += 1
            if done % 10 == 0: print(f"RFSD batches {done}/{len(batches)}, rows={len(all_rows)}", flush=True)
    unique = {}
    for row in all_rows:
        key = (clean_inn(row.get("inn")), int(row.get("year") or 0)); unique[key] = row
    rfsd = sorted(unique.values(), key=lambda r: (clean_inn(r.get("inn")), int(r.get("year") or 0)))
    write_csv(ROOT / "rfsd_fundamentals.csv", rfsd)
    manifest["emitter_rows"] = len(emitters); manifest["share_security_rows"] = len(shares)
    manifest["mapped_inns"] = len(mapped); manifest["rfsd_rows"] = len(rfsd)
    manifest["rfsd_unique_inns"] = len({clean_inn(row.get("inn")) for row in rfsd if clean_inn(row.get("inn"))})
    manifest["identifier_repair_requests"] = requests
    for name in ["security_master.csv", "emitters.csv", "rfsd_fundamentals.csv"]:
        p = ROOT / name; manifest["files"][name] = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k:manifest[k] for k in ["emitter_rows","share_security_rows","mapped_inns","rfsd_rows","rfsd_unique_inns"]}, indent=2), flush=True)
    return 0 if len(mapped) >= 80 and len(rfsd) >= 300 else 2

if __name__ == "__main__": raise SystemExit(main())
