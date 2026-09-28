import json, re
from playwright.sync_api import sync_playwright
B = "https://www.hbhousing.com.tw/buyhouse/桃園市/320-324-330-334/1500-down-price"
variants = ["", "/3-4-room", "/3-room-4-room", "/20-down-age", "/0-20-age", "/elevator-mansion-style", "/3-4-room/20-down-age/elevator-mansion-style", "?page=2", "/2-page"]
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    for v in variants:
        try:
            pg.goto(B + v, wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(3500)
            t = pg.inner_text("body"); m = re.search(r"共找到\s*([\d,]+)", t)
            first = pg.evaluate("[...document.querySelectorAll('a[href^=\"/detail?sn=\"]')].slice(0,2).map(a => a.textContent.trim().slice(0,14))")
            zips = re.findall(r"桃園市(中壢區|平鎮區|桃園區|八德區)", t)
            print(f"{v or '(base)':45} | {pg.title()[:34]} | count {m.group(1) if m else '?'} | first {first} | zips {sorted(set(zips))}")
        except Exception as e:
            print(v, "ERR", e.__class__.__name__)
    b.close()
