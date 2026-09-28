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
    if _gt(item.get("unit_price"), f.get("max_unit_price")):
        return False
    if _gt(item.get("age"), f.get("max_age")):
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
