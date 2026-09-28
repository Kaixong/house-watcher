"""住商不動產爬蟲（www.hbhousing.com.tw）

列表頁是 Nuxt 伺服器產生，物件資料（含座標、主建坪、車位）放在頁面的 __NUXT_DATA__ 裡。
網址條件：/buyhouse/桃園市/320-324-330-334/1500-down-price/20-down-age/2-page
房數無法用網址篩選，改由程式篩。若出現機器人驗證就停止，不嘗試繞過。
"""
from __future__ import annotations

import json
import random
import re
import time
from urllib.parse import quote

BASE = "https://www.hbhousing.com.tw/buyhouse"
SPECIAL = {"ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef",
           "Set", "Map", "Date", "RegExp", "BigInt", "undefined", "NuxtError", "Error"}


def unflatten(arr: list):
    """解開 Nuxt（devalue）壓縮格式：陣列裡的數字是指向其他元素的索引。"""
    cache: dict[int, object] = {}

    def h(i):
        if not isinstance(i, int) or i < 0 or i >= len(arr):
            return None
        if i in cache:
            return cache[i]
        v = arr[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in SPECIAL:
                t = v[0]
                if t in ("ShallowReactive", "Reactive", "Ref", "ShallowRef"):
                    r = h(v[1]) if len(v) > 1 else None
                elif t == "Date":
                    r = v[1] if len(v) > 1 else None
                elif t == "Set":
                    r = [h(x) for x in v[1:]]
                elif t == "Map":
                    r = {str(h(v[k])): h(v[k + 1]) for k in range(1, len(v) - 1, 2)}
                else:
                    r = None
            else:
                r = []
                cache[i] = r
                r.extend(h(x) for x in v)
                return r
        elif isinstance(v, dict):
            r = {}
            cache[i] = r
            for k, x in v.items():
                r[k] = h(x)
            return r
        else:
            r = v
        cache[i] = r
        return r

    return h(0)


def find_key(obj, key, depth=0):
    if depth > 12:
        return None
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key, depth + 1)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key, depth + 1)
            if r is not None:
                return r
    return None


def _f(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


ZIP_DISTRICT = {"320": "中壢區", "324": "平鎮區", "330": "桃園區", "334": "八德區", "333": "龜山區",
                "326": "楊梅區", "325": "龍潭區", "335": "大溪區", "337": "大園區", "338": "蘆竹區"}


def normalize(o: dict, county: str = "") -> dict | None:
    sn = o.get("sn")
    price = _f(o.get("salePrice") or o.get("price"))
    if not sn or not price:
        return None
    park = str(o.get("parking") or "")
    addr = str(o.get("doorplate") or "")
    zipc = str(o.get("zipCode") or "")
    district = ZIP_DISTRICT.get(zipc) or (re.search(r"[市縣](\S{1,3}?[區鄉鎮市])", addr) or [None, ""])[1]
    ping = _f(o.get("area"))
    kind = str(o.get("style") or o.get("type") or "")
    orig = _f(o.get("originalPrice"))
    return {
        "source": "住商不動產",
        "id": f"hb-{sn}",
        "title": o.get("objName") or "",
        "url": f"https://www.hbhousing.com.tw/detail?sn={sn}",
        "image": o.get("photo1") or "",
        "price": price,
        "prev_price": orig if orig and orig > price else None,
        "unit_price": round(price / ping, 2) if ping else None,
        "ping": ping,
        "main_ping": _f(o.get("mainArea")),
        "layout": f"{o.get('room') or ''}房{o.get('hall') or ''}廳{o.get('bath') or ''}衛",
        "rooms": _f(o.get("room")),
        "age": _f(o.get("age")),
        "floor": f"{o.get('floor') or ''}/{o.get('floorTotal') or ''}樓",
        "kind": kind,
        "community": "",
        "community_id": None,
        "county": county,
        "district": district,
        "address": re.sub(r"^\S{2,3}[市縣]\S{1,3}?[區鄉鎮市]", "", addr).strip("​ "),
        "lat": _f(o.get("lat")),
        "lng": _f(o.get("lon")),
        "tags": [],
        "poster": "住商不動產",
        "detail": {"parking": park, "parking_flat": "平面" in park, "traffic": [], "source": "hb"} if park else None,
    }


def scrape(query: dict, county: str = "桃園市", max_pages: int = 120, headless: bool = True, log=print) -> list[dict]:
    """query: {city: "桃園市", zips: ["320",...], max_price: 1500, max_age: 20, style: "elevator-mansion-style"}"""
    from playwright.sync_api import sync_playwright

    path = [quote(query.get("city", "桃園市")), "-".join(query.get("zips", []))]
    if query.get("max_price"):
        path.append(f"{int(query['max_price'])}-down-price")
    if query.get("max_age"):
        path.append(f"{int(query['max_age'])}-down-age")
    if query.get("style"):
        path.append(query["style"])
    base = BASE + "/" + "/".join(path)
    out: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(locale="zh-TW", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        page.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image", "media", "font") else r.continue_())
        shown = False
        for n in range(1, max_pages + 1):
            url = base if n == 1 else f"{base}/{n}-page"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                raw = page.evaluate("document.getElementById('__NUXT_DATA__')?.textContent || ''")
            except Exception as e:  # noqa: BLE001
                log(f"  ⚠ [住商] 第 {n} 頁失敗：{e.__class__.__name__}")
                break
            if not raw:
                body = page.inner_text("body")[:500]
                if any(k in body for k in ("安全驗證", "Just a moment", "機器人")):
                    log("  ⚠ [住商] 出現機器人驗證，停止讀取")
                break
            data = find_key(unflatten(json.loads(raw)), "buyHouseListDatas") or []
            if not shown and data:
                shown = True
                log("  [住商] 欄位範例：" + json.dumps({k: data[0].get(k) for k in ("style", "type", "parking", "age", "area", "mainArea")}, ensure_ascii=False))
            new = 0
            for o in data:
                it = normalize(o or {}, county)
                if it and it["id"] not in out:
                    out[it["id"]] = it
                    new += 1
            if n % 10 == 1:
                log(f"  [住商] 第 {n} 頁：{new} 筆（累計 {len(out)}）")
            if new == 0:
                break
            time.sleep(random.uniform(2, 3.5))
        browser.close()
    log(f"  [住商] 共 {len(out)} 筆")
    return list(out.values())
