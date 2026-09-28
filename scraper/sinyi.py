"""信義房屋爬蟲（www.sinyi.com.tw）

信義的列表頁背後有 JSON API（sinyiwebapi.sinyi.com.tw/filterObject.php）。
這支 API 需要網站發給瀏覽器的 session 標頭，所以先用 Playwright 正常打開一次列表頁，
沿用它的標頭，再用同一個頁面呼叫 API 翻頁。若網站出現機器人驗證就停止，不嘗試繞過。
"""
from __future__ import annotations

import json
import random
import re
import time

BASE = "https://www.sinyi.com.tw/buy/list/Taoyuan-city/320-zip/index"
API = "https://sinyiwebapi.sinyi.com.tw/filterObject.php"

TYPE_NAME = {"L": "大樓", "M": "華廈", "A": "公寓", "T": "透天厝", "V": "別墅", "C": "套房",
             "S": "店面", "O": "辦公", "F": "廠房", "G": "土地"}
PARK_NAME = {"2": "坡道平面", "4": "坡道機械", "8": "塔式"}
FLAT_CODES = {"2"}


def _num(s):
    m = re.search(r"[\d.]+", str(s or ""))
    return float(m.group()) if m else None


def normalize(o: dict, county: str = "") -> dict:
    types = o.get("houselandtype") or []
    parks = [str(x) for x in (o.get("parking") or [])]
    park_txt = "、".join(PARK_NAME.get(p, f"車位（代碼{p}）") for p in parks) if o.get("isParking") else ""
    ping = o.get("areaBuilding")
    price = o.get("totalPrice")
    district = ""
    m = re.match(r"^\S{2,3}[市縣](\S{1,3}?[區鄉鎮市])", o.get("address") or "")
    if m:
        district = m.group(1)
    hn = o["houseNo"]
    return {
        "source": "信義房屋",
        "id": f"sinyi-{hn}",
        "title": o.get("name", ""),
        "url": f"https://www.sinyi.com.tw/buy/house/{hn}",
        "image": (o.get("image") or [""])[0],
        "price": float(price) if price else None,
        "prev_price": float(o["priceFirst"]) if o.get("priceFirst") and price and o["priceFirst"] > price else None,
        "unit_price": round(price / ping, 2) if price and ping else None,
        "ping": ping,
        "main_ping": o.get("pingUsed"),  # 信義提供的是「主建物＋陽台」
        "main_ping_note": "主建＋陽台",
        "layout": o.get("layout") or o.get("totalLayout") or "",
        "age": _num(o.get("age")),
        "floor": f"{o.get('floor', '')}F/{o.get('totalfloor', '')}F",
        "kind": "、".join(TYPE_NAME.get(t, t) for t in types),
        "community": o.get("commName") or "",
        "community_id": None,
        "county": county,
        "district": district,
        "address": re.sub(r"^\S{2,3}[市縣]\S{1,3}?[區鄉鎮市]", "", o.get("address") or ""),
        "lat": o.get("latitude"),
        "lng": o.get("longitude"),
        "tags": [],
        "poster": "信義房屋",
        # 列表就有的車位資訊，直接當作「詳情」使用
        "detail": {"parking": park_txt, "parking_flat": any(p in FLAT_CODES for p in parks),
                   "main_ping": o.get("pingUsed"), "traffic": [], "source": "sinyi"},
    }


def scrape(query: dict, county: str = "", max_pages: int = 20, headless: bool = True, log=print) -> list[dict]:
    """query: {zips: [...], price: "0-1500", rooms: "3-4", types: ["L","M","A"]}"""
    from playwright.sync_api import sync_playwright

    out: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(locale="zh-TW", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        first = []
        page.on("request", lambda r: first.append(r) if "filterObject" in r.url else None)
        page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)
        body_txt = page.inner_text("body")[:2000]
        if not first or any(k in body_txt for k in ("安全驗證", "Just a moment", "機器人")):
            log("  ⚠ [信義] 無法取得列表（可能出現機器人驗證），本次略過")
            browser.close()
            return []
        req = first[0]
        hdr = {k: v for k, v in req.headers.items() if k.lower() in ("sat", "sid", "code", "content-type")}
        body = json.loads(req.post_data)
        f = dict(body.get("filter") or {})
        f["retRange"] = [str(z) for z in query.get("zips", [])]
        if query.get("types"):
            f["houselandtype"] = list(query["types"])
        if query.get("price"):
            f["price"] = {"priceType": 2, "priceRange": [str(query["price"])]}
        if query.get("rooms"):
            f["room"] = {"isRoofPlus": True, "roomRange": [str(query["rooms"])]}
        body["filter"] = f
        body["pageCnt"] = 50
        total = None
        for n in range(1, max_pages + 1):
            body["page"] = n
            try:
                res = page.evaluate(
                    """async ([u, h, b]) => { const r = await fetch(u, {method: 'POST', headers: h, body: JSON.stringify(b)});
                       return await r.json(); }""", [API, hdr, body])
            except Exception as e:  # noqa: BLE001
                log(f"  ⚠ [信義] 第 {n} 頁失敗：{e.__class__.__name__}")
                break
            c = (res or {}).get("content") or {}
            objs = c.get("object") or []
            total = c.get("totalCnt", total)
            for o in objs:
                if o.get("houseNo") and not o.get("isOff"):
                    out[o["houseNo"]] = normalize(o, county)
            log(f"  [信義] 第 {n} 頁：{len(objs)} 筆（共 {total} 筆）")
            if not objs or len(out) >= (total or 0):
                break
            time.sleep(random.uniform(1.5, 3))
        browser.close()
    return list(out.values())
