"""距離計算與地理範圍篩選。"""
import sys, tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper import geo

near = {"name": "美麗歐洲社區", "lat": 24.965501, "lng": 121.237385, "radius_km": 2}
d = geo.haversine_km(near["lat"], near["lng"], 24.9621721, 121.2655383)
assert 2.8 < d < 2.95, d
tmp = Path(tempfile.mkdtemp())
c = geo.GeoCache(tmp / "g.json", log=lambda *a: None)
c.data = {"1": [24.9660, 121.2400], "2": None}
items = [{"id": "a", "community_id": 1}, {"id": "b", "community_id": 2, "detail": {"lat": 24.9582, "lng": 121.2052}},
         {"id": "c"}, {"id": "d", "lat": 24.9655, "lng": 121.2374}]
geo.locate(items, c)
geo.apply_distance(items, near)
got = {i["id"]: i.get("distance_km") for i in items}
print(got)
assert got["a"] < 0.5 and got["b"] > 3 and got["c"] is None and got["d"] < 0.05
kept = [i["id"] for i in items if geo.within(i, near)]
assert kept == ["a", "c", "d"], kept
# 網路查詢
class R:
    def json(self): return {"data": {"surrounding": {"lat": "24.9655010", "lng": "121.2373850"}}}
with mock.patch.object(geo.requests, "get", return_value=R()), mock.patch.object(geo.time, "sleep"):
    assert c.community(7546) == (24.965501, 121.237385)
c.save(); assert (tmp / "g.json").exists()
# 多圓心：任一範圍內即可
multi = [near, {"name": "部桃", "lat": 24.977890, "lng": 121.268102, "radius_km": 2}]
x = {"id": "x", "lat": 24.9621721, "lng": 121.2655383}   # 離美麗歐洲 2.86km、離部桃 ~1.75km
y = {"id": "y", "lat": 24.9300, "lng": 121.2000}         # 都不在範圍內
geo.apply_distance([x, y], multi)
assert x["near_name"] == "部桃" and x["in_range"] and geo.within(x, multi), x
assert not y["in_range"] and not geo.within(y, multi), y
assert geo.centers(near) == [near] and geo.centers(None) == []
class N:
    def json(self): return [{"lat": "24.99", "lon": "121.30"}]
with mock.patch.object(geo.requests, "get", return_value=N()), mock.patch.object(geo.time, "sleep"):
    z = {"id": "z", "county": "桃園市", "district": "桃園區", "address": "中山路889號之1"}
    geo.locate([z], c)
    assert z["lat"] == 24.99 and z["geo_src"] == "地址推估" and "addr:桃園市桃園區中山路889號" in c.data, (z, list(c.data))
print("GEO OK")
