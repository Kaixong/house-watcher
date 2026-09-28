import subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(["python", "-m", "http.server", "8770", "-d", "site"]); time.sleep(1)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:8770/"); pg.wait_for_timeout(2500)
    pg.screenshot(path="shot_list.png")
    pg.click("#vMap"); pg.wait_for_timeout(3500)
    pg.locator(".pin").nth(5).click(force=True); pg.wait_for_timeout(800)
    pg.screenshot(path="shot_map.png")
    mp = b.new_page(viewport={"width": 390, "height": 844}); mp.goto("http://localhost:8770/"); mp.wait_for_timeout(2000); mp.screenshot(path="shot_phone.png")
    print("errors:", errs, "pins:", pg.locator(".pin").count(), "leaflet:", pg.evaluate("typeof L"))
    b.close()
srv.kill()
