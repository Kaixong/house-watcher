import json, re, requests
from playwright.sync_api import sync_playwright
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"}
for cid in [7546, 6611106]:
    r = requests.get(f"https://bff-market.591.com.tw/v3/web/community/info?id={cid}", headers=UA, timeout=20).json()
    s = (r.get("data") or {}).get("surrounding") or {}
    print("community", cid, s.get("community_name"), s.get("lat"), s.get("lng"), s.get("address"))
import sys
ids = sys.argv[1:] if len(sys.argv) > 1 else []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for id_ in ["20897320"] + ids:
        pg.goto(f"https://sale.591.com.tw/home/house/detail/2/{id_}.html", wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(5000)
        html = pg.content()
        hits = re.findall(r'.{0,40}(?:lat|lng|latitude|longitude|center=|q=2[45]\.\d+)[^<]{0,60}', html)[:8]
        print("detail", id_, [h.replace("\n", " ") for h in hits])
        nuxt = pg.evaluate("() => { try { const s = JSON.stringify(window.__NUXT__ || {}); const m = s.match(/.{0,60}(lat|lng)[^,]{0,40}/g); return m ? m.slice(0,6) : null } catch(e) { return String(e) } }")
        print("  nuxt", nuxt)
    b.close()
