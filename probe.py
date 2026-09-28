import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page(); api = []
    pg.on("request", lambda r: api.append(r) if "sinyiwebapi" in r.url else None)
    u = "https://www.sinyi.com.tw/buy/list/Taoyuan-city/320-zip/default-desc/index"
    pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(7000)
    print("title", pg.title())
    for r in api:
        if any(k in r.url for k in ["appSetup", "getSession", "getADInfo", "alive", "setABTesting", "getCommonData", "getRecommendType"]): continue
        resp = r.response()
        try: body = resp.text()[:1500] if resp else ""
        except Exception: body = "?"
        print("API", r.method, r.url, "| post:", (r.post_data or "")[:600], "| hdr:", {k: v for k, v in r.headers.items() if k.lower() in ("sat", "sid", "code", "content-type", "x-api-key", "authorization")})
        print("   resp:", body.replace("\n", " ")[:1500])
    # 篩選網址格式：點幾個篩選看網址
    links = pg.evaluate("[...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(h => h && h.startsWith('/buy/') ).slice(0, 40)")
    print("links:", links)
    card = pg.evaluate("(() => { const a = [...document.querySelectorAll('a[href*=\"/buy/house/\"]')]; return {n: a.length, hrefs: a.slice(0,3).map(x => x.getAttribute('href')), text: a[0] ? a[0].innerText.replace(/\\s+/g, ' | ').slice(0, 400) : null} })()")
    print("card:", json.dumps(card, ensure_ascii=False))
    b.close()
