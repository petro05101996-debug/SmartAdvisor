#!/usr/bin/env python3
"""Fetch current MOEX constituent snapshots for short and long OFZ indices."""
from __future__ import annotations
import csv, hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE="https://iss.moex.com/iss"
OUT=Path(__file__).resolve().parent/"bond_constituents_output"
INDEX_IDS=["RUGBITR1Y","RUGBITR5+"]

def get(url: str, retries: int=6) -> bytes:
    last=None
    for attempt in range(retries):
        try:
            req=Request(url,headers={"Accept":"application/json","User-Agent":"digital-broker-v8-bond-constituents/1.0"})
            with urlopen(req,timeout=90) as response:
                raw=response.read()
                if "json" not in (response.headers.get("Content-Type") or "").lower():
                    raise RuntimeError("non-JSON response")
                return raw
        except (HTTPError,URLError,TimeoutError,RuntimeError) as exc:
            last=exc
            if attempt+1<retries: time.sleep(min(16,2**attempt))
    raise RuntimeError(f"request failed: {url}: {last}")

def table(payload: dict[str,Any], name: str) -> list[dict[str,Any]]:
    obj=payload.get(name)
    if not isinstance(obj,dict): return []
    cols,data=obj.get("columns"),obj.get("data")
    if not isinstance(cols,list) or not isinstance(data,list): return []
    return [dict(zip(cols,row)) for row in data if len(row)==len(cols)]

def main() -> int:
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]; requests={}
    for index_id in INDEX_IDS:
        params={"limit":500,"iss.meta":"off"}
        path=f"statistics/engines/stock/markets/index/analytics/{quote(index_id,safe='')}.json"
        url=f"{BASE}/{path}?{urlencode(sorted(params.items()))}"
        raw=get(url); payload=json.loads(raw); count=0
        for name,obj in payload.items():
            if not isinstance(obj,dict) or not isinstance(obj.get("columns"),list): continue
            for item in table(payload,name):
                row={str(k).lower():v for k,v in item.items()}
                row["source_table"]=name; row["index_id"]=index_id
                rows.append(row); count+=1
        requests[index_id]={"url":url,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"rows":count}
        print(index_id,count,flush=True)
    keys=[]; seen=set()
    for row in rows:
        for key in row:
            if key not in seen: seen.add(key); keys.append(key)
    path=OUT/"current_bond_index_constituents.csv"
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=keys); w.writeheader(); w.writerows(rows)
    manifest={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"rows":len(rows),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"requests":requests}
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
