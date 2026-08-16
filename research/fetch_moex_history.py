#!/usr/bin/env python3
"""Fetch a reproducible monthly MOEX snapshot for Digital Broker v7."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE = "https://iss.moex.com/iss"
DATE_FROM = os.environ.get("MOEX_FROM", "2000-01-01")
DATE_TO = os.environ.get("MOEX_TILL", date.today().isoformat())
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
RAW = OUT / "raw"


@dataclass(frozen=True)
class AssetSpec:
    secid: str
    engine: str = "stock"
    market: str = "index"
    role: str = "risk"
    family: str = "other"


ASSETS = [
    AssetSpec("IMOEX", role="equity", family="equity_broad_price"),
    AssetSpec("MCFTR", role="equity", family="equity_broad_total_return"),
    AssetSpec("MCFTRR", role="equity", family="equity_broad_total_return_net_resident"),
    AssetSpec("MOEXBMI", role="equity", family="equity_broad_price"),
    AssetSpec("MRBC", role="equity", family="equity_bluechip_price"),
    AssetSpec("MRBCTR", role="equity", family="equity_bluechip_total_return"),
    AssetSpec("MESMTR", role="equity", family="equity_smid_total_return"),
    AssetSpec("MOEXOG", role="equity", family="sector_price"),
    AssetSpec("MOEXMM", role="equity", family="sector_price"),
    AssetSpec("MOEXFN", role="equity", family="sector_price"),
    AssetSpec("MOEXEU", role="equity", family="sector_price"),
    AssetSpec("MOEXTL", role="equity", family="sector_price"),
    AssetSpec("MOEXCN", role="equity", family="sector_price"),
    AssetSpec("MOEXCH", role="equity", family="sector_price"),
    AssetSpec("MOEXTN", role="equity", family="sector_price"),
    AssetSpec("MOEXRE", role="equity", family="sector_price"),
    AssetSpec("MOEXIT", role="equity", family="sector_price"),
    AssetSpec("MEOGTR", role="equity", family="sector_total_return"),
    AssetSpec("MEOGTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("MEMMTR", role="equity", family="sector_total_return"),
    AssetSpec("MEMMTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("MEFNTR", role="equity", family="sector_total_return"),
    AssetSpec("MEFNTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("MEEUTR", role="equity", family="sector_total_return"),
    AssetSpec("MEEUTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("METLTR", role="equity", family="sector_total_return"),
    AssetSpec("METLTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("MECNTR", role="equity", family="sector_total_return"),
    AssetSpec("MECNTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("MECHTR", role="equity", family="sector_total_return"),
    AssetSpec("MECHTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("METNTR", role="equity", family="sector_total_return"),
    AssetSpec("METNTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("MEITTR", role="equity", family="sector_total_return"),
    AssetSpec("MEITTRR", role="equity", family="sector_total_return_net_resident"),
    AssetSpec("RGBITR", role="bond", family="bond_all_total_return"),
    AssetSpec("RUGBITR1Y", role="cash", family="bond_short_total_return"),
    AssetSpec("RUGBITR3Y", role="bond", family="bond_1_3y_total_return"),
    AssetSpec("RUGBITR5Y", role="bond", family="bond_3_5y_total_return"),
    AssetSpec("RUGBITR10Y", role="bond", family="bond_5_10y_total_return"),
    AssetSpec("RUGBITR5+", role="bond", family="bond_5plus_total_return"),
    AssetSpec("RUSFARIND", role="cash", family="money_market"),
    AssetSpec("RUGOLD", role="gold", family="gold_rub"),
    AssetSpec("GLDRUB_TOM", engine="currency", market="selt", role="gold", family="gold_rub_traded"),
    AssetSpec("USDRUB_TOM", engine="currency", market="selt", role="fx", family="fx_usd_rub"),
    AssetSpec("CNYRUB_TOM", engine="currency", market="selt", role="fx", family="fx_cny_rub"),
]


def canonical_url(spec: AssetSpec) -> str:
    path = f"engines/{quote(spec.engine, safe='')}/markets/{quote(spec.market, safe='')}/securities/{quote(spec.secid, safe='')}/candles.json"
    params = {"from": DATE_FROM, "interval": 31, "iss.meta": "off", "till": DATE_TO}
    return f"{BASE}/{path}?{urlencode(sorted(params.items()))}"


def download(url: str, retries: int = 5, timeout: int = 60) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"Accept": "application/json", "User-Agent": "digital-broker-v7-research/1.0"})
            with urlopen(req, timeout=timeout) as response:
                raw = response.read()
                if "json" not in (response.headers.get("Content-Type") or "").lower():
                    raise RuntimeError("unexpected content type")
                return raw
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(8, 2**attempt))
    raise RuntimeError(f"failed to download {url}: {last}")


def table(payload: dict[str, Any], name: str) -> list[dict[str, Any]]:
    obj = payload.get(name)
    if not isinstance(obj, dict) or not isinstance(obj.get("columns"), list) or not isinstance(obj.get("data"), list):
        return []
    return [dict(zip(obj["columns"], row)) for row in obj["data"] if len(row) == len(obj["columns"])]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    long_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for pos, spec in enumerate(ASSETS, start=1):
        url = canonical_url(spec)
        raw_path = RAW / f"{spec.engine}__{spec.market}__{spec.secid.replace('+', '_plus')}.json"
        try:
            raw = download(url)
            raw_path.write_bytes(raw)
            candles = table(json.loads(raw), "candles")
            normalized = []
            for row in candles:
                begin = str(row.get("begin") or "")
                if begin:
                    normalized.append({
                        "secid": spec.secid, "engine": spec.engine, "market": spec.market,
                        "role": spec.role, "family": spec.family, "begin": begin,
                        "end": str(row.get("end") or ""), "open": row.get("open"),
                        "close": row.get("close"), "high": row.get("high"), "low": row.get("low"),
                        "value": row.get("value"), "volume": row.get("volume"),
                    })
            normalized.sort(key=lambda x: x["begin"])
            long_rows.extend(normalized)
            status_rows.append({
                **asdict(spec), "canonical_url": url, "status": "ok" if normalized else "empty",
                "rows": len(normalized), "start": normalized[0]["begin"] if normalized else None,
                "end": normalized[-1]["end"] if normalized else None,
                "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw), "error": None,
            })
        except Exception as exc:
            status_rows.append({
                **asdict(spec), "canonical_url": url, "status": "error", "rows": 0,
                "start": None, "end": None, "raw_sha256": None, "raw_bytes": 0,
                "error": f"{type(exc).__name__}: {exc}",
            })
        print(f"[{pos:02d}/{len(ASSETS):02d}] {spec.secid}: {status_rows[-1]['status']} {status_rows[-1]['rows']}", flush=True)

    long_rows.sort(key=lambda x: (x["begin"], x["secid"]))
    csv_path = OUT / "moex_monthly_snapshot.csv"
    fields = ["secid", "engine", "market", "role", "family", "begin", "end", "open", "close", "high", "low", "value", "volume"]
    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(long_rows)

    manifest = {
        "schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "date_from": DATE_FROM, "date_to": DATE_TO, "source": "MOEX ISS public API",
        "rows": len(long_rows), "assets_requested": len(ASSETS),
        "assets_nonempty": sum(row["status"] == "ok" for row in status_rows),
        "snapshot_csv": str(csv_path.relative_to(ROOT.parent)),
        "snapshot_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(), "requests": status_rows,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("rows", "assets_requested", "assets_nonempty", "snapshot_sha256")}, indent=2))
    return 0 if long_rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
