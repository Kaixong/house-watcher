import json, re
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    pg.goto("https://community.rakuya.com.tw/12226/sell/info?ehid=0291a3354954004", wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(4000)
    d = pg.content()
    print("rakuya detail coords:", [d[max(0, m.start()-60):m.end()+30].replace("\n", " ") for m in re.finditer(r"2[45]\.\d{4,}", d)][:5])
    print("addr:", re.findall(r"桃園市[^<\"]{2,30}", d)[:5])
    # 住商
    pg2 = ctx.new_page()
    pg2.goto("https://www.hbhousing.com.tw/buyhouse/%E6%A1%83%E5%9C%92%E5%B8%82/320", wait_until="domcontentloaded", timeout=45000); pg2.wait_for_timeout(7000)
    info = pg2.evaluate("""(() => {
      const els = [...document.querySelectorAll('*')].filter(e => e.children.length < 40 && /\\d+(,\\d+)?\\s*萬/.test(e.innerText || '') && /坪/.test(e.innerText || '') && (e.innerText || '').length < 400);
      const top = els.filter(e => !els.some(o => o !== e && e.contains(o)));   // 最內層
      const card = top[0] ? (top[0].closest('a,li,article') || top[0].parentElement) : null;
      return {n: top.length, texts: top.slice(0, 3).map(e => e.innerText.replace(/\\s+/g, ' | ').slice(0, 250)), html: card ? card.outerHTML.slice(0, 2500) : null};
    })()""")
    print("hb:", json.dumps(info, ensure_ascii=False)[:4000])
    nd = pg2.evaluate("(() => { const s = document.getElementById('__NUXT_DATA__'); return s ? s.textContent.length + ' ' + s.textContent.slice(0, 1200) : (window.__NUXT__ ? 'window.__NUXT__' : null) })()")
    print("hb nuxt:", (nd or "")[:1300])
    links = pg2.evaluate("[...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(h => h && /buyhouse|house\\//.test(h)).slice(0, 40)")
    print("hb links:", links)
    b.close()
