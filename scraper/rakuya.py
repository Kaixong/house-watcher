"""樂屋網爬蟲（www.rakuya.com.tw）

列表頁由伺服器產生，用 Playwright 開頁、從 section.search-obj 卡片讀文字。
樂屋網會彙整其他網站的物件：頁面的追蹤資料裡帶有「591/S20720641」這類來源編號，
藉此可以和 591 的物件精準去重。樂屋網列表沒有座標，座標另外推估。
若出現機器人驗證就停止，不嘗試繞過。
"""
from __future__ import annotations

import json
import random
import re
import time
from urllib.parse import urlencode

LIST = "https://www.rakuya.com.tw/sell/result"

CARD_JS = r"""
() => [...document.querySelectorAll('section.search-obj[data-ehid]')].map(s => {
  const a = s.querySelector('a[href*="ehid="]');
  const img = s.querySelector('img');
  return {ehid: s.dataset.ehid, href: a ? a.href : '', text: s.innerText.replace(/\s+/g, ' | '),
          image: img ? (img.getAttribute('data-src') || img.src || '') : ''};
})
"""


def _f(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize(card: dict, meta: dict | None, county: str = "") -> dict | None:
    t = card.get("text", "")
    parts = [p.strip() for p in t.split("|") if p.strip()]
    price = re.search(r"([\d,]+(?:\.\d+)?)\s*萬(?!/)", t)
    if not price:
        return None
    district = next((p for p in parts if re.fullmatch(r"\S{1,3}[區鄉鎮市]", p)), "")
    kinds = ("電梯大廈", "華廈", "公寓", "透天厝", "別墅", "套房", "店面", "辦公", "廠房", "樓中樓")
    kind = next((p for p in parts if p in kinds), "")
    community = ""
    if district and district in parts:
        i = parts.index(district)
        if i + 1 < len(parts) and parts[i + 1] not in kinds:
            community = parts[i + 1]
    park = ""
    m = re.search(r"(坡道平面|平面|機械|升降)車位", t)
    if m:
        park = m.group(0)
    meta = meta or {}
    group = str(meta.get("object_group_id") or "")
    same_as = None
    g = re.match(r"591/S(\d+)", group)
    if g:
        same_as = f"sale-{g.group(1)}"
    ehid = card["ehid"]
    return {
        "source": "樂屋網",
        "id": f"rakuya-{ehid}",
        "title": parts[0] if parts else "",
        "url": f"https://www.rakuya.com.tw/sell_item/info?ehid={ehid}",
        "image": card.get("image", ""),
        "price": _f(price.group(1)),
        "unit_price": _f((re.search(r"([\d.]+)\s*萬/坪", t) or [None, None])[1]),
        "ping": _f((re.search(r"總建\s*([\d.]+)\s*坪", t) or [None, None])[1]),
        "main_ping": _f((re.search(r"主建\s*([\d.]+)\s*坪", t) or [None, None])[1]),
        "layout": next((p for p in parts if re.fullmatch(r"\d+房(\d+廳)?(\d+衛)?", p)), ""),
        "age": _f(next((p[:-1] for p in parts if re.fullmatch(r"[\d.]+年", p)), None)),
        "floor": next((p for p in parts if re.fullmatch(r"[\dB\-]+/\d+樓", p)), ""),
        "kind": kind.replace("電梯大廈", "電梯大樓"),
        "community": community,
        "community_id": None,
        "county": county,
        "district": district,
        "address": community,
        "tags": [p for p in ("平面車位", "景觀宅", "近捷運") if p in t],
        "poster": meta.get("object_member_brand") or meta.get("item_brand") or "樂屋網",
        "same_as": same_as,
        "detail": {"parking": park, "parking_flat": "平面" in park, "traffic": [], "source": "rakuya"} if park else None,
    }


def scrape(query: dict, county: str = "", max_pages: int = 45, headless: bool = True, log=print) -> list[dict]:
    """query: {zipcode: "320,324,330,334", price: "~1500", room: "3~4", age: "0~20"}"""
    from playwright.sync_api import sync_playwright

    params = {k: v for k, v in query.items() if v}
    out: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(locale="zh-TW", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        metas: dict[str, dict] = {}

        def on_resp(r):
            if "item-data-layer/imprs" in r.url:
                try:
                    for layer in r.json().get("dataLayers") or []:
                        for it in ((layer or {}).get("ecommercelist") or {}).get("items") or []:
                            metas[it.get("item_id")] = it
                except Exception:  # noqa: BLE001
                    pass
        page.on("response", on_resp)

        for n in range(1, max_pages + 1):
            url = f"{LIST}?{urlencode(dict(params, page=n), safe='~,')}"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_selector("section.search-obj", timeout=15000)
                page.wait_for_timeout(1500)
            except Exception as e:  # noqa: BLE001
                body = page.inner_text("body")[:500] if page else ""
                if any(k in body for k in ("安全驗證", "Just a moment", "機器人")):
                    log("  ⚠ [樂屋網] 出現機器人驗證，停止讀取")
                else:
                    log(f"  [樂屋網] 第 {n} 頁沒有物件（{e.__class__.__name__}），結束")
                break
            cards = page.evaluate(CARD_JS)
            new = 0
            for c in cards:
                if c["ehid"] in out:
                    continue
                it = normalize(c, metas.get(c["ehid"]), county)
                if it:
                    out[c["ehid"]] = it
                    new += 1
            log(f"  [樂屋網] 第 {n} 頁：{new} 筆")
            if new == 0:
                break
            time.sleep(random.uniform(2.5, 4.5))
        browser.close()
    # 補上最後一批追蹤資料（591 來源編號）
    for ehid, it in out.items():
        if not it.get("same_as"):
            g = re.match(r"591/S(\d+)", str((metas.get(ehid) or {}).get("object_group_id") or ""))
            if g:
                it["same_as"] = f"sale-{g.group(1)}"
    return list(out.values())
