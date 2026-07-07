"""
Baut aus Rohdaten (SEC EDGAR / yfinance, optional FMP-Overlay) das Metrik-Dict
fuer scoring.compute(). Rechnet ROIC, Cash Conversion, Nettoverschuldung/EBITDA,
Verwaesserung, Reverse-DCF, Margin of Safety, FCF-Rendite sowie Piotroski,
Beneish-M und Accruals. Defensiv: fehlt etwas, bleibt die Metrik None.
"""
from __future__ import annotations
from config import WACC, FINANCIALS
from metrics_extra import piotroski, beneish_m, accruals_ratio


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _latest(series: dict):
    return series[max(series)] if series else None


def _two(series: dict):
    """(t, t-1) Werte einer Jahresreihe."""
    if not series or len(series) < 2:
        return (_latest(series), None)
    ks = sorted(series)
    return series[ks[-1]], series[ks[-2]]


def _cagr(series: dict):
    if not series or len(series) < 2:
        return None
    ks = sorted(series)
    a, b, n = series[ks[0]], series[ks[-1]], ks[-1] - ks[0]
    if not a or a <= 0 or not b or b <= 0 or n <= 0:
        return None
    return (b / a) ** (1 / n) - 1


def _cur_prev(ed, keys):
    """Baut cur/prev-Dicts aus mehreren Jahresreihen fuer Piotroski/Beneish."""
    cur, prev = {}, {}
    for k in keys:
        c, p = _two(ed.get(k, {}))
        cur[k], prev[k] = c, p
    return cur, prev


def _extras(ed, entry_ticker):
    """Piotroski, Beneish-M, Accruals aus 2-Jahres-Daten (best effort)."""
    out = {}
    # Piotroski
    keys_p = ["net_income", "op_cash_flow", "assets", "long_term_debt",
              "current_assets", "current_liabilities", "shares", "gross_profit", "revenue"]
    cur, prev = _cur_prev(ed, keys_p)
    pcur = {"net_income": cur["net_income"], "cfo": cur["op_cash_flow"], "assets": cur["assets"],
            "ltd": cur["long_term_debt"], "current_assets": cur["current_assets"],
            "current_liabilities": cur["current_liabilities"], "shares": cur["shares"],
            "gross_profit": cur["gross_profit"], "revenue": cur["revenue"]}
    pprev = {"net_income": prev["net_income"], "cfo": prev["op_cash_flow"], "assets": prev["assets"],
             "ltd": prev["long_term_debt"], "current_assets": prev["current_assets"],
             "current_liabilities": prev["current_liabilities"], "shares": prev["shares"],
             "gross_profit": prev["gross_profit"], "revenue": prev["revenue"]}
    f_raw, f_max = piotroski(pcur, pprev)
    out["piotroski_raw"], out["piotroski_max"] = f_raw, f_max

    # Beneish-M
    keys_b = ["revenue", "receivables", "cogs", "current_assets", "ppe", "assets",
              "dep_amort", "sga", "net_income", "op_cash_flow", "current_liabilities", "long_term_debt"]
    cb, pb = _cur_prev(ed, keys_b)
    def bmap(d):
        return {"revenue": d["revenue"], "receivables": d["receivables"], "cogs": d["cogs"],
                "current_assets": d["current_assets"], "ppe": d["ppe"], "assets": d["assets"],
                "dep": d["dep_amort"], "sga": d["sga"], "net_income": d["net_income"],
                "cfo": d["op_cash_flow"], "current_liabilities": d["current_liabilities"],
                "ltd": d["long_term_debt"] or 0}
    out["mscore"] = beneish_m(bmap(cb), bmap(pb))
    return out


def from_edgar(ed: dict, price: dict, ticker: str, sector: str, fmp: dict | None = None) -> dict:
    r = {"is_financial": ticker in FINANCIALS, "sector": sector, "source": "edgar"}
    ni = _latest(ed.get("net_income", {}))
    op = _latest(ed.get("operating_income", {}))
    assets = _latest(ed.get("assets", {}))
    cur_liab = _latest(ed.get("current_liabilities", {}))
    cash = _latest(ed.get("cash", {}))
    ltd = _latest(ed.get("long_term_debt", {})) or 0
    std = _latest(ed.get("short_term_debt", {})) or 0
    ocf = _latest(ed.get("op_cash_flow", {}))
    capex = _latest(ed.get("capex", {}))
    da = _latest(ed.get("dep_amort", {}))
    gp, rev, shares = ed.get("gross_profit", {}), ed.get("revenue", {}), ed.get("shares", {})

    invested = (assets - cur_liab) if (assets is not None and cur_liab is not None) else None
    if op is not None and invested and invested > 0:
        r["roic"] = (op * 0.79) / invested
    op_s = ed.get("operating_income", {})
    if len(op_s) >= 2 and invested:
        ks = sorted(op_s)
        r["incremental_roic"] = ((op_s[ks[-1]] - op_s[ks[-2]]) * 0.79) / abs(invested)

    fcf = (ocf - abs(capex)) if (ocf is not None and capex is not None) else None
    if fcf is not None and ni:
        r["cash_conversion"] = fcf / ni
    r["accruals"] = accruals_ratio(ni, ocf, assets)

    gm_series = [gp[y] / rev[y] for y in sorted(set(gp) & set(rev)) if rev[y]]
    if gm_series:
        r["gross_margin_series"] = gm_series
    ebitda = (op + da) if (op is not None and da is not None) else None
    if ebitda:
        r["netdebt_ebitda"] = ((ltd + std) - (cash or 0)) / ebitda
    r["shares_cagr"] = _cagr(shares)
    r["expected_growth"] = _cagr(rev) or price.get("forward_growth")

    r.update(_extras(ed, ticker))
    _valuation_common(r, price, ni, fcf)
    if fmp:
        _overlay_fmp(r, fmp)
    return r


