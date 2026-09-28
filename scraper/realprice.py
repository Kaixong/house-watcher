"""實價登錄行情查詢

兩層資料：
1. 同社區：591 實價登錄（bff-market.591.com.tw）用社區編號查成交紀錄，最精準
2. 附近類似：內政部實價登錄開放資料（每季 zip），找同行政區、同路段、同建物型態、坪數相近的成交

輸出每個物件的 item["market"]：
{
  "community": {name, id, url, n, median_12m, median_all, trend:[[期間, 中位數, 筆數]], deals:[...]},
  "nearby":    {scope, n, median_12m, trend:[...], deals:[...]},
  "premium":   開價單價相對行情的百分比（正數=比行情貴）
}
"""
from __future__ import annotations

import csv
import io
import json
import random
import re
import statistics
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

PING = 3.30579  # 1 坪 = 3.30579 平方公尺
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}
MARKET_API = "https://bff-market.591.com.tw/v1/price/list"
LVR_URL = "https://plvr.land.moi.gov.tw/DownloadSeason?season={s}&type=zip&fileName=lvr_landcsv.zip"

# 內政部開放資料的縣市代碼
COUNTY_CODE = {
    "臺北市": "a", "臺中市": "b", "基隆市": "c", "臺南市": "d", "高雄市": "e", "新北市": "f",
    "宜蘭縣": "g", "桃園市": "h", "嘉義市": "i", "新竹縣": "j", "苗栗縣": "k", "南投縣": "m",
    "彰化縣": "n", "新竹市": "o", "雲林縣": "p", "嘉義縣": "q", "屏東縣": "t", "花蓮縣": "u",
    "臺東縣": "v", "金門縣": "w", "澎湖縣": "x", "連江縣": "z",
}
# 591 網址裡的 regionid → 縣市
REGION_591 = {
    1: "臺北市", 2: "基隆市", 3: "新北市", 4: "新竹市", 5: "新竹縣", 6: "桃園市", 7: "苗栗縣",
    8: "臺中市", 10: "彰化縣", 11: "南投縣", 12: "嘉義市", 13: "嘉義縣", 14: "雲林縣",
    15: "臺南市", 17: "高雄市", 19: "屏東縣", 21: "宜蘭縣", 22: "臺東縣", 23: "花蓮縣",
    24: "澎湖縣", 25: "金門縣", 26: "連江縣",
}
# 591 物件類型 → 實價登錄「建物型態」關鍵字
KIND_MAP = {
    "電梯大樓": ("住宅大樓", "華廈"), "大樓": ("住宅大樓",), "華廈": ("華廈",),
    "公寓": ("公寓",), "透天厝": ("透天厝",), "別墅": ("透天厝",), "套房": ("套房",),
}
# 備註含這些字的通常不是一般行情，排除
SPECIAL_NOTE = re.compile(r"親友|員工|特殊關係|關係人|瑕疵|凶宅|增建|持分|急買急賣|債權|法拍|含裝潢|政府機關")


def norm_county(name: str) -> str:
    return (name or "").replace("台", "臺").strip()


def road_key(addr: str) -> str:
    """從地址取出「路段」，例如「臺北市內湖區成功路四段31~60號」→「成功路四段」。"""
    a = (addr or "").replace("台", "臺")
    a = re.sub(r"^.*?(?:[市縣])", "", a, count=1) if re.match(r"^\S{2,3}[市縣]", a) else a
    a = re.sub(r"^\S{1,3}?[區鄉鎮市](?=\S)", "", a, count=1)
    m = re.search(r"([^\d\s、,，]{1,12}?(?:路|街|大道)(?:[一二三四五六七八九十]+段)?)", a)
    return m.group(1) if m else ""


def roc_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s.isdigit() or len(s) not in (6, 7):
        return None
    y, m, d = int(s[:-4]) + 1911, int(s[-4:-2]), int(s[-2:])
    try:
        return date(y, m, d)
    except ValueError:
        return None


