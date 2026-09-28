"""信義資料轉換、住宅類型篩選、跨網站去重。資料格式取自信義 API 實際回應（2026-09）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper import sinyi
from scraper.filters import passes, passes_detail
import run

o = {"houseNo": "7789MV", "name": "獨家｜信義東興三房車位", "latitude": 24.952964, "longitude": 121.233853,
     "image": ["https://res.sinyi.com.tw/buy/7789MV/smallimg/A.JPG"], "commName": "日安天下", "address": "桃園市中壢區廣州路",
     "age": "33.5年", "houselandtype": ["L"], "priceFirst": 1099, "totalPrice": 899, "areaBuilding": 40.84, "pingUsed": 24.11,
     "layout": "3房2廳2衛", "floor": "6", "totalfloor": "12", "isParking": True, "parking": ["2"], "isOff": False}
it = sinyi.normalize(o, "臺北市".replace("臺北", "桃園"))
print(it["district"], it["address"], it["kind"], it["price"], it["prev_price"], it["unit_price"], it["detail"])
assert it["district"] == "中壢區" and it["address"] == "廣州路" and it["kind"] == "大樓"
assert it["price"] == 899 and it["prev_price"] == 1099 and it["age"] == 33.5 and it["detail"]["parking_flat"]
assert it["url"] == "https://www.sinyi.com.tw/buy/house/7789MV"
mech = sinyi.normalize(dict(o, parking=["4"]))
assert mech["detail"]["parking"] == "坡道機械" and not mech["detail"]["parking_flat"]

f = {"kinds": ["大樓", "華廈", "公寓"], "max_age": 40, "parking": "平面", "transit_keywords": ["公車"]}
assert passes(it, f) and not passes(dict(it, kind="店面"), f)
assert passes_detail(it, f) == (True, "來源未提供附近交通，請自行確認")
assert not passes_detail(mech, f)[0]
assert not passes({"kind": "工業用"}, {"kinds": ["住家用", "住商用"]}) and passes({"kind": "住商用"}, {"kinds": ["住家用", "住商用"]})

a = {"id": "sale-1", "source": "591中古屋", "community": "日安天下", "price": 899, "ping": 40.9, "url": "u591", "lat": 24.953, "lng": 121.2338}
b = dict(it)
c = dict(it, id="sinyi-X", community="別的社區", lat=25.0, lng=121.3, url="uX")
dup = run.dedupe([b, a, c])
assert dup == {"sinyi-7789MV": "sale-1"}, dup
assert a["also"][0]["source"] == "信義房屋"
print("SINYI OK")
