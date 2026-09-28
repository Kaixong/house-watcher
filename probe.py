import requests, time, json
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140 Safari/537.36"}
secs = {}
for page in range(1, 25):
    r = requests.get("https://bff-newhouse.591.com.tw/v1/list-search", headers=UA, timeout=20,
                     params={"page": page, "device": "pc", "device_id": "abc123xyz", "regionid": 6}).json()
    for it in (r.get("data") or {}).get("items") or []:
        secs[it.get("section")] = it.get("sectionid")
    time.sleep(1)
    if len(secs) >= 13: break
print("sections", json.dumps(secs, ensure_ascii=False))
for q in ["衛生福利部桃園醫院", "桃園市立武陵高級中等學校", "武陵高中 桃園", "部立桃園醫院", "美麗歐洲 中壢"]:
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "json", "limit": 2, "countrycodes": "tw"},
                     headers={"User-Agent": "house-watcher-probe/1.0 (github.com/Kaixong/house-watcher)"}, timeout=20).json()
    print("geo", q, [(x.get("display_name")[:60], x.get("lat"), x.get("lon")) for x in r])
    time.sleep(1.2)
