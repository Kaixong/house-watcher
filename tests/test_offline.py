import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from playwright.sync_api import sync_playwright
from scraper import sale591, newhouse591
from scraper.filters import passes

html = (Path(__file__).parent / "fixture_sale.html").read_text("utf-8")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.set_content(html)
    raws = pg.evaluate(sale591.EXTRACT_JS); b.close()
items = [sale591.normalize(r) for r in raws]
for it in items: print(json.dumps(it, ensure_ascii=False))
a, c = items
assert a["price"] == 1748 and a["unit_price"] == 141.54 and a["ping"] == 12.35 and a["age"] == 0
assert a["layout"] == "2房1廳1衛" and a["floor"] == "4F/5F" and a["district"] == "內湖區" and a["kind"] == "電梯大樓"
assert a["url"] == "https://sale.591.com.tw/home/house/detail/2/20745087.html"
assert c["age"] == 35.2 and c["price"] == 2580
f = {"max_price": 3000, "min_ping": 20, "max_age": 30, "exclude_keywords": ["頂加"]}
assert not passes(a, f)  # 坪數太小
assert not passes(c, f)  # 屋齡太大 + 頂加
assert passes(c, {"max_price": 3000})
b="https://sale.591.com.tw/?shType=list&regionid=1&section=3,10&price=1000$_3000$"
assert sale591.page_url(b,1)==b
assert sale591.page_url(b,3)=="https://sale.591.com.tw/?shType=list&regionid=1&section=3,10&price=1000$_3000$&firstRow=60", sale591.page_url(b,3)

nh = {"hid":138145,"build_name":"春風大院","section":"中山區","address":"台北市中山區遼寧街","cover":"x.jpg","tag":["近捷運"],"purpose_str":"住家用","area":"16~59坪","room":"二房(16~23坪)","price":"價格待定","price_unit":"","shop_name":"南京復興","ad_type":2}
n = newhouse591.normalize(nh); print(n)
assert n["unit_price"] is None and passes(n, {"max_unit_price": 100})
assert newhouse591.parse_unit_price("85~95", "萬/坪") == (85, 95)
assert newhouse591.parse_unit_price("3,000", "萬/戶") == (None, None)
print("ALL OK")
