import requests, time
for q in ["平鎮車站", "平鎮火車站", "平鎮站, 桃園市", "Pingzhen Station"]:
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "json", "limit": 4, "countrycodes": "tw"},
                     headers={"User-Agent": "house-watcher/1.0 (personal)"}, timeout=20).json()
    print(q, [(x["display_name"][:80], x.get("type"), x["lat"], x["lon"]) for x in r]); time.sleep(1.2)
