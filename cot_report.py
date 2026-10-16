import datetime as dt, requests, numpy as np, pandas as pd, io, os, warnings
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
from live_prices import get_live_price, UA

RED, DARK, GRID = "#BC1324", "#222222", "#F0F0F0"
BASE = "https://publicreporting.cftc.gov/resource/{}.json"
DS = {"COMM": ("kh3c-gbw2", "m_money_positions_long_all", "m_money_positions_short_all", "Managed Money"),
      "TFF":  ("yw9f-hn96", "lev_money_positions_long", "lev_money_positions_short", "Leveraged Funds")}

# ad, kod, çarpan, sabit fiyat (fallback)
PAGES = [
 ("Emtialar", "COMM", [("WTI Crude Oil","067651",1000,70.0),("Natural Gas","023651",10000,3.0),
   ("Gold","088691",100,2300.0),("Silver","084691",5000,28.0),("Copper","085692",25000,4.5),
   ("Corn","002602",5000,4.5),("Wheat (SRW)","001602",5000,5.5)]),
 ("Döviz", "TFF", [("Euro FX","099741",125000,1.08),("Japanese Yen","097741",12500000,0.0067),
   ("British Pound","096742",62500,1.27),("Australian Dollar","232741",100000,0.66),
   ("Canadian Dollar","090741",100000,0.73),("Mexican Peso","095741",500000,0.055)]),
 ("Hisse Endeksleri", "TFF", [("E-mini S&P 500","13874A",50,5200.0),("E-mini Nasdaq-100","209742",20,18000.0),
   ("Russell 2000 E-mini","239742",50,2050.0)]),
 ("Tahviller", "TFF", [("UST 2Y","042601",2000,100.0),("UST 5Y","044601",1000,100.0),("UST 10Y","043602",1000,100.0),
   ("UST Bond","020601",1000,100.0),("Ultra Bond","020604",1000,100.0)]),
]
LOGO = plt.imread(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bv_logo_white.png"))
WIN, MINP, THR, VIEW_START = 104, 52, 2.0, "2023-01-01"

# Grafik arkası overlay'ler. Tahvil: kontratın teslim sepetine karşılık gelen CMT yield (FRED, sağ eksen %).
# CME sepetleri (kalan vade): 2Y 1y9m-2y, 5Y 4y2m-5y3m, 10Y 6.5-10y, Bond 15-<25y, Ultra >=25y.
# FRED'de 15Y/25Y CMT yok -> Bond = 20Y, Ultra = 30Y proxy.
YIELD_MAP = {"042601": ("DGS2", "2Y"), "044601": ("DGS5", "5Y"), "043602": ("DGS10", "10Y"),
             "020601": ("DGS20", "20Y"), "020604": ("DGS30", "30Y")}
YIELD_COLOR = {"DGS2": "#1F77B4", "DGS5": "#2CA02C", "DGS10": "#FF7F0E", "DGS20": "#9467BD", "DGS30": "#8C564B"}
EQUITY = {"^GSPC": ("S&P 500", "#0A9396"), "^NDX": ("Nasdaq-100", "#6A4C93"), "^RUT": ("Russell 2000", "#B5651D")}
# Hisse endeksi kontratları -> spot endeks (arka plan)
EQUITY_MAP = {"13874A": "^GSPC", "209742": "^NDX", "239742": "^RUT"}

_cache = {}

def fred_series(fid):
    if ("fred", fid) not in _cache:
        # NOT: FRED 'Mozilla/5.0' UA'sını sessizce read-timeout yapar -> headers gönderme
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                         params={"id": fid, "cosd": VIEW_START}, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        s = pd.Series(pd.to_numeric(df[fid], errors="coerce").values, index=pd.to_datetime(df["observation_date"])).dropna()
        if s.empty: raise RuntimeError(f"FRED {fid} boş döndü")
        _cache[("fred", fid)] = s
    return _cache[("fred", fid)]

def yahoo_series(sym):
    if ("yh", sym) not in _cache:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", headers=UA, timeout=30,
                         params={"period1": int(pd.Timestamp(VIEW_START).timestamp()), "period2": int(dt.datetime.now().timestamp()),
                                 "interval": "1d"})
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        s = pd.Series(res["indicators"]["quote"][0]["close"],
                      index=pd.to_datetime(res["timestamp"], unit="s").normalize()).dropna()
        if s.empty: raise RuntimeError(f"Yahoo {sym} boş döndü")
        _cache[("yh", sym)] = s
    return _cache[("yh", sym)]

