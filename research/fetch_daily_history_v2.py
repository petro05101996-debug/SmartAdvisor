from __future__ import annotations

import json
import time
import urllib.parse

import fetch_daily_history as base

# GLDRUB_TOM is not an index security; CBR gold is the authoritative long gold series.
base.INDEX_SERIES = [x for x in base.INDEX_SERIES if x != "GLDRUB_TOM"]


def fetch_candles_full(secid: str):
    rows = []
    start = 0
    previous_start = -1
    for _page in range(500):
        if start == previous_start:
            raise RuntimeError(f"Pagination did not advance for {secid}: {start}")
        previous_start = start
        params = urllib.parse.urlencode({
            "from": base.FROM,
            "till": base.TILL,
            "interval": 24,
            "start": start,
            "iss.meta": "off",
            "candles.columns": "begin,close",
        })
        url = f"https://iss.moex.com/iss/engines/stock/markets/index/securities/{secid}/candles.json?{params}"
        payload = json.loads(base.get_bytes(url))
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
                rows.append({
                    "date": str(begin)[:10],
                    "secid": secid,
                    "close": float(close),
                    "source": "MOEX_ISS_CANDLES",
                })
        start += len(data)
        time.sleep(0.03)
    else:
        raise RuntimeError(f"Too many pages for {secid}")
    return rows


base.fetch_candles = fetch_candles_full

if __name__ == "__main__":
    base.main()
