import json, re
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    reqs = []
    pg.on("response", lambda r: reqs.append((r.request.resource_type, r.status, r.url)) if r.request.resource_type in ("xhr", "fetch", "document") else None)
    for u in ["https://www.leju.com.tw/", "https://www.leju.com.tw/page_search_result?oid=L&city=H&area=320"]:
        reqs.clear()
        try:
            pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(6000)
        except Exception as e:
            print("ERR", u, e.__class__.__name__); continue
        print("==", u, "→", pg.url, "|", pg.title())
        links = pg.evaluate("[...document.querySelectorAll('a')].map(a => a.textContent.trim().slice(0,12) + ' ' + a.href).filter(s => /leju/.test(s)).slice(0, 80)")
        print("links:", json.dumps(links, ensure_ascii=False)[:3500])
        print("reqs:", [r for r in reqs if "leju" in r[2]][:25])
        print("text:", " ".join(pg.inner_text("body").split())[:600])
    b.close()