def add_overlays(ax, code, title, bg):
    """Z-score paneline arka plan serileri: tahvilde yield (sağ eksen %) + S&P 500, hissede spot endeks.
    Z-score ekseni üstte kalır; panel arka plan rengi en alttaki twin eksene taşınır."""
    specs = []  # (seri, etiket, renk, stil, sağ eksen etiketi göster)
    if code in YIELD_MAP:
        fid, lbl = YIELD_MAP[code]
        y = fred_series(fid)
        specs.append((y, f"{lbl} UST yield (sağ, son %{y.iloc[-1]:.2f})", YIELD_COLOR[fid], "-", True))
        sym = "^GSPC"
    else:
        sym = EQUITY_MAP.get(code)
    if sym:
        e = yahoo_series(sym); lbl, col = EQUITY[sym]
        specs.append((e, f"{lbl} (arka, son {e.iloc[-1]:,.0f})".replace(",", "."), col, "-.", not specs))
    if not specs: return []
    handles, twins = [], []
    for s, lbl, col, ls, show in specs:
        tw = ax.twinx(); twins.append(tw)
        s = s[s.index >= VIEW_START]
        h, = tw.plot(s.index, s.values, color=col, lw=1.0, ls=ls, alpha=.85, label=lbl)
        handles.append(h)
        pad = (s.max() - s.min()) * .08; tw.set_ylim(s.min() - pad, s.max() + pad)
        for sp in tw.spines.values(): sp.set_visible(False)
        if show:
            tw.tick_params(labelsize=5.5, colors=col, length=2)
            if code in YIELD_MAP: tw.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"%{v:.1f}"))
        else:
            tw.set_yticks([])
    for k, tw in enumerate(twins):  # en alttaki twin panel rengini taşır, Z-score ekseni en üstte
        tw.set_zorder(k * .1); tw.patch.set_visible(k == 0)
    twins[0].set_facecolor(bg)
    ax.set_zorder(1); ax.patch.set_visible(False)
    return handles

def fetch(kind, codes):
    ds, lc, sc, _ = DS[kind]
    inlist = ",".join(f"'{c}'" for c in codes)
    r = requests.get(BASE.format(ds), timeout=120, params={
        "$select": f"report_date_as_yyyy_mm_dd,cftc_contract_market_code,{lc},{sc},open_interest_all",
        "$where": f"report_date_as_yyyy_mm_dd >= '2016-01-01' AND cftc_contract_market_code IN ({inlist})",
        "$order": "report_date_as_yyyy_mm_dd", "$limit": 50000})
    if r.status_code != 200:  # sessiz hata yok
        raise RuntimeError(f"{ds} HTTP {r.status_code}: {r.text[:300]}")
    df = pd.DataFrame(r.json())
    if df.empty: raise RuntimeError(f"{ds} boş döndü")
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    for c in (lc, sc, "open_interest_all"): df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.rename(columns={"cftc_contract_market_code": "code"})
    df = df.groupby(["code", "date"], as_index=False)[[lc, sc, "open_interest_all"]].sum()
    df["net"] = df[lc] - df[sc]; df["oi"] = df["open_interest_all"]
    df = df.sort_values(["code", "date"])
    g = df.groupby("code")
    for s in ("net", "oi"):
        m = g[s].transform(lambda x: x.rolling(WIN, min_periods=MINP).mean())
        sd = g[s].transform(lambda x: x.rolling(WIN, min_periods=MINP).std())
        df[f"{s}_z"] = (df[s] - m) / sd
    return df

NOTES = {
 "Tahviller": "\nArka plan: FRED CMT yield, sağ eksen (teslim sepeti kalan vade: 2Y 1y9m–2y, 5Y 4y2m–5y3m, 10Y 6.5–10y, Bond 15–<25y → 20Y proxy, "
              "Ultra ≥25y → 30Y proxy) ve S&P 500 (Yahoo, kendi ölçeğinde, eksensiz).",
 "Hisse Endeksleri": "\nArka plan: kontratın spot endeksi (Yahoo Finance; S&P 500, Nasdaq-100, Russell 2000), kendi ölçeğinde, eksensiz.",
}

