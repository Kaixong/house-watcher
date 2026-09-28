import json
from playwright.sync_api import sync_playwright
urls = ["https://www.sinyi.com.tw/buy/list/0-1500-price/Taoyuan-city/320-zip/330-zip/334-zip/index",
        "https://www.sinyi.com.tw/buy/list/0-1500-price/dalou-huaxia-type/3-4-roomtotal/Taoyuan-city/320-zip/330-zip/334-zip/index"]
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    for u in urls:
        pg = ctx.new_page(); got = []
        pg.on("request", lambda r: got.append(r) if "filterObject" in r.url else None)
        pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(6000)
        print("==", pg.url[:160], "|", pg.title())
        for r in got[:1]:
            body = json.loads(r.post_data); print("filter:", json.dumps(body["filter"], ensure_ascii=False), "page", body["page"], "pageCnt", body["pageCnt"])
            resp = r.response().json(); c = resp["content"]; print("total:", c["totalCnt"], "first:", [(o["name"], o["totalPrice"], o["layout"], o["age"], o["houselandtype"], o["parking"]) for o in c["object"][:4]])
        # 類型/房數篩選的連結文字
        opts = pg.evaluate("[...document.querySelectorAll('a[href*=\"-type\"], a[href*=\"room\"], a[href*=\"-age\"]')].map(a => [a.textContent.trim().slice(0,10), a.getAttribute('href')]).slice(0, 40)")
        print("opts:", json.dumps(opts, ensure_ascii=False)[:2500])
        pg.close()
    b.close()
