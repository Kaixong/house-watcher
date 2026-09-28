import json, re
from playwright.sync_api import sync_playwright
def safe_post(r):
    try: return (r.request.post_data or "")[:300]
    except Exception: return "<binary>"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    # 樂屋網：多區 + 第 2 頁
    pg.goto("https://www.rakuya.com.tw/sell/result?zipcode=320,330&price=~1500&room=3~4&page=2", wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(5000)
    cards = pg.evaluate("[...document.querySelectorAll('a[href*=\"sell/info?ehid=\"], a[href*=\"sell_item/info?ehid=\"]')].map(a => a.innerText.replace(/\\s+/g,' | ')).filter(t => /萬/.test(t))")
    print("rakuya multi-zip p2:", len(cards), [c[:60] for c in cards[:4]])
    print("district counts:", {d: sum(1 for c in cards if d in c) for d in ["中壢區", "桃園區"]})
    html = pg.content(); print("gtm json in html:", "object_group_id" in html, "item_list" in html)
    # 卡片 DOM 結構
    one = pg.evaluate("(() => { const a = document.querySelector('a[href*=\"sell/info?ehid=\"]'); const li = a && (a.closest('section,li,article') || a.parentElement); return li ? li.outerHTML.slice(0, 2500) : null })()")
    print("card html:", one)
    # 詳情頁座標
    href = pg.evaluate("document.querySelector('a[href*=\"sell/info?ehid=\"]')?.href")
    pg.goto(href, wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(4000)
    d = pg.content(); print("detail:", pg.url[:120], re.findall(r'.{0,30}(?:lat|lng|latitude|longitude)["\']?\s*[:=]\s*["\']?2[45]\.\d+.{0,40}', d)[:4])
    txt = " ".join(pg.inner_text("body").split()); i = txt.find("車位"); print("detail 車位:", txt[max(0,i-60):i+80])
    # 住商
    api = []
    pg2 = ctx.new_page()
    pg2.on("response", lambda r: api.append(r) if r.request.resource_type in ("xhr", "fetch") and "hbhousing" in r.url else None)
    pg2.goto("https://www.hbhousing.com.tw/buyhouse/%E6%A1%83%E5%9C%92%E5%B8%82/320", wait_until="domcontentloaded", timeout=45000); pg2.wait_for_timeout(7000)
    print("hb:", pg2.url[:150], pg2.title()[:60])
    for r in api[:15]:
        try: body = r.text()[:700]
        except Exception: body = ""
        print("  hb api:", r.request.method, r.status, r.url[:180], "|", safe_post(r), "|", body.replace("\n", " ")[:700])
    cards = pg2.evaluate("[...document.querySelectorAll('a')].filter(a => /萬/.test(a.innerText) && /坪/.test(a.innerText) && a.innerText.length < 500).slice(0,3).map(a => [a.getAttribute('href'), a.innerText.replace(/\\s+/g,' | ').slice(0,250)])")
    print("  hb cards:", json.dumps(cards, ensure_ascii=False)[:1500])
    links = pg2.evaluate("[...document.querySelectorAll('a')].map(a => [a.textContent.trim().slice(0,8), a.getAttribute('href')]).filter(x => x[1] && /buyhouse/.test(x[1]) && /中壢|平鎮|八德|桃園區/.test(x[0])).slice(0,8)")
    print("  hb district links:", links)
    b.close()
