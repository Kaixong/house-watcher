"""房房小助手：主程式

用法：
  python run.py              # 抓資料、更新儀表板、寄通知
  python run.py --no-email   # 不寄信（測試用）
  python run.py --show       # 顯示瀏覽器視窗（除錯用）
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from scraper import newhouse591, realprice, sale591
from scraper.filters import needs_detail, passes, passes_detail
from scraper.notify import build_email, send_email

ROOT = Path(__file__).parent
CACHE = ROOT / ".cache"
STATE = ROOT / "data" / "listings.json"
DASH_DATA = ROOT / "docs" / "data.json"
TPE = timezone(timedelta(hours=8))


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text("utf-8"))
    return {"items": {}, "runs": []}


def _county_of(search: dict) -> str:
    """搜尋條件所在縣市：優先用 config 的 county，否則從 591 網址的 regionid 推算。"""
    if search.get("county"):
        return realprice.norm_county(search["county"])
    qs = parse_qs(urlparse(search.get("url", "")).query)
    rid = (qs.get("regionid") or qs.get("region") or [""])[0]
    return realprice.REGION_591.get(int(rid), "") if str(rid).isdigit() else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text("utf-8"))
    state = load_state()
    # 條件改名或刪除後，舊條件的物件不再保留
    names = {x["name"] for x in cfg.get("searches", [])}
    state["items"] = {k: v for k, v in state["items"].items() if v.get("search") in names}
    first_run = not state["items"]
    now = datetime.now(TPE).strftime("%Y-%m-%d %H:%M")
    warnings: list[str] = []
    new_items, drops = [], []
    seen_now: set[str] = set()

    for s in cfg.get("searches", []):
        name, typ = s["name"], s.get("type", "sale")
        print(f"▶ {name}（{typ}）")
        try:
            if typ == "sale":
                items = sale591.scrape(s["url"], s.get("max_pages", 5), headless=not args.show)
            elif typ == "newhouse":
                items = newhouse591.scrape(s["url"], s.get("max_pages", 3))
            else:
                warnings.append(f"{name}：不支援的 type「{typ}」")
                continue
        except Exception as e:  # noqa: BLE001
            warnings.append(f"{name}：抓取失敗（{e.__class__.__name__}: {e}）")
            continue
        if not items:
            warnings.append(f"{name}：沒有抓到任何資料，可能被網站阻擋或網址條件有誤")
        matched = [it for it in items if passes(it, s.get("filters"))]
        print(f"  共 {len(items)} 筆，列表條件符合 {len(matched)} 筆")
        if typ == "sale" and needs_detail(s.get("filters")) and matched:
            dcache = state.setdefault("details", {})
            for it in matched:  # 沿用之前讀過的詳情（含沒通過條件的），避免重複開網頁
                old = state["items"].get(it["id"]) or {}
                if old.get("detail") or it["id"] in dcache:
                    it["detail"] = old.get("detail") or dcache[it["id"]]
            try:
                sale591.scrape_details(matched, headless=not args.show,
                                       max_pages=int(s.get("max_details", 60)))
            except Exception as e:  # noqa: BLE001
                warnings.append(f"{name}：詳情頁讀取失敗（{e.__class__.__name__}）")
            for it in matched:
                if it.get("detail"):
                    dcache[it["id"]] = it["detail"]
                it.pop("unverified", None)
            kept = []
            for it in matched:
                ok, why = passes_detail(it, s.get("filters"))
                if ok:
                    if why:
                        it["unverified"] = why
                    kept.append(it)
            print(f"  詳情條件符合 {len(kept)} 筆")
            matched = kept

        county = _county_of(s)
        for it in matched:
            it["search"] = name
            if county and not it.get("county"):
                it["county"] = county
            old = state["items"].get(it["id"])
            seen_now.add(it["id"])
            if old is None:
                it["first_seen"] = now
                it["price_history"] = [[now, it.get("price")]] if it.get("price") else []
                if not first_run:
                    new_items.append(it)
            else:
                it["first_seen"] = old.get("first_seen", now)
                hist = old.get("price_history", [])
                if it.get("price") and old.get("price") and it["price"] < old["price"]:
                    it["prev_price"] = old["price"]
                    drops.append(it)
                if it.get("price") and (not hist or hist[-1][1] != it["price"]):
                    hist.append([now, it["price"]])
                it["price_history"] = hist
            it["last_seen"] = now
            state["items"][it["id"]] = it

    # 實價登錄行情（只查目前在架的物件）
    if (cfg.get("realprice") or {}).get("enabled", True):
        print("▶ 查詢實價登錄行情")
        try:
            realprice.enrich([state["items"][i] for i in seen_now], cfg.get("realprice") or {}, CACHE)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"實價登錄行情查詢失敗（{e.__class__.__name__}: {e}）")

    for iid, it in state["items"].items():
        it["active"] = iid in seen_now
        it["is_new"] = any(n["id"] == iid for n in new_items)

    state["runs"] = (state.get("runs", []) + [{
        "time": now, "new": len(new_items), "drops": len(drops),
        "active": len(seen_now), "warnings": warnings,
    }])[-52:]

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), "utf-8")
    DASH_DATA.parent.mkdir(exist_ok=True)
    DASH_DATA.write_text(json.dumps({
        "updated": now,
        "searches": [s["name"] for s in cfg.get("searches", [])],
        "runs": state["runs"],
        "items": sorted(state["items"].values(),
                        key=lambda x: (not x.get("active"), x.get("first_seen", "")),
                        reverse=False),
    }, ensure_ascii=False), "utf-8")

    print(f"✔ 完成：新物件 {len(new_items)}、降價 {len(drops)}、目前在架 {len(seen_now)}")
    if first_run:
        print("  （第一次執行：所有物件都當作基準，不寄「新物件」通知）")
    for w in warnings:
        print(f"  ⚠ {w}")

    n = cfg.get("notify", {}) or {}
    if not args.no_email and n.get("email", True):
        if first_run:
            subj = f"🏠 房房小助手已啟動：目前有 {len(seen_now)} 筆符合條件"
            _, body = build_email([state["items"][i] for i in seen_now], [], warnings,
                                  cfg.get("dashboard_url", ""), n.get("max_items_in_email", 30))
            _safe_send(subj, body, warnings)
        elif new_items or drops or warnings or n.get("send_when_empty"):
            subj, body = build_email(new_items, drops, warnings,
                                     cfg.get("dashboard_url", ""), n.get("max_items_in_email", 30))
            _safe_send(subj, body, warnings)


def _safe_send(subj, body, warnings):
    try:
        send_email(subj, body)
    except Exception as e:  # noqa: BLE001
        print(f"  ✖ 寄信失敗：{e.__class__.__name__}: {e}")
        print("    → 請確認 GMAIL_USER / GMAIL_APP_PASSWORD 是否正確（要用 16 碼應用程式密碼）")


if __name__ == "__main__":
    main()
