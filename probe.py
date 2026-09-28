import subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(["python", "-m", "http.server", "8770", "-d", "site"]); time.sleep(1)
Q = "({sy: Math.round(scrollY), mapTop: Math.round(document.getElementById('map').getBoundingClientRect().top), sel: document.querySelectorAll('.pin.sel').length, hl: document.querySelectorAll('.card.hl').length, popup: document.querySelectorAll('.leaflet-popup').length, btn: !document.getElementById('toMap').hidden})"
with sync_playwright() as p:
    b = p.chromium.launch()
    mp = b.new_page(**p.devices["iPhone 13"]); errs = []; mp.on("pageerror", lambda e: errs.append(str(e)))
    mp.goto("http://localhost:8770/"); mp.wait_for_timeout(2000); mp.click("#vMap"); mp.wait_for_timeout(3000)
    mp.evaluate("scrollTo(0, document.getElementById('map').getBoundingClientRect().top + scrollY - 10)"); mp.wait_for_timeout(500)
    pins = mp.locator(".pin"); n = pins.count()
    pins.nth(n // 2).click(force=True); mp.wait_for_timeout(1200); a = mp.evaluate(Q)
    pins.nth(n // 3).click(force=True); mp.wait_for_timeout(1200); b2 = mp.evaluate(Q)
    mp.screenshot(path="shot_phone_map.png")
    mp.locator(".leaflet-popup [data-focus]").click(); mp.wait_for_timeout(1200)
    c = mp.evaluate(Q + ".sy") if False else mp.evaluate("(() => { const e = document.querySelector('.card.hl'); const r = e.getBoundingClientRect(); return {cardVisible: r.top > -5 && r.bottom < innerHeight + 5, btn: !document.getElementById('toMap').hidden} })()")
    mp.screenshot(path="shot_phone_card.png")
    mp.click("#toMap"); mp.wait_for_timeout(1500); d = mp.evaluate(Q)
    dp = b.new_page(viewport={"width": 1280, "height": 900}); dp.goto("http://localhost:8770/"); dp.wait_for_timeout(2000); dp.click("#vMap"); dp.wait_for_timeout(3000)
    sy0 = dp.evaluate("scrollY"); dpins = dp.locator(".pin"); dpins.nth(dpins.count() // 2).click(force=True); dp.wait_for_timeout(1500)
    e = dp.evaluate("(() => { const el = document.querySelector('#mapList .card.hl'), L = document.getElementById('mapList').getBoundingClientRect(), r = el.getBoundingClientRect(); return {sy: scrollY, inSide: r.top >= L.top - 5 && r.bottom <= L.bottom + 5, sel: document.querySelectorAll('.pin.sel').length} })()")
    dp.screenshot(path="shot_desk.png")
    print("errors:", errs); print("phone pin1:", a); print("phone pin2:", b2); print("phone 看完整資料:", c); print("phone 回到地圖:", d); print("desk sy0:", sy0, e)
    b.close()
srv.kill()
