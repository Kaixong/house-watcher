import json, sys, collections
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("rp", "realprice.py"); rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
from pathlib import Path
lvr = rp.LvrData(Path("lvrc"), seasons=2)
rows = lvr.rows("桃園市")
byd = collections.defaultdict(list)
for r in rows: byd[r["date"]].append(r)
lo, hi = lvr.coverage(); print("rows", len(rows), "coverage", lo, hi)
# 也看原始檔（未過濾）有多少筆，以及過濾掉的原因
import zipfile, csv, io
raw = []
for zp in lvr._zip_paths():
    with zipfile.ZipFile(zp) as z:
        for i, r in enumerate(csv.DictReader(io.StringIO(z.read("h_lvr_land_a.csv").decode("utf-8-sig")))):
            if i == 0: continue
            raw.append(r)
rawd = collections.defaultdict(list)
for r in raw:
    d = rp.roc_date(r.get("交易年月日", ""))
    if d: rawd[d.isoformat()].append(r)
print("raw rows", len(raw))
d = json.load(open("data.json", encoding="utf-8"))
tested = 0; stats = collections.Counter()
for it in d["items"]:
    c = (it.get("market") or {}).get("community")
    if not c or it["source"] != "591中古屋": continue
    for dl in c["deals"]:
        if dl.get("presale") or not (lo <= dl["date"] <= hi): continue
        cands = byd.get(dl["date"], []); rc = rawd.get(dl["date"], [])
        hit = [r for r in cands if abs(r["total"] - dl["total"]) <= 1]
        rawhit = [r for r in rc if abs(float(r["總價元"] or 0) / 1e4 - dl["total"]) <= 1]
        stats["filtered_hit" if hit else ("raw_only" if rawhit else "none")] += 1
        if not hit and tested < 6:
            tested += 1
            near = sorted(rc, key=lambda r: abs(float(r["總價元"] or 0) / 1e4 - dl["total"]))[:2]
            print("MISS", it.get("community"), dl["date"], dl["total"], dl.get("address"), "| same-day raw nearest:",
                  [(round(float(r["總價元"]) / 1e4), r["土地位置建物門牌"][:22], r["備註"][:15], r["主要用途"]) for r in near])
print(stats)
