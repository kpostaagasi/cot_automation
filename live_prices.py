"""Canlı fiyat modülü: Yahoo Finance. Hata durumunda sabit fiyata düşer."""
import requests, warnings

UA = {"User-Agent": "Mozilla/5.0"}

# (yahoo sembol, dönüşüm) ; dönüşüm: None | 'div100' | 'inv'
PRICE_MAP = {
    "067651": ("CL=F", None), "023651": ("NG=F", None), "088691": ("GC=F", None),
    "084691": ("SI=F", None), "085692": ("HG=F", None), "002602": ("ZC=F", "div100"),
    "099741": ("EURUSD=X", None), "097741": ("JPY=X", "inv"), "096742": ("GBPUSD=X", None),
    "232741": ("AUDUSD=X", None), "090741": ("CAD=X", "inv"), "095741": ("MXN=X", "inv"),
    "13874A": ("ES=F", None), "209742": ("NQ=F", None), "239742": ("RTY=F", None),
}

def _last_close(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "5d", "interval": "1d"}, headers=UA, timeout=20)
    r.raise_for_status()
    closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    closes = [c for c in closes if c is not None]
    if not closes:
        raise ValueError("close yok")
    return float(closes[-1])

def get_live_price(code, fallback):
    """(fiyat, kaynak) döner. Tahviller map'te yok -> par (fallback)."""
    if code not in PRICE_MAP:
        return fallback, "par"
    sym, conv = PRICE_MAP[code]
    try:
        p = _last_close(sym)
        if conv == "div100": p /= 100.0
        elif conv == "inv": p = 1.0 / p
        return p, "canlı"
    except Exception as e:
        warnings.warn(f"[live_prices] {sym} alınamadı ({e}); sabit fiyat {fallback} kullanılıyor")
        return fallback, "sabit"
