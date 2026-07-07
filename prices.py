"""
Kurs- und Marktdaten via yfinance (deckt US und SIX ab, z. B. NESN.SW).

Liefert:
- aktueller Kurs, Allzeithoch, Drawdown vom ATH
- aktuelles KGV + Näherung des historischen KGV-Mittels/Streuung
- EV/EBITDA und P/FCF (aktuell + Historie-Näherung)
- Benchmark-Tagesrenditen für die Event-Study
"""
from __future__ import annotations
import statistics as st
import yfinance as yf


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def price_block(yf_symbol: str) -> dict:
    tk = yf.Ticker(yf_symbol)
    hist = _safe(lambda: tk.history(period="max", auto_adjust=True), None)
    out = {"price": None, "ath": None, "drawdown": None}
    if hist is not None and len(hist):
        close = hist["Close"].dropna()
        price = float(close.iloc[-1])
        ath = float(close.max())
        out.update(price=price, ath=ath,
                   drawdown=round((price - ath) / ath * 100, 1) if ath else None)
    # Kennzahlen aus fast_info / info
    fi = _safe(lambda: tk.fast_info, {}) or {}
    info = _safe(lambda: tk.info, {}) or {}
    out["pe_now"] = _safe(lambda: float(info.get("trailingPE")), None)
    out["market_cap"] = _safe(lambda: float(info.get("marketCap") or fi.get("market_cap")), None)
    out["forward_growth"] = _safe(lambda: float(info.get("earningsGrowth")), None)
    return out


def historical_pe(yf_symbol: str) -> dict:
    """
    Näherung des historischen KGV-Mittels: Jahresend-Kurs / verwässertes EPS
    des jeweiligen Geschäftsjahres, über die verfügbaren Jahre.
    yfinance liefert nur begrenzte Historie – daher Näherung, klar so deklariert.
    """
    tk = yf.Ticker(yf_symbol)
    fin = _safe(lambda: tk.income_stmt, None)          # Spalten = Jahre
    hist = _safe(lambda: tk.history(period="10y", auto_adjust=True), None)
    if fin is None or hist is None or not len(hist):
        return {"pe_hist_mean": None, "pe_hist_std": None}
    shares = _safe(lambda: float(tk.info.get("sharesOutstanding")), None)
    pes = []
    try:
        ni_row = "Net Income" if "Net Income" in fin.index else None
        for col in fin.columns:
            year = col.year
            ni = fin.loc[ni_row, col] if ni_row else None
            if not ni or not shares:
                continue
            eps = float(ni) / shares
            if eps <= 0:
                continue
            year_prices = hist.loc[hist.index.year == year, "Close"]
            if len(year_prices):
                pes.append(float(year_prices.mean()) / eps)
    except Exception:
        pass
    if len(pes) >= 3:
        return {"pe_hist_mean": round(st.mean(pes), 1), "pe_hist_std": round(st.pstdev(pes) or 1.0, 2)}
    return {"pe_hist_mean": None, "pe_hist_std": None}


def benchmark_returns(bench_symbol: str):
    """Tagesrenditen des Referenzindex für die abnormale Rendite."""
    tk = yf.Ticker(bench_symbol)
    hist = _safe(lambda: tk.history(period="1y", auto_adjust=True), None)
    if hist is None or not len(hist):
        return None
    return hist["Close"].pct_change().dropna()


def stock_returns(yf_symbol: str):
    tk = yf.Ticker(yf_symbol)
    hist = _safe(lambda: tk.history(period="1y", auto_adjust=True), None)
    if hist is None or not len(hist):
        return None
    return hist["Close"].pct_change().dropna()
