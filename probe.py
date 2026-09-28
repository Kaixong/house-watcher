import json, re
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page(); api = []
    pg.on("response", lambda r: api.append(r) if r.request.resource_type in ("xhr", "fetch") and "leju" in r.url and "cdn-cgi" not in r.url else None)
    pg.goto("https://www.leju.com.tw/object_list?city_code=H", wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(6000)
    links = pg.evaluate("[...document.querySelectorAll('a')].map(a => [a.textContent.trim().slice(0,14), a.getAttribute('href')]).filter(x => x[1] && /object_list|object\\//.test(x[1])).slice(0, 60)")
    print("links:", json.dumps(links, ensure_ascii=False)[:2500])
    nd = pg.evaluate("(() => { const s = document.getElementById('__NEXT_DATA__') || document.querySelector('script[type=\"application/json\"]'); return s ? s.textContent.slice(0, 200) : null })()")
    print("nextdata:", nd)
    # 找中壢區
    zl = [l for l in links if "中壢" in (l[0] or "")]
    print("zhongli:", zl)
    target = zl[0][1] if zl else None
    if target:
        api.clear()
        pg.goto("https://www.leju.com.tw" + target if target.startswith("/") else target, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(7000)
        print("== page", pg.url, pg.title())
        txt = " ".join(pg.inner_text("body").split()); print("blocked" if "安全驗證" in txt else "ok", txt[:500])
        # 物件卡片：找含「萬」與「坪」的連結區塊
        card = pg.evaluate("""(() => { const as = [...document.querySelectorAll('a[href*="object"]')].filter(a => /萬/.test(a.textContent) && /坪/.test(a.textContent));
            return {n: as.length, hrefs: as.slice(0,5).map(a => a.getAttribute('href')), html: as[0] ? (as[0].closest('li,article,div') || as[0]).outerHTML.slice(0, 3000) : null} })()""")
        print("cards:", json.dumps(card, ensure_ascii=False)[:4200])
        pag = pg.evaluate("[...document.querySelectorAll('a')].map(a => [a.textContent.trim(), a.getAttribute('href')]).filter(x => /^(\\d+|下一頁|›|»|>)$/.test(x[0]) && x[1]).slice(0, 10)")
        print("pagination:", pag)
        for r in api[:10]:
            try: body = r.text()[:600]
            except Exception: body = "?"
            print("api:", r.status, r.url[:160], "|", body.replace("\\n", " ")[:600])
    b.close()
