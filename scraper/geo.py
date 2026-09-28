"""座標與距離：用 591 社區資料取得物件座標，計算與中心點的距離。"""
from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}
INFO_API = "https://bff-market.591.com.tw/v3/web/community/info"


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class GeoCache:
    """社區座標快取（社區不會搬家，查過就記住）。"""

    def __init__(self, path: Path, log=print):
        self.path = Path(path)
        self.log = log
        self.data = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {}
        self.fetched = 0

    def community(self, cid) -> tuple[float, float] | None:
        key = str(cid)
        if key in self.data:
            v = self.data[key]
            return tuple(v) if v else None
        try:
            r = requests.get(INFO_API, params={"id": cid, "timestamp": int(time.time() * 1000)},
                             headers=UA, timeout=20)
            s = ((r.json() or {}).get("data") or {}).get("surrounding") or {}
            lat, lng = float(s.get("lat") or 0), float(s.get("lng") or 0)
            v = [lat, lng] if lat and lng else None
        except Exception as e:  # noqa: BLE001
            self.log(f"    社區 {cid} 座標查詢失敗：{e.__class__.__name__}")
            return None  # 失敗不寫入快取，下次再試
        self.data[key] = v
        self.fetched += 1
        time.sleep(random.uniform(0.6, 1.2))
        return tuple(v) if v else None

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data), "utf-8")


def locate(items: list[dict], cache: GeoCache) -> None:
    """為物件補上 lat/lng（社區座標優先，其次詳情頁座標）。"""
    for it in items:
        if it.get("lat") and it.get("lng"):
            continue
        ll = cache.community(it["community_id"]) if it.get("community_id") else None
        if not ll:
            d = it.get("detail") or {}
            if d.get("lat") and d.get("lng"):
                ll = (d["lat"], d["lng"])
        if ll:
            it["lat"], it["lng"] = round(ll[0], 6), round(ll[1], 6)


def centers(near) -> list[dict]:
    """near 可以是單一圓心（dict）或多個圓心（list）。"""
    if not near:
        return []
    return [near] if isinstance(near, dict) else list(near)


def apply_distance(items: list[dict], near) -> None:
    """算出到每個圓心的距離，記下「在範圍內、最近的那個圓心」（都不在範圍內就記最近的）。"""
    cs = centers(near)
    for it in items:
        if not (it.get("lat") and it.get("lng")) or not cs:
            continue
        ds = [(round(haversine_km(c["lat"], c["lng"], it["lat"], it["lng"]), 2), c) for c in cs]
        inside = [x for x in ds if x[0] <= float(x[1].get("radius_km", 2))]
        d, c = min(inside or ds, key=lambda x: x[0])
        it["distance_km"], it["near_name"] = d, c.get("name", "中心點")
        it["in_range"] = bool(inside)


def within(item: dict, near) -> bool:
    """在任一圓心的範圍內就保留；沒有座標的物件先保留（之後讀詳情頁再判斷）。"""
    if not centers(near) or item.get("distance_km") is None:
        return True
    return bool(item.get("in_range"))
