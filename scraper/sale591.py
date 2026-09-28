"""591 中古屋爬蟲（sale.591.com.tw）

591 中古屋列表由瀏覽器端 JavaScript 產生，因此用 Playwright 開真的瀏覽器載入頁面，
再從畫面上的 .ware-item 卡片讀資料。分頁用網址的 page=N。
"""
from __future__ import annotations

import random
import re
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

LIST_SELECTOR = ".ware-item"

# 在瀏覽器裡執行，把每張卡片轉成 dict
EXTRACT_JS = r"""
() => [...document.querySelectorAll('.ware-item')].map(el => {
  const q = s => el.querySelector(s);
  const txt = s => (q(s)?.textContent || '').trim();
  const a = q('.ware-item__header a');
  const priceSec = q('.ware-item__price-section');
  return {
    id: el.getAttribute('data-id'),
    title: (a?.textContent || el.getAttribute('title') || '').trim(),
    url: a?.href || '',
    image: q('img.ware-item__image')?.getAttribute('data-src') || q('img.ware-item__image')?.src || '',
    attrs: [...el.querySelectorAll('.ware-item__attr')].map(s => s.textContent.trim()),
    community: txt('.ware-item__community'),
    community_url: q('.ware-item__community a')?.href || '',
    section: txt('.ware-item__section').replace(/-$/, ''),
    address: txt('.ware-item__address'),
    price_text: txt('.ware-item__price-value'),
    price_section_text: (priceSec?.textContent || '').trim(),
    tags: [...el.querySelectorAll('.tags-row__item, .tags-row__tag')].map(s => s.textContent.trim()),
    poster: txt('.user-info__name'),
    featured: !!q('.ware-item__badge--featured'),
  };
})
"""


def page_url(base_url: str, page: int, page_size: int = 30) -> str:
    """第 1 頁用使用者貼的原始網址；之後用 firstRow 參數換頁（591 的原生分頁方式）。"""
    if page == 1:
        return base_url
    p = urlparse(base_url)
    qs = parse_qs(p.query, keep_blank_values=True)
    qs.pop("page", None)
    qs["firstRow"] = [str((page - 1) * page_size)]
    return urlunparse(p._replace(query=urlencode(qs, doseq=True, safe=",$_")))


def _num(s: str) -> float | None:
    m = re.search(r"[\d,]+(?:\.\d+)?", s or "")
    return float(m.group().replace(",", "")) if m else None


def _cid(url: str):
    m = re.search(r"market\.591\.com\.tw/(\d+)", url or "")
    return int(m.group(1)) if m else None


def normalize(raw: dict) -> dict:
    """把卡片原始文字整理成統一欄位。"""
    attrs = raw.get("attrs", [])
    layout = next((a for a in attrs if re.search(r"\d+房", a)), "")
    ping = next((_num(a) for a in attrs if "坪" in a), None)
    floor = next((a for a in attrs if re.search(r"\d+F", a, re.I)), "")
    age_txt = next((a for a in attrs if re.search(r"(年|個月)$", a) and "坪" not in a), "")
    age = None
    if age_txt:
        y = re.search(r"([\d.]+)\s*年", age_txt)
        age = float(y.group(1)) if y else 0.0  # 「2個月」視為 0 年
    kind = attrs[0] if attrs and not re.search(r"\d", attrs[0]) else ""
    unit = re.search(r"([\d,.]+)\s*萬/坪", raw.get("price_section_text", ""))
    return {
        "source": "591中古屋",
        "id": f"sale-{raw['id']}",
        "title": raw.get("title", ""),
        "url": (raw.get("url") or "").split("?")[0]
        or f"https://sale.591.com.tw/home/house/detail/2/{raw['id']}.html",
        "image": raw.get("image", ""),
        "price": _num(raw.get("price_text", "")),  # 萬
        "unit_price": float(unit.group(1).replace(",", "")) if unit else None,  # 萬/坪
        "ping": ping,
        "layout": layout,
        "age": age,
        "floor": floor,
        "kind": kind,
        "community": raw.get("community", ""),
        "community_id": _cid(raw.get("community_url", "")),
        "district": raw.get("section", ""),
        "address": raw.get("address", ""),
        "tags": raw.get("tags", []),
        "poster": raw.get("poster", ""),
    }


def _dump_debug(page, n, log):
    """載入失敗時存下截圖與網頁內容到 data/debug/，方便找原因。"""
    from pathlib import Path
    d = Path(__file__).resolve().parent.parent / "data" / "debug"
    d.mkdir(parents=True, exist_ok=True)
    try:
        log(f"    頁面標題：{page.title()!r}　網址：{page.url}")
        body = page.evaluate("() => document.body ? document.body.innerText.slice(0, 400) : ''")
        log("    頁面文字：" + " ".join(body.split())[:300])
        classes = page.evaluate("""() => [...new Set([...document.querySelectorAll('[class]')]
            .flatMap(e => [...e.classList]).filter(c => /item|list|house|ware/i.test(c)))].slice(0, 40)""")
        log(f"    相關 class：{classes}")
        (d / f"sale_page{n}.html").write_text(page.content(), "utf-8")
        page.screenshot(path=str(d / f"sale_page{n}.png"), full_page=False)
    except Exception as e:  # noqa: BLE001
        log(f"    （除錯資料儲存失敗：{e}）")


def scrape(url: str, max_pages: int = 5, headless: bool = True, log=print) -> list[dict]:
    from playwright.sync_api import sync_playwright

    results: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
        )
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page = ctx.new_page()

        for n in range(1, max_pages + 1):
            u = page_url(url, n)
            log(f"  [591中古屋] 第 {n} 頁：{u}")
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_selector(LIST_SELECTOR, timeout=20000)
                page.mouse.wheel(0, 4000)  # 觸發 lazy-load
                time.sleep(1.5)
            except Exception as e:  # noqa: BLE001
                log(f"  ⚠ 第 {n} 頁載入失敗：{e.__class__.__name__}")
                _dump_debug(page, n, log)
                break
            raws = page.evaluate(EXTRACT_JS)
            new = 0
            for r in raws:
                if r.get("id") and r["id"].isdigit() and r["id"] not in results:
                    results[r["id"]] = normalize(r)
                    new += 1
            log(f"    取得 {new} 筆")
            if new == 0 or len(raws) < 20:
                break
            time.sleep(random.uniform(3, 6))  # 禮貌性延遲，別對網站造成負擔
        browser.close()
    return list(results.values())
