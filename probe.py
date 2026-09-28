import json, collections
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    pg = ctx.new_page(); got = []
    pg.on("request", lambda r: got.append(r) if "filterObject" in r.url else None)
    pg.goto("https://www.sinyi.com.tw/buy/list/0-1500-price/3-4-roomtotal/Taoyuan-city/320-zip/index", wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(6000)
    r = got[0]; hdr = {k: v for k, v in r.headers.items() if k.lower() in ("sat", "sid", "code", "content-type")}; body = json.loads(r.post_data)
    # DOM：卡片文字 ↔ houseNo（找車位字樣與類型字樣）
    cards = pg.evaluate("[...document.querySelectorAll('a[href*=\"/buy/house/\"]')].filter(a => a.href.includes('breadcrumb=list')).map(a => [a.getAttribute('href').split('/')[3].split('?')[0], a.innerText.replace(/\\s+/g,' ')])")
    objs = {o["houseNo"]: o for o in r.response().json()["content"]["object"]}
    import re
    pmap, tmap = collections.defaultdict(set), collections.defaultdict(set)
    for hn, t in cards:
        o = objs.get(hn)
        if not o: continue
        m = re.findall(r"(坡道平面|坡道機械|升降平面|升降機械|塔式|一樓平面|機械|平面)[^ ]*車位", t)
        pmap[str(o.get("parking"))].update(m)
        m2 = re.findall(r"年(大樓|華廈|公寓|透天|別墅|套房|店面|辦公|廠房)", t)
        tmap[str(o.get("houselandtype"))].update(m2)
    print("parking codes:", {k: sorted(v) for k, v in pmap.items()})
    print("type codes:", {k: sorted(v) for k, v in tmap.items()})
    # 直接呼叫 API：三區、大樓華廈公寓、1500 萬內、3-4 房、每頁 50
    body2 = dict(body); body2["filter"] = dict(body["filter"], retRange=["320", "330", "334"], houselandtype=["L", "M", "A"], price={"priceType": 2, "priceRange": ["0-1500"]}, room={"isRoofPlus": True, "roomRange": ["3-4"]})
    body2["pageCnt"] = 50; body2["page"] = 1
    res = pg.evaluate("async ([h, b]) => { const r = await fetch('https://sinyiwebapi.sinyi.com.tw/filterObject.php', {method: 'POST', headers: h, body: JSON.stringify(b)}); return await r.json(); }", [hdr, body2])
    c = res.get("content") or {}
    print("direct api:", res.get("retCode"), res.get("retMsg"), "total", c.get("totalCnt"), "n", len(c.get("object") or []))
    print("zips:", collections.Counter(o["zipCode"] for o in c.get("object") or []), "types:", collections.Counter(tuple(o["houselandtype"]) for o in c.get("object") or []))
    print("sample:", json.dumps((c.get("object") or [{}])[0], ensure_ascii=False)[:1200])
    b.close()