def from_yfinance(tk_symbol: str, price: dict, ticker: str, sector: str) -> dict:
    import yfinance as yf
    r = {"is_financial": ticker in FINANCIALS, "sector": sector, "source": "yfinance"}
    tk = yf.Ticker(tk_symbol)

    def grab(df, row):
        try:
            if df is not None and row in df.index:
                s = df.loc[row].dropna()
                return {c.year: float(s[c]) for c in s.index}
        except Exception:
            pass
        return {}

    inc, bs, cf = _safe(lambda: tk.income_stmt), _safe(lambda: tk.balance_sheet), _safe(lambda: tk.cashflow)
    ed = {
        "revenue": grab(inc, "Total Revenue"), "operating_income": grab(inc, "Operating Income"),
        "net_income": grab(inc, "Net Income"), "gross_profit": grab(inc, "Gross Profit"),
        "op_cash_flow": grab(cf, "Operating Cash Flow"), "capex": grab(cf, "Capital Expenditure"),
        "assets": grab(bs, "Total Assets"), "current_liabilities": grab(bs, "Current Liabilities"),
        "current_assets": grab(bs, "Current Assets"),
        "cash": grab(bs, "Cash And Cash Equivalents"), "long_term_debt": grab(bs, "Long Term Debt"),
        "short_term_debt": grab(bs, "Current Debt"), "dep_amort": grab(cf, "Depreciation And Amortization"),
        "shares": grab(bs, "Share Issued"), "receivables": grab(bs, "Accounts Receivable"),
        "cogs": grab(inc, "Cost Of Revenue"), "sga": grab(inc, "Selling General And Administration"),
        "ppe": grab(bs, "Net PPE"),
    }
    ni, op = _latest(ed["net_income"]), _latest(ed["operating_income"])
    assets, cur_l = _latest(ed["assets"]), _latest(ed["current_liabilities"])
    invested = (assets - cur_l) if (assets is not None and cur_l is not None) else None
    if op is not None and invested and invested > 0:
        r["roic"] = (op * 0.79) / invested
    ocf, capex = _latest(ed["op_cash_flow"]), _latest(ed["capex"])
    fcf = (ocf - abs(capex)) if (ocf is not None and capex is not None) else None
    if fcf is not None and ni:
        r["cash_conversion"] = fcf / ni
    r["accruals"] = accruals_ratio(ni, ocf, assets)
    gm_series = [ed["gross_profit"][y] / ed["revenue"][y]
                 for y in sorted(set(ed["gross_profit"]) & set(ed["revenue"])) if ed["revenue"][y]]
    if gm_series:
        r["gross_margin_series"] = gm_series
    da = _latest(ed["dep_amort"])
    ebitda = (op + da) if (op is not None and da is not None) else None
    if ebitda:
        r["netdebt_ebitda"] = ((_latest(ed["long_term_debt"]) or 0) +
                               (_latest(ed["short_term_debt"]) or 0) - (_latest(ed["cash"]) or 0)) / ebitda
    r["shares_cagr"] = _cagr(ed["shares"])
    r["expected_growth"] = _cagr(ed["revenue"]) or price.get("forward_growth")
    r.update(_extras(ed, ticker))
    _valuation_common(r, price, ni, fcf)
    return r


def _overlay_fmp(r, fmp):
    """Bessere FMP-Werte ueberschreiben Naeherungen (KGV-Historie, Piotroski, ROIC)."""
    for k in ("pe_now", "pe_hist_mean", "pe_hist_std", "ev_now", "ev_hist_mean",
              "ev_hist_std", "market_cap", "roic", "piotroski_raw", "piotroski_max"):
        if fmp.get(k) is not None:
            r[k] = fmp[k]
    r["source"] = "fmp"


def _valuation_common(r, price, ni, fcf):
    r["pe_now"] = price.get("pe_now")
    r["pe_hist_mean"] = price.get("pe_hist_mean")
    r["pe_hist_std"] = price.get("pe_hist_std")
    r["drawdown"] = price.get("drawdown")
    r["events"] = price.get("events", [])
    mcap = price.get("market_cap")
    if mcap and fcf and fcf > 0:
        r["pfcf_now"] = mcap / fcf
        r["fcf_yield"] = fcf / mcap
    pe = r.get("pe_now")
    if pe and pe > 0:
        r["implied_growth"] = max(0.0, (pe - 8) * 0.9 / 100)
    eg = r.get("expected_growth")
    if r.get("implied_growth") is not None and eg is not None:
        r["realistic"] = r["implied_growth"] <= eg + 0.03
    if fcf and fcf > 0 and mcap and eg is not None:
        g = max(min(eg, 0.15), -0.02)
        disc, tg = WACC + 0.02, 0.025
        val, cf_t = 0.0, fcf
        for t in range(1, 11):
            cf_t *= (1 + g)
            val += cf_t / (1 + disc) ** t
        val += cf_t * (1 + tg) / (disc - tg) / (1 + disc) ** 10
        r["mos"] = (val - mcap) / val if val else None
