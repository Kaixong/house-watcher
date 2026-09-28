import json
from playwright.sync_api import sync_playwright
urls = {
  "樂居買房列表": "https://www.leju.com.tw/object_list?city_code=H",
  "信義房屋": "https://www.sinyi.com.tw/buy/list/Taoyuan-city/320-zip/default-desc/index",
  "永慶房屋": "https://buy.yungching.com.tw/region/桃園市-中壢區_c/",
  "樂屋網": "https://www.rakuya.com.tw/sell/result?city=4&zipcode=320",
  "住商不動產": "https://www.hbhousing.com.tw/buyhouse/桃園市/中壢區",
}
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    for name, u in urls.items():
        pg = ctx.new_page(); api = []
        pg.on("response", lambda r: api.append((r.status, r.url[:140])) if r.request.resource_type in ("xhr", "fetch") and "google" not in r.url and "facebook" not in r.url else None)
        try:
            resp = pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(7000)
            txt = " ".join(pg.inner_text("body").split())
            blocked = any(k in txt for k in ["安全驗證", "Just a moment", "Access denied", "機器人", "captcha", "Verify you are human"])
            print(f"== {name} | status {resp.status if resp else '?'} | {pg.url[:90]} | {pg.title()[:40]} | {'被擋（機器人驗證）' if blocked else 'OK'}")
            print("   text:", txt[:350])
            print("   api:", [a for a in api if a[0] == 200][:8])
        except Exception as e:
            print(f"== {name} | ERR {e.__class__.__name__}")
        pg.close()
    b.close()