def render_email_charts(outdir):
    """Mail gövdesi için tahvil faizi + hisse endeksi PNG'leri; üretilen dosya yollarını döner."""
    paths = []
    def _fig(title):
        fig, ax = plt.subplots(figsize=(9, 3.2), dpi=110)
        ax.grid(color=GRID, lw=.6); ax.tick_params(labelsize=7, colors=DARK)
        for sp in ax.spines.values(): sp.set_color("#CCCCCC")
        ax.set_title(title, fontsize=9, loc="left", weight="bold", color=DARK)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
        return fig, ax
    def _save(fig, ax, fn, ncol):
        ax.legend(ncol=ncol, fontsize=7.5, frameon=False, loc="upper left")
        fig.tight_layout(); p = os.path.join(outdir, fn); fig.savefig(p); plt.close(fig); paths.append(p)

    fig, ax = _fig(f"ABD Tahvil Faizleri (FRED CMT, günlük, %) | {VIEW_START[:4]}+")
    for fid, lbl in YIELD_MAP.values():
        y = fred_series(fid)
        ax.plot(y.index, y.values, color=YIELD_COLOR[fid], lw=1.2, label=f"{lbl}  %{y.iloc[-1]:.2f}")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"%{v:.1f}"))
    _save(fig, ax, "tahvil_faizleri.png", 5)

    fig, ax = _fig(f"Hisse Endeksleri (Yahoo Finance, {VIEW_START[:4]} başı = 100)")
    for sym, (lbl, col) in EQUITY.items():
        e = yahoo_series(sym); r = 100 * e / e.iloc[0]
        ax.plot(r.index, r.values, color=col, lw=1.2, label=f"{lbl}  {e.iloc[-1]:,.0f} ({r.iloc[-1]-100:+.0f}%)".replace(",", "."))
    ax.axhline(100, color=DARK, lw=.6)
    _save(fig, ax, "hisse_endeksleri.png", 3)
    return paths

def fmt_notional(v):
    s = "-" if v < 0 else "+"
    return f"{s}${abs(v)/1e9:.2f}B" if abs(v) >= 1e9 else f"{s}${abs(v)/1e6:.0f}M"

