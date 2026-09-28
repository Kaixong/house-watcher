from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    for dev in ["iPhone 13", None]:
        ctx = b.new_context(**(p.devices[dev] if dev else {}), locale="zh-TW")
        pg = ctx.new_page()
        for id_ in ["20897320", "20945964"]:
            u = f"https://sale.591.com.tw/home/house/detail/2/{id_}.html"
            pg.goto(u, wait_until="networkidle", timeout=45000); pg.wait_for_timeout(2500)
            txt = " ".join(pg.inner_text("body").split())[:160]
            print(dev or "desktop", id_, "|", pg.url, "|", pg.title()[:40], "|", txt)
        ctx.close()
    b.close()
