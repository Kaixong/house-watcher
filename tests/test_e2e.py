"""模擬兩次每週執行，驗證新物件/降價判斷、儀表板資料、信件內容。"""
import json, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import run
from scraper import sale591, newhouse591, notify

tmp = Path(tempfile.mkdtemp())
run.STATE, run.DASH_DATA = tmp / "listings.json", tmp / "data.json"
sent = []
notify_send = lambda s, b, log=print: sent.append((s, b)) or True
run.send_email = notify_send
run.realprice.enrich = lambda *a, **k: None  # 行情另有測試
cfg = tmp / "config.yaml"
cfg.write_text("""searches:
  - {name: 測試中古屋, type: sale, url: "https://sale.591.com.tw/?regionid=1", filters: {max_price: 3000, exclude_keywords: [頂加]}}
  - {name: 測試新建案, type: newhouse, url: "https://newhouse.591.com.tw/list?regionid=1"}
notify: {email: true}
""", "utf-8")

def item(i, price, ping=30, age=10, title="內湖三房"):
    return {"source":"591中古屋","id":f"sale-{i}","title":f"{title}{i}","url":"u","image":"","price":price,
            "unit_price":round(price/ping,1),"ping":ping,"layout":"3房2廳2衛","age":age,"floor":"5F/10F",
            "kind":"電梯大樓","community":"","district":"內湖區","address":"成功路","tags":[],"poster":""}
week = [
    [item(1, 2500), item(2, 2800), item(3, 3500)],                 # 3 超過預算
    [item(1, 2400), item(2, 2800), item(4, 2600), item(5, 2000, title="頂加")],  # 1 降價, 4 新, 2 還在, 5 排除
]
nh = [newhouse591.normalize({"hid":1,"build_name":"A建案","price":"85~95","price_unit":"萬/坪","section":"中山區"})]
for w in range(2):
    sale591.scrape = lambda *a, **k: week[w]
    newhouse591.scrape = lambda *a, **k: nh
    sys.argv = ["run.py", "--config", str(cfg)]
    run.main()

d = json.loads(run.DASH_DATA.read_text("utf-8"))
by = {i["id"]: i for i in d["items"]}
assert "sale-3" not in by and "sale-5" not in by
assert by["sale-4"]["is_new"] and not by["sale-2"]["is_new"]
assert by["sale-1"]["prev_price"] == 2500 and by["sale-1"]["price_history"][-1][1] == 2400
assert by["new-1"]["active"] and by["new-1"]["unit_price"] == 85
assert len(sent) == 2 and "已啟動" in sent[0][0] and "1 筆新物件、1 筆降價" in sent[1][0], [s for s,_ in sent]
Path("tests/sample_email.html").write_text(sent[1][1], "utf-8")
shutil.copy(run.DASH_DATA, "tests/sample_data.json")
print("E2E OK:", sent[1][0])
