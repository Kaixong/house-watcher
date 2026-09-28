import json, time, requests
from playwright.sync_api import sync_playwright
for q in ["中壢車站", "中壢火車站", "日月光半導體 中壢", "日月光 中壢廠", "ASE Chung-Li"]:
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "json", "limit": 3, "countrycodes": "tw"},
                     headers={"User-Agent": "house-watcher/1.0 (personal)"}, timeout=20).json()
    print("geo", q, [(x["display_name"][:70], x["lat"], x["lon"]) for x in r]); time.sleep(1.2)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    for name, u in [("rakuya", "https://www.rakuya.com.tw/sell/result?zipcode=320&price=~1500&room=3~4"),
                    ("hbhousing", "https://www.hbhousing.com.tw/buyhouse/%E6%A1%83%E5%9C%92%E5%B8%82/%E4%B8%AD%E5%A3%A2%E5%8D%80")]:
        pg = ctx.new_page(); api = []
        pg.on("response", lambda r: api.append(r) if r.request.resource_type in ("xhr", "fetch", "document") and not any(k in r.url for k in ["google", "facebook", "insider", "hinet", "cdn-cgi", "doubleclick", "tagging"]) else None)
        pg.goto(u, wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(8000)
        txt = " ".join(pg.inner_text("body").split())
        print("==", name, pg.url[:150], "|", pg.title()[:50], "| blocked" if "安全驗證" in txt else "| ok")
        for r in api[:40]:
            try:
                ct = r.headers.get("content-type", "")
                body = r.text()[:900] if ("json" in ct) else ""
            except Exception: body = ""
            if body or r.request.resource_type != "document":
                print("  ", r.request.method, r.status, r.url[:200], "|", (r.request.post_data or "")[:300], "|", body.replace("\n", " ")[:900])
        cards = pg.evaluate("""(() => { const as = [...document.querySelectorAll('a')].filter(a => /萬/.test(a.innerText) && /坪/.test(a.innerText) && a.innerText.length < 500);
          return {n: as.length, sample: as.slice(0, 3).map(a => [a.getAttribute('href'), a.innerText.replace(/\\s+/g, ' | ').slice(0, 260)])} })()""")
        print("  cards:", json.dumps(cards, ensure_ascii=False)[:1500])
        nuxt = pg.evaluate("(() => { for (const k of ['__NUXT__', '__NEXT_DATA__', '__INITIAL_STATE__']) if (window[k]) return k; const s = document.getElementById('__NUXT_DATA__') || document.getElementById('__NEXT_DATA__'); return s ? s.id + ':' + s.textContent.length : null })()")
        print("  state:", nuxt)
        pg.close()
    b.close()
