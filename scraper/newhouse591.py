"""591 新建案爬蟲（newhouse.591.com.tw）

新建案列表背後有 JSON API（bff-newhouse.591.com.tw/v1/list-search），
直接用 requests 呼叫即可，不需要開瀏覽器。
使用者貼的搜尋網址的參數（regionid、sectionid、price…）會原封不動帶給 API。
"""
from __future__ import annotations

import random
import re
import secrets
import time
from urllib.parse import parse_qsl, urlparse

import requests

API = "https://bff-newhouse.591.com.tw/v1/list-search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Origin": "https://newhouse.591.com.tw",
    "Referer": "https://newhouse.591.com.tw/",
}


def parse_unit_price(price: str, unit: str) -> tuple[float | None, float | None]:
    """'85~95' + '萬/坪' → (85, 95)；價格待定 → (None, None)。"""
    if not price or "待定" in price:
        return None, None
    nums = [float(x.replace(",", "")) for x in re.findall(r"[\d,]+(?:\.\d+)?", price)]
    if not nums:
        return None, None
    if "坪" not in (unit or "") and "坪" not in price:
        return None, None  # 非單價（例如總價），不當單價比較
    return min(nums), max(nums)


def normalize(it: dict) -> dict:
    lo, hi = parse_unit_price(str(it.get("price", "")), str(it.get("price_unit", "")))
    price_txt = f"{it.get('price', '')}{it.get('price_unit', '')}".strip()
    return {
        "source": "591新建案",
        "id": f"new-{it['hid']}",
        "title": it.get("build_name", ""),
        "url": f"https://newhouse.591.com.tw/{it['hid']}",
        "image": it.get("cover", ""),
        "price": None,
        "price_text": price_txt,
        "unit_price": lo,
        "unit_price_max": hi,
        "ping": None,
        "ping_text": it.get("area", ""),
        "layout": it.get("room", ""),
        "age": None,
        "floor": "",
        "kind": it.get("purpose_str", ""),
        "community": it.get("build_name", ""),
        "community_id": it.get("community_id") or None,
        "county": (it.get("region") or "").replace("台", "臺"),
        "district": it.get("section", ""),
        "address": it.get("address", ""),
        "tags": it.get("tag", []) or [],
        "poster": it.get("shop_name", ""),
        "is_ad": bool(it.get("ad_type")),
    }


def scrape(url: str, max_pages: int = 3, log=print) -> list[dict]:
    params = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
    params.pop("page", None)
    params.update({"device": "pc", "device_id": secrets.token_urlsafe(15)})
    s = requests.Session()
    s.headers.update(HEADERS)
    out: dict[str, dict] = {}
    for n in range(1, max_pages + 1):
        log(f"  [591新建案] 第 {n} 頁")
        try:
            r = s.get(API, params={"page": n, **params}, timeout=30)
            r.raise_for_status()
            data = r.json().get("data") or {}
        except Exception as e:  # noqa: BLE001
            log(f"  ⚠ 第 {n} 頁失敗：{e}")
            break
        items = data.get("items") or []
        for it in items:
            if it.get("hid") and f"new-{it['hid']}" not in out:
                out[f"new-{it['hid']}"] = normalize(it)
        log(f"    取得 {len(items)} 筆（共 {data.get('total', '?')} 筆）")
        if not items or n >= int(data.get("total_page") or 1):
            break
        time.sleep(random.uniform(2, 4))
    return list(out.values())
