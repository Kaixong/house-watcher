"""Gmail 通知：用 Gmail SMTP + 應用程式密碼寄信。

需要的環境變數（在 GitHub 放 Secrets）：
  GMAIL_USER          寄件的 Gmail 帳號
  GMAIL_APP_PASSWORD  Gmail「應用程式密碼」（16 碼，不是登入密碼）
  MAIL_TO             收件者，可多個，用逗號分隔（沒填就寄給自己）
"""
from __future__ import annotations

import html
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _fmt_price(it: dict) -> str:
    if it.get("price"):
        s = f"{it['price']:,.0f} 萬"
        if it.get("unit_price"):
            s += f"（{it['unit_price']:g} 萬/坪）"
        return s
    return it.get("price_text") or "—"


def _card(it: dict, badge: str) -> str:
    e = html.escape
    meta = " · ".join(
        x for x in [
            it.get("district", ""),
            it.get("layout", "")[:30],
            f"權狀 {it['ping']:g} 坪" if it.get("ping") else it.get("ping_text", ""),
            f"{it.get('main_ping_note') or '主建'} {it['main_ping']:g} 坪" if it.get("main_ping") else "",
            f"屋齡 {it['age']:g} 年" if it.get("age") is not None else "",
            it.get("floor", ""),
        ] if x
    )
    drop = ""
    if it.get("prev_price"):
        drop = (f'<span style="color:#0a7d3b">　↓ 原 {it["prev_price"]:,.0f} 萬</span>')
    mk = ""
    m = it.get("market") or {}
    if m.get("premium") is not None:
        p = m["premium"]
        color, word = ("#9a5b00", f"比行情貴 {p}%") if p > 3 else (("#1d7a45", f"比行情便宜 {abs(p)}%") if p < -3 else ("#2f3e8f", f"接近行情（{p:+}%）"))
        mk = (f'<br><span style="font-size:13px;color:{color};font-weight:600">{e(word)}</span>'
              f'<span style="font-size:12px;color:#888">　{e(m.get("ref_label", ""))}中位數 {m.get("ref_price")} 萬/坪</span>')
    d = it.get("detail") or {}
    dl = " ｜ ".join(x for x in [f"車位：{d['parking']}" if d.get("parking") else "",
                                 f"交通：{'、'.join(d.get('traffic', [])[:3])}" if d.get("traffic") else ""] if x)
    if dl:
        mk += f'<br><span style="font-size:12px;color:#555">{e(dl)}</span>'
    img = (f'<img src="{e(it["image"])}" width="120" height="90" '
           f'style="object-fit:cover;border-radius:6px;display:block">' if it.get("image") else "")
    return f"""
<tr><td style="padding:10px 0;border-bottom:1px solid #eee;vertical-align:top;width:130px">{img}</td>
<td style="padding:10px 0 10px 12px;border-bottom:1px solid #eee;vertical-align:top;font-family:sans-serif">
  <span style="background:#d9480f;color:#fff;font-size:11px;padding:2px 6px;border-radius:4px">{badge}</span>
  <span style="font-size:12px;color:#888">　{e(it.get('source',''))}</span><br>
  <a href="{e(it['url'])}" style="font-size:15px;font-weight:600;color:#1a1a1a;text-decoration:none">{e(it.get('title',''))}</a><br>
  <span style="font-size:15px;color:#d9480f;font-weight:600">{e(_fmt_price(it))}</span>{drop}{mk}<br>
  <span style="font-size:13px;color:#555">{e(meta)}</span><br>
  <span style="font-size:12px;color:#888">{e(it.get('address',''))}</span>
</td></tr>"""


def build_email(new_items, drops, warnings, dashboard_url, max_items=30, summary=None) -> tuple[str, str]:
    if new_items or drops:
        subject = f"🏠 房房小助手：{len(new_items)} 筆新物件"
        if drops:
            subject += f"、{len(drops)} 筆降價"
    else:
        subject = "🏠 房房小助手：本次沒有新物件或降價"
    rows = "".join(_card(it, "NEW") for it in new_items[:max_items])
    rows += "".join(_card(it, "降價") for it in drops[:max_items])
    more = ""
    if len(new_items) > max_items:
        more = f"<p>…還有 {len(new_items) - max_items} 筆，請到儀表板查看。</p>"
    warn = ""
    if warnings:
        warn = ('<div style="background:#fff4e5;padding:10px;border-radius:6px;font-size:13px">⚠ '
                + "<br>⚠ ".join(html.escape(w) for w in warnings) + "</div>")
    link = (f'<p><a href="{html.escape(dashboard_url)}">打開儀表板 →</a></p>' if dashboard_url else "")
    if summary:
        link = (f'<p style="font-size:14px;color:#333">目前符合條件 <b>{summary["active"]}</b> 筆・'
                f'近 7 天新物件 <b>{summary["week_new"]}</b> 筆・降價中 <b>{summary["drops"]}</b> 筆</p>') + link
    body = f"""<div style="max-width:640px;font-family:sans-serif">
<h2 style="margin:0 0 8px">本週符合條件的物件</h2>{warn}{link}
<table cellspacing="0" cellpadding="0" style="width:100%">{rows or '<tr><td style="font-family:sans-serif;padding:12px 0">這次執行沒有新上架或降價的物件，可以到儀表板看全部物件。</td></tr>'}</table>
{more}<p style="font-size:12px;color:#999">此信由 GitHub Actions 自動寄出</p></div>"""
    return subject, body


def send_email(subject: str, html_body: str, log=print) -> bool:
    user = os.environ.get("GMAIL_USER", "").strip()
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = [x.strip() for x in (os.environ.get("MAIL_TO") or user).split(",") if x.strip()]
    if not user or not pwd:
        log("  （未設定 GMAIL_USER / GMAIL_APP_PASSWORD，略過寄信）")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, user, ", ".join(to)
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pwd)
        s.sendmail(user, to, msg.as_string())
    log(f"  ✉ 已寄信給 {', '.join(to)}")
    return True
