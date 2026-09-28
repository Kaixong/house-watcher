# 🏠 房房小助手

每週自動抓取 591 **中古屋**與**新建案**中符合你條件的物件：
- 比對上週結果，找出**新上架**與**降價**的物件
- 更新一個網頁儀表板（GitHub Pages）
- 寄 Gmail 通知給你
- 每週一早上 07:52（台北時間）自動執行，也可以隨時手動觸發

```
config.yaml ─► run.py ─┬─ scraper/sale591.py      （Playwright 開瀏覽器抓中古屋）
                       ├─ scraper/newhouse591.py  （直接呼叫新建案 JSON API）
                       ├─ scraper/filters.py      （額外篩選條件）
                       ├─ data/listings.json      （歷史紀錄，用來判斷新物件/降價）
                       ├─ docs/data.json ─► docs/index.html（儀表板）
                       └─ scraper/notify.py ─► Gmail
```

---

## 一、設定步驟（約 15 分鐘）

### 1. 建立 GitHub repo
1. 登入 GitHub，右上角 **+ → New repository**，名稱例如 `house-watcher`。
   - 選 **Private** 也可以，但 GitHub Pages 需要付費方案才能讓 private repo 開放網頁；想免費用儀表板請選 **Public**。（物件都是公開資料，Gmail 密碼放在 Secrets 不會外洩。）
2. 把這個資料夾的所有檔案上傳（可以直接在網頁上 **Add file → Upload files** 拖進去，記得包含 `.github` 資料夾）。
   > 網頁上傳時隱藏資料夾 `.github` 可能被略過。若是如此，在 repo 裡 **Add file → Create new file**，檔名輸入 `.github/workflows/weekly.yml`，把內容貼上即可。

### 2. 取得 Gmail 應用程式密碼
1. 到 Google 帳戶 → **安全性** → 開啟 **兩步驟驗證**（必須先開）。
2. 到 <https://myaccount.google.com/apppasswords>，名稱輸入「house-watcher」，按建立。
3. 會得到一組 16 碼密碼（例如 `abcd efgh ijkl mnop`），先複製起來。

### 3. 把密碼放進 GitHub Secrets
repo 頁面 → **Settings → Secrets and variables → Actions → New repository secret**，新增：

| Name | Value |
|---|---|
| `GMAIL_USER` | 你的 Gmail，例如 `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | 上一步的 16 碼密碼 |
| `MAIL_TO` | （可選）收件者，多人用逗號分隔；不填就寄給自己 |

### 4. 開啟 GitHub Pages（儀表板）
**Settings → Pages** → Source 選 **Deploy from a branch** → Branch 選 `main`、資料夾選 `/docs` → Save。
約一分鐘後網址會出現，例如 `https://你的帳號.github.io/house-watcher/`。
把這個網址填回 `config.yaml` 的 `dashboard_url`，信件就會附上連結。

### 5. 第一次執行
repo → **Actions** → 左邊點「每週抓取房屋物件」→ 右邊 **Run workflow**。
約 3–5 分鐘跑完。**第一次執行會把目前所有符合的物件當作基準**，寄一封「已啟動」信；之後每週只通知新物件和降價。

---

## 二、日常使用

### 修改搜尋條件（不用寫程式，在 GitHub 網頁上改就好）
1. 打開儀表板，按右上角「修改條件」（或直接開 `https://github.com/你的帳號/house-watcher/edit/main/config.yaml`）
2. 到 591 網站用它的篩選器設好條件 → 複製網址列 → 貼到 `url:` 後面的引號裡
   - 中古屋：`https://sale.591.com.tw/?...`
   - 新建案：`https://newhouse.591.com.tw/list?...`
3. 591 篩不到的條件寫在 `filters:`（總價、坪數、單價、屋齡上限、關鍵字包含/排除）
4. 按右上角綠色的 **Commit changes** 存檔
5. **存檔後會自動重跑一次**（約 3–5 分鐘），跑完儀表板就會更新

小提醒：YAML 對縮排很敏感，請維持原本的空格對齊；想新增一組條件，複製整段 `- name: ...` 貼在下面再改內容即可。
也可以直接跟 Claude 說想要的條件，請它幫你改。

### 行情比較（實價登錄）
每個在架物件會自動查兩種行情，儀表板點「行情走勢」可看圖表與成交明細：
- **同社區**：591 實價登錄的該社區成交紀錄（最精準，中古屋大多有）
- **附近類似**：內政部實價登錄開放資料，依序找「同路段、同建物型態、坪數 ±35%、屋齡 ±10 年」，筆數不夠再放寬到同行政區
- 「比行情貴/便宜 X%」= 開價單價 ÷ 行情中位數。基準優先順序：同社區近一年 → 同社區近兩年 → 附近近一年
- 單價都已扣除車位；行情僅供參考

### 手動觸發
- 儀表板的「▶ 立即重新抓取」→ 會開到 GitHub Actions 頁面 → 按 **Run workflow**
- 可取消勾選「是否寄送 Gmail 通知」只更新儀表板

### 在自己電腦上跑（測試或備援）
```bash
pip install -r requirements.txt
python -m playwright install chromium
python run.py --no-email          # 不寄信
python run.py --show --no-email   # 顯示瀏覽器視窗，方便看哪裡卡住
```
要在本機寄信，先設定環境變數 `GMAIL_USER`、`GMAIL_APP_PASSWORD`。

---

## 三、常見問題

**信裡出現「沒有抓到任何資料」的警告？**
591 有反爬蟲機制，GitHub 的主機在美國，有機會被擋。處理順序：
1. 先到 Actions 手動再跑一次（偶發失敗很常見）
2. 在自己電腦跑 `python run.py --show --no-email` 確認網址條件是否正確
3. 若確定只有 GitHub 上會被擋，可改在自己電腦用「工作排程器」(Windows) 或 `cron` (Mac) 每週執行 `python run.py`，並把 `data/`、`docs/data.json` push 回 GitHub

**591 改版後抓不到？**
中古屋卡片的欄位定義在 `scraper/sale591.py` 最上面的 `EXTRACT_JS`（CSS class 如 `.ware-item`、`.ware-item__price-value`），改版時通常只要更新這幾個名稱。

**使用須知**
本工具僅供個人找房使用。程式每頁之間都有數秒延遲、每週只跑一次，請勿調高頻率或大量抓取，並尊重網站的使用條款。

---

## 四、之後可以加的功能
- 樂居、信義、永慶等其他來源（新增一個 `scraper/xxx.py`，回傳相同欄位即可）
- 用物件詳情頁的「主建物坪數」做更精準的行情比對
- LINE 官方帳號（Messaging API）推播
