import json, re
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page(); api = []
    pg.on("response", lambda r: api.append(r) if r.request.resource_type in ("xhr", "fetch") and "leju" in r.url and "cdn-cgi" not in r.url else None)
    pg.goto("https://www.leju.com.tw/object_list?city_code=H", wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(8000)
    html = pg.content()
    print("len", len(html), "title", pg.title())
    i = html.find("中壢區買房"); print("around 中壢區買房:", html[max(0, i-400):i+200] if i >= 0 else None)
    print("anchors:", pg.evaluate("[...document.querySelectorAll('a')].length"))
    print("sample anchors:", json.dumps(pg.evaluate("[...document.querySelectorAll('a')].slice(40, 90).map(a => [a.textContent.trim().slice(0,16), a.getAttribute('href')])"), ensure_ascii=False)[:2500])
    m = re.findall(r'href="([^"]*(?:object|house|sale)[^"]*)"', html)[:30]; print("hrefs in html:", m)
    for k in ["__NUXT__", "__NEXT_DATA__", "__INITIAL_STATE__", "window.__data"]:
        print(k, k in html)
    for r in api[:12]:
        try: body = r.text()[:500]
        except Exception: body = "?"
        print("api:", r.status, r.url[:170], "|", body[:500])
    b.close()
