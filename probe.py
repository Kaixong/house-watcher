import subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(["python", "-m", "http.server", "8770", "-d", "site"]); time.sleep(1)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:8770/"); pg.wait_for_timeout(2500); pg.click("#vMap"); pg.wait_for_timeout(3500)
    pins = pg.locator(".pin"); pins.nth(pins.count() // 2).click(force=True); pg.wait_for_timeout(600)
    pg.evaluate("MAP.setView(MARKERS[HL].getLatLng(), 16)"); pg.wait_for_timeout(1800)
    pg.evaluate("document.querySelector('.leaflet-popup-close-button')?.click()"); pg.wait_for_timeout(500)
    pg.locator("#map").screenshot(path="shot_map.png")
    box = pg.evaluate("(() => { const r = document.querySelector('.pin.sel').getBoundingClientRect(); return [r.x, r.y, r.width, r.height] })()")
    x, y, w, h = box; cx, cy = x + w / 2, y + h / 2
    pg.screenshot(path="shot_map2.png", clip={"x": cx - 60, "y": cy - 60, "width": 120, "height": 120}, scale="device")
    print("pin box", box)
    print("errors:", errs, "sel:", pg.locator(".pin.sel").count())
    b.close()
srv.kill()
