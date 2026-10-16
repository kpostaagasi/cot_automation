"""Haftalık COT raporu, onaylı gönderim.
  python send_weekly.py prepare  -> raporu üretir, out/ klasörüne yazar, önizlemeyi SADECE SMTP_USER'a yollar
  python send_weekly.py send     -> out/ içindeki onaylanmış paketi ekibe yollar (yeniden üretmez)
Ortam: SMTP_USER, SMTP_PASS (Gmail App Password), MAIL_TO (virgülle), MAIL_CC (opsiyonel)
"""
import os, sys, ssl, smtplib, datetime as dt, traceback
import json, glob
from email.message import EmailMessage
from cot_report import main as build, fmt_notional

USER = os.environ["SMTP_USER"]; PWD = os.environ["SMTP_PASS"]
TO = [x.strip() for x in os.environ["MAIL_TO"].split(",") if x.strip()]
CC = [x.strip() for x in os.environ.get("MAIL_CC", "").split(",") if x.strip()]
MAX_AGE_DAYS = 11  # son COT haftası bundan eskiyse (yayın gecikmesi) ekibe gönderme

def send(to, subject, html, text, attach=None, cc=(), inline=()):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = USER, ", ".join(to), subject
    if cc: m["Cc"] = ", ".join(cc)
    m.set_content(text); m.add_alternative(html, subtype="html")
    for path in inline:  # gövdeye gömülü grafikler (cid = dosya adı); PDF eklenmeden önce, HTML parçasına
        with open(path, "rb") as f:
            m.get_payload()[1].add_related(f.read(), maintype="image", subtype="png",
                                           filename=os.path.basename(path), cid=f"<{_cid(path)}>")
    if attach:
        with open(attach, "rb") as f:
            m.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(attach))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(USER, PWD); s.send_message(m)

def _cid(path): return os.path.splitext(os.path.basename(path))[0]

CHART_TITLES = {"tahvil_faizleri": "Tahvil faizleri", "hisse_endeksleri": "Hisse endeksleri"}

def charts_html(paths):
    return "".join(f'<p><b>{CHART_TITLES.get(_cid(p), _cid(p))}:</b><br>'
                   f'<img src="cid:{_cid(p)}" alt="{_cid(p)}" style="width:100%;max-width:760px;border:1px solid #ddd"></p>'
                   for p in paths)

def row(cells, bold=False):
    tag = "th" if bold else "td"
    return "<tr>" + "".join(f'<{tag} style="border:1px solid #ddd;padding:4px 8px;text-align:left">{c}</{tag}>' for c in cells) + "</tr>"

OUT = "out"

def prepare():
    week = dt.date.today()
    os.makedirs(OUT, exist_ok=True)
    fname = os.path.join(OUT, f"BV_Portfoy_CFTC_COT_{week:%Y%m%d}.pdf")
    try:
        s = build(fname)
    except Exception:
        send([USER], "[HATA] CFTC COT raporu üretilemedi", f"<pre>{traceback.format_exc()}</pre>", traceback.format_exc())
        raise
    latest = s["latest"].date()
    age = (week - latest).days
    if age > MAX_AGE_DAYS:
        msg = f"Son COT haftası {latest:%d.%m.%Y} ({age} gün önce). CFTC yayını gecikmiş olabilir; ekibe gönderilmedi."
        send([USER], "[UYARI] CFTC COT verisi güncel değil", msg, msg, attach=fname)
        sys.exit(1)  # onay adımı hiç açılmaz

    tbl = row(["Sınıf", "Kontrat", "Net Z", "OI Z", "Net kontrat", "Notional"], True)
    for t, n, c, nz, oz, net, notl in s["anomalies"]:
        tbl += row([t, f"{n} [{c}]", f"{nz:+.2f}", f"{oz:+.2f}", f"{net:+,}".replace(",", "."), fmt_notional(notl)])
    near = "".join(f"<li>{n} ({t}): Net Z {nz:+.2f}, OI Z {oz:+.2f}</li>" for t, n, c, nz, oz in s["near"]) or "<li>Yok</li>"
    stale = ""
    if s["stale_prices"]:
        stale = "<p style='color:#BC1324'>Canlı fiyat alınamayan kontratlar (sabit fiyat kullanıldı): " + \
                ", ".join(p[0] for p in s["stale_prices"]) + "</p>"
    charts = [p for p in s.get("charts", []) if os.path.exists(p)]
    html = f"""<div style="font-family:Arial,sans-serif;font-size:13px;color:#222">
<p>Merhaba,</p>
<p>{latest:%d.%m.%Y} tarihli (Salı pozisyonu) CFTC COT pozisyonlanma raporu ektedir.</p>
<p><b>Sıra dışı konumlanmalar (|Z| ≥ 2):</b></p>
<table style="border-collapse:collapse;font-size:12px">{tbl if s["anomalies"] else row(["Bu hafta eşik aşımı yok"])}</table>
<p><b>Eşiğe yakın (1.75 ≤ |Z| &lt; 2):</b></p><ul>{near}</ul>
{stale}
{charts_html(charts)}
<p style="font-size:11px;color:#777">Z-score: 104 haftalık rolling, kontrat bazında. Emtia: Managed Money, diğerleri: Leveraged Funds.
Notional: Yahoo Finance canlı fiyat, tahviller par. Faizler: FRED CMT; endeksler: Yahoo Finance. Otomatik üretilmiştir.</p>
<p>İyi çalışmalar,<br>Kamil Postaağası</p></div>"""
    text = f"{latest:%d.%m.%Y} tarihli CFTC COT raporu ektedir. Sıra dışı: " + \
           (", ".join(a[1] for a in s["anomalies"]) or "yok")
    subject = f"CFTC COT Pozisyonlanma Raporu | {latest:%d.%m.%Y}"
    json.dump({"subject": subject, "html": html, "text": text, "pdf": os.path.basename(fname),
               "inline": [os.path.basename(p) for p in charts]},
              open(os.path.join(OUT, "mail.json"), "w", encoding="utf-8"), ensure_ascii=False)
    run_url = os.environ.get("RUN_URL", "")
    banner = f"""<div style="background:#FFF5F5;border:1px solid #BC1324;padding:10px;margin-bottom:12px;font-family:Arial">
<b>ONAY BEKLİYOR.</b> Bu mail henüz ekibe gitmedi. Alıcılar: {", ".join(TO)}{(" | CC: " + ", ".join(CC)) if CC else ""}<br>
Göndermek için: <a href="{run_url}">"2 - COT Ekibe Gönder (ONAY)"</a> &gt; Run workflow. Göndermeyeceksen hiçbir şey yapmana gerek yok.</div>"""
    send([USER], "[ONAY BEKLİYOR] " + subject, banner + html, "ONAY BEKLİYOR\n" + run_url + "\n\n" + text, attach=fname, inline=charts)
    print("Önizleme gönderildi (SMTP_USER)")  # public log: adres yazdırma

def send_approved():
    p = json.load(open(os.path.join(OUT, "mail.json"), encoding="utf-8"))
    inline = [os.path.join(OUT, f) for f in p.get("inline", [])]  # eksikse open() hata versin: kırık görsel gitmesin
    send(TO, p["subject"], p["html"], p["text"], attach=os.path.join(OUT, p["pdf"]), cc=CC, inline=inline)
    print(f"Ekibe gönderildi: {len(TO)} alıcı, {len(CC)} CC")  # public log: adres yazdırma

if __name__ == "__main__":
    {"prepare": prepare, "send": send_approved}[sys.argv[1]]()
