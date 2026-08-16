from __future__ import annotations

import json
import time
import urllib.parse

import fetch_daily_history as base

base.INDEX_SERIES = [x for x in base.INDEX_SERIES if x != "GLDRUB_TOM"]


def fetch_candles_fast(secid: str):
    rows = []
    start = 0
    for _page in range(200):
        params = urllib.parse.urlencode({
            "from": base.FROM,
            "till": base.TILL,
            "interval": 24,
            "start": start,
            "limit": 500,
            "iss.meta": "off",
            "iss.only": "candles,candles.cursor",
            "candles.columns": "begin,close",
            "candles.cursor.columns": "INDEX,TOTAL,PAGESIZE",
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
            if rec.get("begin") and rec.get("close") is not None:
                rows.append({
                    "date": str(rec["begin"])[:10],
                    "secid": secid,
                    "close": float(rec["close"]),
                    "source": "MOEX_ISS_CANDLES",
                })
        start += len(data)
        cursor = payload.get("candles.cursor", {})
        ccols = cursor.get("columns", [])
        cdata = cursor.get("data", [])
        total = None
        if cdata:
            crec = dict(zip(ccols, cdata[0]))
            total = crec.get("TOTAL")
        if total is not None and start >= int(total):
            break
        time.sleep(0.01)
    else:
        raise RuntimeError(f"Too many daily pages for {secid}")
    return rows


base.fetch_candles = fetch_candles_fast

if __name__ == "__main__":
    base.main()
