"""住商（Nuxt 資料解析）、樂屋網（卡片文字解析）、房數篩選、同名社區座標、樂屋網 591 編號去重。"""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper import hbhousing, rakuya, geo
from scraper.filters import passes
import run

# --- 住商：devalue 格式（取自實際頁面的結構） ---
arr = [["ShallowReactive", 1], {"data": 2}, ["ShallowReactive", 3], {"$f": 4}, {"cnts": 5, "buyHouseListDatas": 6}, 4193, [7],
       {"sn": 8, "objName": 9, "price": 10, "room": 11, "hall": 12, "bath": 12, "area": 13, "style": 14, "doorplate": 15,
        "parking": 16, "floor": 17, "floorTotal": 18, "age": 19, "lon": 20, "lat": 21, "mainArea": 22, "zipCode": 23, "originalPrice": -1},
       "AS144416", "屋齡新兩房平車", 1138, 3, 2, 43.06, "大樓", "桃園市中壢區松仁路​", "坡道平面", 4, 12, 5.8, 121.25, 24.96, 21.5, "320"]
data = hbhousing.find_key(hbhousing.unflatten(arr), "buyHouseListDatas")
it = hbhousing.normalize(data[0], "桃園市")
print(it)
assert it["id"] == "hb-AS144416" and it["price"] == 1138 and it["main_ping"] == 21.5 and it["district"] == "中壢區"
assert it["address"] == "松仁路" and it["lat"] == 24.96 and it["detail"]["parking_flat"] and it["layout"] == "3房2廳2衛"
f = {"rooms": [3, 4], "kinds": ["大樓", "華廈"], "max_age": 20, "min_main_ping": 20}
assert passes(it, f) and not passes(dict(it, layout="2房1廳1衛"), f) and passes(dict(it, kind=""), f)

# --- 樂屋網：卡片文字（取自實際頁面） ---
card = {"ehid": "03415e355218159", "image": "x.jpg", "text": "忠貞市場/南亞商圈稀有電梯3房車 | 新上架 | 中壢區 | 南亞國寶 | 華廈 | 3房2廳2衛 | 26.7年 | 5/7樓 | 總建37.73坪 | 主建19.8坪 | 21.15萬/坪 | 798萬 | 距離美廉社中壢龍昌店 | 約57公尺 | 優質 | 平面車位 | 宜收租"}
r = rakuya.normalize(card, {"object_group_id": "591/S20720641", "object_member_brand": "太平洋房屋"}, "桃園市")
print(r)
assert r["price"] == 798 and r["ping"] == 37.73 and r["main_ping"] == 19.8 and r["age"] == 26.7 and r["unit_price"] == 21.15
assert r["district"] == "中壢區" and r["community"] == "南亞國寶" and r["kind"] == "華廈" and r["same_as"] == "sale-20720641"
assert r["detail"]["parking_flat"] and r["layout"] == "3房2廳2衛"

# --- 同名社區座標 ---
c = geo.GeoCache(Path(tempfile.mkdtemp()) / "g.json", log=lambda *a: None)
a591 = {"id": "sale-20720641", "source": "591中古屋", "community": "南亞國寶", "district": "中壢區", "lat": 24.95, "lng": 121.21, "price": 800, "ping": 37.7, "url": "u"}
geo.locate([a591], c)
r2 = dict(r); geo.locate([r2], c)
assert r2["lat"] == 24.95 and r2["geo_src"] == "同名社區"
assert not geo.within({"id": "z"}, [{"lat": 1, "lng": 1}], strict=True) and geo.within({"id": "z"}, [{"lat": 1, "lng": 1}])

# --- 去重：樂屋網標明 591 編號 → 直接合併，即使價格不同 ---
dup = run.dedupe([dict(r2, price=820), a591])
assert dup == {"rakuya-03415e355218159": "sale-20720641"}, dup
print("SOURCES OK")