def main(out_path="BV_Portfoy_CFTC_COT_Advanced_Report.pdf"):
    today = dt.date.today()
    data, rowcheck, anomalies, prices = {}, [], [], []
    for title, kind, ks in PAGES:
        df = fetch(kind, [k[1] for k in ks])
        data[title] = df
        for name, code, *_ in ks:
            n = (df.code == code).sum(); rowcheck.append((title, name, code, n))
    latest = max(d.date.max() for d in data.values())

    with PdfPages(out_path) as pdf:
        for title, kind, ks in PAGES:
            df = data[title]; cat = DS[kind][3]
            fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
            fig.patches.append(plt.Rectangle((0, .925), 1, .075, transform=fig.transFigure, color=RED, zorder=0))
            fig.text(.02, .968, f"CFTC COT Pozisyonlanma | {title} ({cat})", color="white", fontsize=15, weight="bold", va="center")
            fig.text(.02, .938, f"Rolling Z-Score ({WIN} hafta, min {MINP}) | Kalibrasyon: 2016+ | Görünüm: 2023+ | Anomali: |Net Z| veya |OI Z| ≥ {THR}",
                     color="white", fontsize=8.5, va="center")
            h = .042; w = h * LOGO.shape[1] / LOGO.shape[0] * (8.27 / 11.69)
            lax = fig.add_axes([.98 - w, .9625 - h / 2, w, h]); lax.imshow(LOGO, interpolation="antialiased"); lax.axis("off"); lax.set_zorder(10)
            nrow = -(-len(ks) // 2)   # 2 kolon, kontrat sayısına göre satır
            gs = fig.add_gridspec(nrow, 2, left=.05, right=.98, top=.88, bottom=.09, hspace=.62, wspace=.12)
            for i in range(nrow * 2):
                ax = fig.add_subplot(gs[i // 2, i % 2])
                if i >= len(ks): ax.axis("off"); continue
                name, code, mult, fb = ks[i]
                d = df[(df.code == code)].dropna(subset=["net_z"])
                d = d[d.date >= VIEW_START]
                ax.set_facecolor("white"); ax.grid(color=GRID, lw=.6)
                for sp in ax.spines.values(): sp.set_color("#CCCCCC")
                ax.set_ylim(-3.2, 3.2); ax.tick_params(labelsize=6, colors=DARK)
                if len(d) < 10:
                    ax.set_title(f"{name} [{code}]", fontsize=8, color=DARK, weight="bold")
                    ax.text(.5, .5, "Yetersiz / Eksik Veri", ha="center", transform=ax.transAxes, color="grey"); continue
                last = d.iloc[-1]
                price, src = get_live_price(code, fb)
                notional = last.net * mult * price
                prices.append((name, price, fb, src))
                flag = abs(last.net_z) >= THR or abs(last.oi_z) >= THR
                if flag:
                    ax.set_facecolor("#FFF5F5")
                    anomalies.append((title, name, code, last.net_z, last.oi_z, int(last.net), notional))
                x, z = d.date, d.net_z
                ax.fill_between(x, 0, z, where=z >= 0, color="green", alpha=.12, interpolate=True)
                ax.fill_between(x, 0, z, where=z < 0, color=RED, alpha=.12, interpolate=True)
                ax.plot(x, z, color=RED, lw=1.1, label="Net Pozisyon Z-Score")
                ax.plot(x, d.oi_z, color="#777777", lw=.9, ls="--", label="Open Interest Z-Score")
                ax.axhline(0, color=DARK, lw=.6)
                for t in (THR, -THR): ax.axhline(t, color=RED, lw=.7, ls=":")
                extra = []
                try:
                    extra = add_overlays(ax, code, title, ax.get_facecolor())
                except Exception as e:
                    warnings.warn(f"[cot_report] {name} arka plan serisi alınamadı: {e}")
                ax.set_xlim(x.min(), x.max())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
                hs = ax.get_legend_handles_labels()[0] + extra
                ax.legend(handles=hs, loc="lower left", ncol=2, fontsize=5 if len(hs) <= 2 else 4.5, frameon=False)
                tag = " [SIRA DIŞI]" if flag else ""
                ax.set_title(f"{name} [{code}]{tag}\nNet Z: {last.net_z:+.2f} | OI Z: {last.oi_z:+.2f} | "
                             f"Net: {int(last.net):+,} kontrat ({fmt_notional(notional)})".replace(",", "."),
                             fontsize=7.5, color=RED if flag else DARK, weight="bold", loc="left")
            fig.text(.02, .035, f"Metodoloji: net = long − short ({cat}); Z = (x − μ{WIN}h) / σ{WIN}h, kontrat bazında. "
                     f"Notional = net × çarpan × fiyat. Fiyat: Yahoo Finance (canlı; corn/wheat ÷100, JPY/CAD/MXN 1/x), tahvil = par (100)." +
                     NOTES.get(title, ""), fontsize=6.5 if title not in NOTES else 5.6, color=DARK)
            fig.text(.02, .018, f"Kaynak: CFTC Public Reporting API | Son COT haftası: {latest:%d.%m.%Y} (Salı pozisyonu) | "
                     f"Rapor tarihi: {today:%d.%m.%Y}", fontsize=6.5, color=DARK)
            fig.text(.98, .018, "BV Portföy Fon Yönetimi", fontsize=6.5, color=RED, ha="right", weight="bold")
            pdf.savefig(fig); plt.close(fig)

    try:  # mail gövdesi grafikleri (best-effort: alınamazsa mail grafiksiz gider)
        charts = render_email_charts(os.path.dirname(os.path.abspath(out_path)))
    except Exception as e:
        charts = []; warnings.warn(f"[cot_report] Mail grafikleri üretilemedi: {e}")

    # Doğrulama çıktıları
    bad = [x for x in rowcheck if x[3] < 400]
    if bad:
        raise RuntimeError(f"Satır sayısı doğrulaması başarısız: {bad}")
    near = []
    for title, _, ks in PAGES:
        d = data[title]; last = d[d.date == d.date.max()]
        names = {k[1]: k[0] for k in ks}
        for _, r in last.iterrows():
            if not any(a[2] == r.code for a in anomalies) and (1.75 <= abs(r.net_z) < THR or 1.75 <= abs(r.oi_z) < THR):
                near.append((title, names[r.code], r.code, r.net_z, r.oi_z))
    summary = dict(latest=latest, anomalies=anomalies, near=near, rowcheck=rowcheck,
                   stale_prices=[p for p in prices if p[3] == "sabit"], path=out_path, charts=charts)
    print("SON COT HAFTASI:", latest.date())
    print("\nSATIR SAYISI"); [print(f"  {t:17s} {n:20s} {c}  {r}") for t, n, c, r in rowcheck]
    bad = [x for x in rowcheck if x[3] < 400]
    print("  UYARI düşük satır: yok")
    print("\nFİYATLAR (canlı vs sabit)")
    for n, p, fb, s in prices: print(f"  {n:20s} {p:12.5f} {fb:12.5f} {s:6s} sapma {100*(p/fb-1):+.0f}%")
    print("\nANOMALİLER")
    for a in anomalies: print(f"  {a[0]:17s} {a[1]:20s} NetZ {a[3]:+.2f} OIZ {a[4]:+.2f} net {a[5]:+,} {fmt_notional(a[6])}")
    for title, _, ks in PAGES:
        d = data[title]
        z = d[(d.date == d.date.max())].set_index("code")[["net_z", "oi_z"]]
        print(f"\n{title} son hafta Z:\n", z.round(2).to_string())
    return summary

if __name__ == "__main__":
    main()