def quarter(d: date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _median(xs):
    return round(statistics.median(xs), 1) if xs else None


def summarize(deals: list[dict], today: date | None = None) -> dict:
    """deals: [{date:'YYYY-MM-DD', unit:萬/坪, ...}] → 中位數、每季走勢。"""
    today = today or date.today()
    deals = sorted([d for d in deals if d.get("unit")], key=lambda d: d["date"], reverse=True)
    cut12 = (today - timedelta(days=365)).isoformat()
    last12 = [d["unit"] for d in deals if d["date"] >= cut12]
    cut24 = (today - timedelta(days=730)).isoformat()
    last24 = [d["unit"] for d in deals if d["date"] >= cut24]
    byq = defaultdict(list)
    for d in deals:
        byq[quarter(date.fromisoformat(d["date"]))].append(d["unit"])
    trend = [[q, _median(v), len(v)] for q, v in sorted(byq.items())]
    return {
        "n": len(deals),
        "n_12m": len(last12),
        "median_12m": _median(last12),
        "n_24m": len(last24),
        "median_24m": _median(last24),
        "median_all": _median([d["unit"] for d in deals]),
        "trend": trend[-16:],
        "deals": deals[:12],
    }


# ---------------------------------------------------------------------------
# 1. 591 社區實價登錄
# ---------------------------------------------------------------------------
def fetch_community_deals(cid: int | str, trans_types=(1,), max_pages=4, log=print) -> list[dict]:
    out = []
    for tt in trans_types:
        for page in range(1, max_pages + 1):
            try:
                r = requests.get(MARKET_API, headers=UA, timeout=20, params={
                    "community_id": cid, "split_park": 1, "trans_type": tt,
                    "page": page, "page_size": 50, "_source": 0})
                data = (r.json() or {}).get("data") or {}
            except Exception as e:  # noqa: BLE001
                log(f"    社區 {cid} 查詢失敗：{e.__class__.__name__}")
                break
            for it in data.get("items") or []:
                if it.get("is_special"):
                    continue
                try:
                    unit = float(str((it.get("unit_price") or {}).get("price", "")).replace(",", ""))
                except ValueError:
                    continue
                total = str(it.get("total_price_v", "")).replace(",", "")
                out.append({
                    "date": it.get("trans_date", ""),
                    "unit": unit,
                    "total": float(total) if total.replace(".", "").isdigit() else None,
                    "ping": _f((it.get("build_area_v") or {}).get("area")),
                    "main_ping": _f((it.get("building_area") or {}).get("area")),
                    "layout": it.get("layout_v2") or it.get("layout", ""),
                    "floor": f"{it.get('shift_floor', '')}/{it.get('total_floor', '')}",
                    "address": it.get("address", ""),
                    "park": it.get("park_type_str", ""),
                    "presale": tt == 2,
                })
            if page >= int(data.get("total_page") or 1):
                break
            time.sleep(random.uniform(0.8, 1.6))
    return [d for d in out if d["date"]]


def _f(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 2. 內政部實價登錄開放資料
# ---------------------------------------------------------------------------
def recent_seasons(n: int, today: date | None = None) -> list[str]:
    """由近到遠的季別代碼，例如 ['115S2','115S1',...]；多列幾季以防最新一季尚未發布。"""
    today = today or date.today()
    y, q = today.year, (today.month - 1) // 3 + 1
    out = []
    for _ in range(n + 2):
        out.append(f"{y - 1911}S{q}")
        q -= 1
        if q == 0:
            y, q = y - 1, 4
    return out


class LvrData:
    """下載並快取各季 zip，只解析需要的縣市。"""

    def __init__(self, cache_dir: Path, seasons: int = 8, log=print):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.n = seasons
        self.log = log
        self._rows: dict[str, list[dict]] = {}
        self.all_deals: dict[str, list[tuple[str, float]]] = {}  # 核對用：含特殊交易的 (日期, 總價萬)
        self._zips: list[Path] | None = None

    def _zip_paths(self) -> list[Path]:
        if self._zips is not None:
            return self._zips
        got = []
        for s in recent_seasons(self.n):
            if len(got) >= self.n:
                break
            p = self.cache / f"{s}.zip"
            if not (p.exists() and p.stat().st_size > 1_000_000):
                try:
                    r = requests.get(LVR_URL.format(s=s), headers=UA, timeout=120)
                    if r.status_code != 200 or len(r.content) < 1_000_000 or r.content[:2] != b"PK":
                        continue  # 該季尚未發布
                    p.write_bytes(r.content)
                    self.log(f"  下載實價登錄 {s}（{len(r.content) / 1e6:.1f} MB）")
                except Exception as e:  # noqa: BLE001
                    self.log(f"  ⚠ 實價登錄 {s} 下載失敗：{e.__class__.__name__}")
                    continue
            got.append(p)
        self._zips = got
        return got

    def coverage(self) -> tuple[str, str]:
        """下載的季別大致涵蓋的交易日期（申報通常在交易後 1～2 個月）。"""
        codes = sorted(p.stem for p in self._zip_paths())
        if not codes:
            return "9999", "0000"
        def start(code):
            y, q = code.split("S")
            return date(int(y) + 1911, (int(q) - 1) * 3 + 1, 1)
        lo = start(codes[0]) + timedelta(days=30)    # 季初的交易可能申報在更早、沒下載的季別
        hi = start(codes[-1]) + timedelta(days=60)   # 季末的交易可能還沒公布
        return lo.isoformat(), hi.isoformat()

    def rows(self, county: str) -> list[dict]:
        county = norm_county(county)
        if county in self._rows:
            return self._rows[county]
        code = COUNTY_CODE.get(county)
        rows: list[dict] = []
        if not code:
            self.log(f"  ⚠ 不認得的縣市「{county}」，略過附近行情")
            self._rows[county] = rows
            return rows
        for zp in self._zip_paths():
            try:
                with zipfile.ZipFile(zp) as z:
                    raw = z.read(f"{code}_lvr_land_a.csv").decode("utf-8-sig", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            reader = csv.DictReader(io.StringIO(raw))
            allv = self.all_deals.setdefault(county, [])
            for i, r in enumerate(reader):
                if i == 0 and r.get("鄉鎮市區", "").startswith("The"):
                    continue  # 英文標題列
                dd, tt = roc_date(r.get("交易年月日", "")), _f(r.get("總價元"))
                if dd and tt and "建物" in r.get("交易標的", ""):
                    allv.append((dd.isoformat(), round(tt / 10000)))
                d = parse_lvr_row(r)
                if d:
                    rows.append(d)
        self.log(f"  {county} 實價登錄：{len(rows)} 筆住宅成交（{len(self._zip_paths())} 季）")
        self._rows[county] = rows
        return rows


def parse_lvr_row(r: dict) -> dict | None:
    if "建物" not in r.get("交易標的", ""):
        return None
    if SPECIAL_NOTE.search(r.get("備註", "") or ""):
        return None
    use = r.get("主要用途", "")
    if use and "住" not in use:
        return None
    d = roc_date(r.get("交易年月日", ""))
    area = _f(r.get("建物移轉總面積平方公尺")) or 0
    total = _f(r.get("總價元")) or 0
    park_a = _f(r.get("車位移轉總面積平方公尺")) or 0
    park_p = _f(r.get("車位總價元")) or 0
    if not d or area <= 0 or total <= 0:
        return None
    if park_p > 0 and area - park_a > 0:
        unit = (total - park_p) / 10000 / ((area - park_a) / PING)
    else:
        unit = total / 10000 / (area / PING)
    if not 5 < unit < 600:  # 明顯異常值
        return None
    built = roc_date(r.get("建築完成年月", ""))
    addr = r.get("土地位置建物門牌", "")
    return {
        "date": d.isoformat(),
        "unit": round(unit, 1),
        "total": round(total / 10000),
        "ping": round(area / PING, 1),
        "main_ping": round((_f(r.get("主建物面積")) or 0) / PING, 1) or None,
        "layout": f"{r.get('建物現況格局-房', '')}房{r.get('建物現況格局-廳', '')}廳{r.get('建物現況格局-衛', '')}衛",
        "floor": f"{r.get('移轉層次', '')}/{r.get('總樓層數', '')}",
        "type": r.get("建物型態", ""),
        "district": r.get("鄉鎮市區", ""),
        "road": road_key(addr),
        "address": re.sub(r"^\S{2,3}[市縣]", "", addr),
        "age": round((d - built).days / 365.25, 1) if built and built <= d else None,
        "park": r.get("車位類別", ""),
    }


def find_nearby(item: dict, rows: list[dict], min_n: int = 6) -> tuple[str, list[dict]]:
    """由嚴到寬找類似成交：同路段 → 同行政區。"""
    district = item.get("district", "")
    road = road_key(item.get("address", ""))
    types = KIND_MAP.get(item.get("kind", ""), ())
    ping = item.get("ping")
    age = item.get("age")
    if item.get("source") == "591新建案":
        age = 0  # 新建案只和屋齡 10 年內的成交比較

    def ok(r, strict_age=True):
        if district and r["district"] != district:
            return False
        if types and not any(t in r["type"] for t in types):
            return False
        if ping and not (ping * 0.65 <= r["ping"] <= ping * 1.35):
            return False
        if strict_age and age is not None and r["age"] is not None and abs(r["age"] - age) > 10:
            return False
        return True

    tiers = []
    if road:
        tiers.append((f"{district}{road}", lambda r: r["road"] == road and ok(r)))
        tiers.append((f"{district}{road}（不限屋齡）", lambda r: r["road"] == road and ok(r, False)))
    tiers.append((f"{district}（同型態、坪數相近）", lambda r: ok(r)))
    for scope, fn in tiers:
        hit = [r for r in rows if fn(r)]
        if len(hit) >= min_n:
            return scope, hit
    return tiers[-1][0], [r for r in rows if tiers[-1][1](r)]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def enrich(items: list[dict], cfg: dict, cache_dir: Path, log=print) -> None:
    """為每個物件加上 item['market']。會使用 / 更新 data/market_cache.json。"""
    cfg = cfg or {}
    if not cfg.get("enabled", True) or not items:
        return
    cache_file = Path(cache_dir) / "market_cache.json"
    cache = json.loads(cache_file.read_text("utf-8")) if cache_file.exists() else {}
    today = date.today()
    lvr = LvrData(Path(cache_dir) / "lvr", seasons=int(cfg.get("seasons", 8)), log=log)
    gov_index: dict[str, tuple] = {}  # 縣市 → (日期+總價索引, 最早日期)

    def gov_check(county: str, deals: list[dict]) -> tuple[int, int]:
        """591 社區成交 vs 內政部：同一天、總價差 1 萬內即視為核對成功。回傳 (核對成功, 可核對筆數)。"""
        if county not in gov_index:
            idx = defaultdict(list)
            lvr.rows(county)
            for dd, tt in lvr.all_deals.get(norm_county(county), []):
                idx[dd].append(tt)
            gov_index[county] = (idx,) + lvr.coverage()
        idx, first, last = gov_index[county]
        ok = n = 0
        for d in deals:
            if not d.get("date") or not (first <= d["date"] <= last) or d.get("total") is None or d.get("presale"):
                d.pop("gov", None)  # 預售屋在另一份資料、太舊的不在下載範圍：不列入核對
                continue
            n += 1
            d["gov"] = any(abs(t - d["total"]) <= 1 for t in idx.get(d["date"], []))
            ok += d["gov"]
        return ok, n
    fetched = 0
    max_fetch = int(cfg.get("max_community_lookups", 80))

    for it in items:
        m: dict = {}
        # --- 1. 同社區 ---
        cid = it.get("community_id")
        if cid and cfg.get("community", True):
            key = str(cid)
            c = cache.get(key)
            stale = not c or c.get("fetched", "") < (today - timedelta(days=6)).isoformat()
            if stale and fetched < max_fetch:
                tts = (1, 2) if it.get("source") == "591新建案" else (1,)
                deals = fetch_community_deals(cid, tts, log=log)
                c = {"fetched": today.isoformat(), "deals": deals}
                cache[key] = c
                fetched += 1
                time.sleep(random.uniform(1, 2))
            if c and c.get("deals"):
                if it.get("county"):
                    ok, n = gov_check(it["county"], c["deals"])
                else:
                    ok = n = 0
                s = summarize(c["deals"], today)
                s["gov_ok"], s["gov_n"] = ok, n
                s.update({"name": it.get("community", ""), "id": cid,
                          "url": f"https://market.591.com.tw/{cid}"})
                m["community"] = s
        # --- 2. 附近類似（內政部）---
        county = it.get("county")
        if county and cfg.get("nearby", True):
            rows = lvr.rows(county)
            if rows:
                scope, hit = find_nearby(it, rows)
                if hit:
                    s = summarize(hit, today)
                    s["scope"] = scope
                    m["nearby"] = s
        # --- 開價 vs 行情 ---
        ref = None
        c, n = m.get("community") or {}, m.get("nearby") or {}
        for src, x, key, label in (("community", c, "12m", "同社區近一年"), ("community", c, "24m", "同社區近兩年"),
                                   ("nearby", n, "12m", "附近近一年"), ("nearby", n, "all", "附近歷年"),
                                   ("community", c, "all", "同社區歷年")):
            if x.get(f"n_{key}" if key != "all" else "n", 0) >= 3 and x.get(f"median_{key}"):
                ref = (src, x[f"median_{key}"], label)
                break
        if ref and it.get("unit_price"):
            m["premium"] = round((it["unit_price"] / ref[1] - 1) * 100, 1)
            m["premium_ref"] = ref[0]
            m["ref_price"] = ref[1]
            m["ref_label"] = ref[2]
        if m:
            m["updated"] = today.isoformat()
            it["market"] = m

    cache_file.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    log(f"  行情查詢完成：社區 API 查詢 {fetched} 次，{sum(1 for i in items if i.get('market'))} 筆物件有行情")
