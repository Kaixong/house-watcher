"""測試主建坪數解析、詳情頁解析與詳情條件。結構仿照 591 實際頁面（2026-09）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from playwright.sync_api import sync_playwright
from scraper import sale591
from scraper.filters import passes, passes_detail, needs_detail

raw = {"id": "20897320", "title": "內壢元智商圈3房+車位", "url": "u", "attrs": ["電梯大樓", "3房2廳2衛", "權狀47.78坪", "主建22.79坪", "9年", "6F/12F"],
       "price_text": "1,388", "price_section_text": "1,388萬 29.05萬/坪", "section": "中壢區-", "address": "元化路"}
it = sale591.normalize(raw)
assert it["ping"] == 47.78 and it["main_ping"] == 22.79 and it["age"] == 9 and it["price"] == 1388, it

html = """<div class="detail-house-box"><h3 class="detail-house-name">房屋資料</h3>
<div class="detail-house-item"><div class="detail-house-key">型態</div><div class="detail-house-value">電梯大樓</div></div>
<div class="detail-house-item"><div class="detail-house-key">管理費</div><div class="detail-house-value">2797元/月</div></div>
<div class="detail-house-item"><div class="detail-house-key">車位</div><div class="detail-house-value">10.9坪，平面式，已含售金內</div></div>
<div class="detail-house-item"><div class="detail-house-key">公設比</div><div class="detail-house-value">32%</div></div></div>
<div class="detail-house-box"><h3 class="detail-house-name">坪數 說明</h3>
<div class="detail-house-item"><div class="detail-house-key">主建物</div><div class="detail-house-value">22.79坪</div></div></div>
<div class="detail-house-box"><h3 class="detail-house-name">附近交通</h3>
<div class="detail-house-item"><div class="detail-house-key"></div><div class="detail-house-value">群益幼稚園公車站</div></div>
<div class="detail-house-item"><div class="detail-house-key"></div><div class="detail-house-value">內壢火車站</div></div></div>"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.set_content(html)
    d = sale591.parse_detail(pg.evaluate(sale591.DETAIL_JS)); b.close()
print(d)
assert d["parking_flat"] and d["main_ping"] == 22.79 and d["traffic"] == ["群益幼稚園公車站", "內壢火車站"]

f = {"max_price": 1500, "max_age": 20, "min_main_ping": 20, "parking": "平面", "transit_keywords": ["公車", "捷運", "火車", "客運"]}
assert needs_detail(f) and passes(it, f)
it["detail"] = d
assert passes_detail(it, f) == (True, "")
it["detail"] = dict(d, parking="機械式", parking_flat=False)
assert not passes_detail(it, f)[0]
it["detail"] = dict(d, traffic=["某某國小"])
assert not passes_detail(it, f)[0]
assert not passes(dict(it, main_ping=18.5), f)
del it["detail"]; assert passes_detail(it, f) == (True, "詳情未確認")
print("DETAIL OK")
