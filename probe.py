import json, re, collections
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    u = "https://www.leju.com.tw/object_list?city_code=H&post_codes=320,330,334&page=2"
    pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(7000)
    print("url", pg.url, pg.title())
    html = pg.content()
    pats = collections.Counter(re.sub(r"[0-9a-zA-Z]{6,}", "<ID>", h) for h in re.findall(r'href="(/[^"?#]+)"', html)); print("href patterns:", pats.most_common(15))
    info = pg.evaluate("""(() => {
      const as = [...document.querySelectorAll('a')].filter(a => /萬/.test(a.textContent) && /坪/.test(a.textContent) && a.textContent.length < 600);
      const box = as[0] ? as[0] : null;
      return {n: as.length, sampleHref: as.slice(0, 4).map(a => a.getAttribute('href')), text: as.slice(0, 3).map(a => a.innerText.replace(/\\s+/g, ' | ').slice(0, 300)), html: box ? box.outerHTML.slice(0, 3500) : null};
    })()""")
    print(json.dumps(info, ensure_ascii=False)[:6000])
    nd = pg.evaluate("(() => { const s = document.getElementById('__NUXT_DATA__'); return s ? s.textContent.length + ' ' + s.textContent.slice(0, 1500) : 'no __NUXT_DATA__' })()")
    print("nuxtdata:", nd[:1600])
    txt = " ".join(pg.inner_text("body").split()); i = txt.find("戶"); print("count text:", re.findall(r"共\\s*[\\d,]+\\s*[筆戶]|[\\d,]+\\s*筆物件|[\\d,]+戶", txt)[:5])
    b.close()
