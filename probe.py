from playwright.sync_api import sync_playwright
urls = ["https://sale.591.com.tw/home/house/detail/2/20683233.html", "https://sale.591.com.tw/home/house/detail/2/20634161.html",
        "https://sale.591.com.tw/home/house/detail/2/20946666.html", "https://newhouse.591.com.tw/135214", "https://newhouse.591.com.tw/132898",
        "https://newhouse.591.com.tw/home/housing/detail?hid=135214"]
with sync_playwright() as p:
    b = p.chromium.launch()
    for dev in [None, "iPhone 13"]:
        ctx = b.new_context(**(p.devices[dev] if dev else {}), locale="zh-TW"); pg = ctx.new_page()
        for u in urls:
            try:
                pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(5000)
                bad = any(k in pg.inner_text("body") for k in ["不存在", "無此物件", "已關閉", "找不到"])
                print(dev or "desktop", "|", u, "→", pg.url, "|", pg.title()[:35], "| 問題頁" if bad else "| OK")
            except Exception as e:
                print(dev or "desktop", "|", u, "ERR", e.__class__.__name__)
        ctx.close()
    b.close()
