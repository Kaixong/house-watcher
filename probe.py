import json, re, time, requests
from playwright.sync_api import sync_playwright
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}
base = "https://www.rakuya.com.tw/sell-search/api/search-item/count"
for extra in ["", "&age=~20", "&age=0~20", "&type=2", "&usecode=1", "&parking=1", "&feature=parking", "&size=20~"]:
    try:
        r = requests.get(base + "?zipcode=320,324,330,334&price=~1500&room=3~4&model=list" + extra, headers=UA, timeout=20).json()
        print("rakuya count", extra or "(base)", r.get("data", {}).get("count"))
    except Exception as e:
        print("rakuya count", extra, "ERR", e.__class__.__name__)
    time.sleep(1)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent=UA["User-Agent"])
    pg = ctx.new_page()
    pg.goto("https://www.rakuya.com.tw/sell/result?zipcode=320&price=~1500&room=3~4", wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(4000)
    fl = pg.evaluate("""[...document.querySelectorAll('input[name], select[name], [data-key], [data-value], a[href*="sell/result"]')].map(e => (e.name || e.dataset.key || '') + '=' + (e.value || e.dataset.value || e.getAttribute('href') || '') + ' ' + (e.closest('label,li,a')?.innerText || '').trim().slice(0, 10)).filter(s => /age|type|park|size|use|kind|屋齡|車位|類型|坪/.test(s)).slice(0, 60)""")
    print("rakuya filters:", json.dumps(fl, ensure_ascii=False)[:3000])
    pg2 = ctx.new_page()
    pg2.goto("https://www.hbhousing.com.tw/buyhouse/%E6%A1%83%E5%9C%92%E5%B8%82/320/1500-down-price", wait_until="domcontentloaded", timeout=45000); pg2.wait_for_timeout(6000)
    print("hb url:", pg2.url, pg2.title()[:60])
    links = pg2.evaluate("[...document.querySelectorAll('a')].map(a => [a.textContent.trim().slice(0,10), a.getAttribute('href')]).filter(x => x[1] && /price|room|age|style|type|page|tag/.test(x[1]) && x[1].includes('320')).slice(0, 60)")
    print("hb links:", json.dumps(links, ensure_ascii=False)[:3500])
    cnt = pg2.evaluate("(() => { const t = document.body.innerText; const m = t.match(/共找到\\s*[\\d,]+/); return m ? m[0] : null })()"); print("hb count:", cnt)
    b.close()
