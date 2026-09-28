"""依 config.yaml 的 filters 篩選物件。欄位抓不到（None）時不會被刷掉。"""
from __future__ import annotations


def _gt(v, limit):
    return v is not None and limit is not None and v > limit


def _lt(v, limit):
    return v is not None and limit is not None and v < limit


def passes(item: dict, f: dict | None) -> bool:
    f = f or {}
    if _gt(item.get("price"), f.get("max_price")) or _lt(item.get("price"), f.get("min_price")):
        return False
    if _gt(item.get("ping"), f.get("max_ping")) or _lt(item.get("ping"), f.get("min_ping")):
        return False
    if _lt(item.get("main_ping"), f.get("min_main_ping")):
        return False
    if _gt(item.get("unit_price"), f.get("max_unit_price")):
        return False
    if _gt(item.get("age"), f.get("max_age")):
        return False
    if f.get("districts") and item.get("district") not in f["districts"]:
        return False
    text = " ".join(
        str(item.get(k, "")) for k in ("title", "address", "community", "district", "kind")
    ) + " " + " ".join(item.get("tags", []))
    inc = [k for k in (f.get("include_keywords") or []) if k]
    exc = [k for k in (f.get("exclude_keywords") or []) if k]
    if inc and not any(k in text for k in inc):
        return False
    if any(k in text for k in exc):
        return False
    return True


# 需要打開詳情頁才能判斷的條件
DETAIL_KEYS = ("parking", "transit_keywords", "min_main_ping")


def needs_detail(f: dict | None) -> bool:
    f = f or {}
    return bool(f.get("parking") or f.get("transit_keywords"))


def passes_detail(item: dict, f: dict | None) -> tuple[bool, str]:
    """回傳 (是否通過, 原因)。詳情頁讀取失敗的物件保留，但標記「未確認」。"""
    f = f or {}
    d = item.get("detail")
    if not d:
        return True, "詳情未確認"
    if f.get("parking") == "平面" and not d.get("parking_flat"):
        return False, f"車位非平面（{d.get('parking') or '無資料'}）"
    if f.get("parking") == "有" and not d.get("parking"):
        return False, "沒有車位"
    kws = f.get("transit_keywords") or []
    if kws and not any(k in t for t in d.get("traffic", []) for k in kws):
        return False, "附近交通沒有符合的站點"
    if _lt(d.get("main_ping"), f.get("min_main_ping")):
        return False, "主建物坪數不足"
    return True, ""
