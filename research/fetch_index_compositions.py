from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://iss.moex.com/iss"
AS_OF = "2026-07-31"
INDICES = {
    "OIL_GAS": "MOEXOG",
    "METALS": "MOEXMM",
    "FINANCE": "MOEXFN",
    "UTILITIES": "MOEXEU",
    "TELECOM": "MOEXTL",
    "CONSUMER": "MOEXCN",
    "CHEMICALS": "MOEXCH",
    "TRANSPORT": "MOEXTN",
    "IT": "MOEXIT",
    "BROAD_EQ": "IMOEX",
}
OUT = Path("research/data_extended")


def get_json(url: str, retries: int = 5) -> dict:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "digital-broker-v7-research/1.0"})
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}") from last


def rows_from_block(payload: dict) -> list[dict]:
    preferred = ["analytics", "indices", "securities"]
    names = preferred + [name for name in payload if name not in preferred]
    for name in names:
        block = payload.get(name)
        if not isinstance(block, dict):
            continue
        columns = block.get("columns") or []
        data = block.get("data") or []
        normalized = {str(column).lower() for column in columns}
        if data and normalized.intersection({"secid", "ticker"}):
            return [dict(zip(columns, row)) for row in data]
    return []


def first(row: dict, *names: str):
    lower = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        value = lower.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": AS_OF,
        "source": "MOEX ISS index analytics",
        "note": "The public endpoint supplied membership periods and index weights for this snapshot; verify non-null weights after each refresh.",
        "indices": {},
    }
    for sleeve, index_id in INDICES.items():
        path = f"/statistics/engines/stock/markets/index/analytics/{urllib.parse.quote(index_id)}.json"
        query = urllib.parse.urlencode({"iss.meta": "off", "date": AS_OF, "limit": 100})
        url = BASE + path + "?" + query
        payload = get_json(url)
        rows = rows_from_block(payload)
        normalized = []
        for row in rows:
            secid = first(row, "SECID", "TICKER")
            if not secid:
                continue
            normalized.append({
                "secid": str(secid),
                "shortname": first(row, "SHORTNAME", "NAME"),
                "from": first(row, "FROM"),
                "till": first(row, "TILL"),
                "tradingsession": first(row, "TRADINGSESSION"),
                "weight": first(row, "WEIGHT"),
            })
        result["indices"][sleeve] = {
            "index_id": index_id,
            "url": url,
            "constituents": normalized,
            "count": len(normalized),
        }
        print(f"{sleeve}/{index_id}: {len(normalized)}")
        time.sleep(0.2)
    raw = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    (OUT / "current_compositions.json").write_bytes(raw)
    (OUT / "current_compositions.sha256").write_text(hashlib.sha256(raw).hexdigest() + "\n")


if __name__ == "__main__":
    main()
