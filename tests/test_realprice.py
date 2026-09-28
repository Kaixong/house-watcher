"""用仿真的實價登錄 CSV 與 591 社區回應測試行情模組。"""
import io, json, sys, tempfile, zipfile
from datetime import date
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper import realprice as rp

HDR = "鄉鎮市區,交易標的,土地位置建物門牌,土地移轉總面積平方公尺,都市土地使用分區,非都市土地使用分區,非都市土地使用編定,交易年月日,交易筆棟數,移轉層次,總樓層數,建物型態,主要用途,主要建材,建築完成年月,建物移轉總面積平方公尺,建物現況格局-房,建物現況格局-廳,建物現況格局-衛,建物現況格局-隔間,有無管理組織,總價元,單價元平方公尺,車位類別,車位移轉總面積平方公尺,車位總價元,備註,編號,主建物面積,附屬建物面積,陽台面積,電梯,移轉編號"
ENG = "The villages and towns urban district," + ",".join(["x"] * 32)
def row(dist, addr, ymd, typ, area_m2, total, park_a=0, park_p=0, note="", built="1000101"):
    return ",".join([dist, "房地(土地+建物)", addr, "20", "住", "", "", ymd, "土地1建物1車位0", "五層", "十二層",
        typ, "住家用", "鋼筋混凝土造", built, str(area_m2), "3", "2", "2", "有", "有", str(total), "0",
        "坡道平面" if park_p else "", str(park_a), str(park_p), note, "RPX", str(area_m2 * 0.6), "0", "8", "有", ""])
rows = [HDR, ENG]
# 成功路四段 電梯大樓 ~30坪（99m2）8 筆，單價約 85~95 萬/坪
for i, (ymd, total) in enumerate([("1150110", 2650e4), ("1150220", 2700e4), ("1150315", 2750e4), ("1141105", 2600e4),
                                  ("1140820", 2550e4), ("1150405", 2800e4), ("1150518", 2850e4), ("1140610", 2500e4)]):
    rows.append(row("內湖區", f"臺北市內湖區成功路四段{i+1}~30號", ymd, "住宅大樓(11層含以上有電梯)", 99.2, int(total)))
rows.append(row("內湖區", "臺北市內湖區成功路四段9號", "1150301", "住宅大樓(11層含以上有電梯)", 99.2, 1000e4, note="親友間交易"))  # 排除
rows.append(row("內湖區", "臺北市內湖區成功路四段9號", "1150301", "公寓(5樓含以下無電梯)", 99.2, 1800e4))            # 型態不符
rows.append(row("內湖區", "臺北市內湖區成功路四段9號", "1150301", "住宅大樓(11層含以上有電梯)", 330, 9000e4))        # 坪數不符
rows.append(row("內湖區", "臺北市內湖區瑞光路1號", "1150301", "住宅大樓(11層含以上有電梯)", 132, 4000e4, 33, 300e4)) # 含車位
csv_text = "\n".join(rows)

tmp = Path(tempfile.mkdtemp())
(tmp / "lvr").mkdir()
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("a_lvr_land_a.csv", ("﻿" + csv_text).encode("utf-8"))
    z.writestr("pad.bin", b"0" * 1_100_000)
(tmp / "lvr" / "115S2.zip").write_bytes(buf.getvalue())

lvr = rp.LvrData(tmp / "lvr", seasons=1, log=lambda *a: None)
lvr._zips = [tmp / "lvr" / "115S2.zip"]
data = lvr.rows("台北市")
assert len(data) == 11, len(data)  # 親友交易被排除
park = [d for d in data if d["road"] == "瑞光路"][0]
assert abs(park["unit"] - (3700 / (99 / rp.PING))) < 0.2, park  # 扣除車位價與面積
item = {"source": "591中古屋", "district": "內湖區", "address": "成功路四段", "kind": "電梯大樓", "ping": 30.4, "age": 15,
        "unit_price": 95.0, "county": "臺北市"}
scope, hit = rp.find_nearby(item, data)
assert scope == "內湖區成功路四段" and len(hit) == 8, (scope, len(hit))
s = rp.summarize(hit, date(2026, 9, 28))
print("附近:", scope, s["n"], s["median_12m"], s["trend"])
assert s["trend"][0][0] == "2025Q2" and s["n_12m"] == 6

sample = {"status": 1, "data": {"total_page": 1, "items": [
    {"trans_date": "2026-04-27", "unit_price": {"price": "93.1"}, "total_price_v": "6,988", "build_area_v": {"area": "90.4"},
     "building_area": {"area": "69.9"}, "layout_v2": "3房2廳", "shift_floor": "10樓", "total_floor": "15樓", "address": "中山北路一段101號", "park_type_str": "平面車位", "is_special": 0},
    {"trans_date": "2025-09-24", "unit_price": {"price": "77.5"}, "total_price_v": "6,950", "build_area_v": {"area": "89.6"},
     "building_area": {"area": "89.6"}, "layout_v2": "3房2廳", "shift_floor": "10樓", "total_floor": "15樓", "address": "中山北路一段101號", "is_special": 0},
    {"trans_date": "2025-11-01", "unit_price": {"price": "40"}, "is_special": 1}]}}
class R:
    def json(self): return sample
with mock.patch.object(rp.requests, "get", return_value=R()), mock.patch.object(rp.time, "sleep"):
    deals = rp.fetch_community_deals(5374, log=lambda *a: None)
    assert len(deals) == 2 and deals[0]["unit"] == 93.1 and deals[0]["total"] == 6988
    it2 = dict(item, community_id=5374, community="紀汎希")
    rp.LvrData.rows = lambda self, c: data
    rp.enrich([it2], {"seasons": 1}, tmp, log=print)
m = it2["market"]
print("社區:", m["community"]["median_all"], "附近:", m["nearby"]["median_12m"], "溢價:", m.get("premium"), m.get("premium_ref"))
assert m["community"]["n"] == 2 and m["premium_ref"] == "nearby" and m["premium"] > 0 and m["ref_label"] == "附近近一年"
print("REALPRICE OK")
