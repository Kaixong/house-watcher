import requests, time
for q in ["中華路一段550號, 中壢區, 桃園市", "桃園市中壢區中華路一段550號", "日月光, 中壢區", "ASE, Zhongli"]:
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "json", "limit": 3, "countrycodes": "tw"},
                     headers={"User-Agent": "house-watcher/1.0 (personal)"}, timeout=20).json()
    print(q, [(x["display_name"][:80], x["lat"], x["lon"]) for x in r]); time.sleep(1.2)
r = requests.get("https://nominatim.openstreetmap.org/search", params={"street": "中華路一段", "city": "中壢區", "state": "桃園市", "format": "json", "limit": 3},
                 headers={"User-Agent": "house-watcher/1.0 (personal)"}, timeout=20).json()
print("street:", [(x["display_name"][:80], x["lat"], x["lon"]) for x in r])
