"""
Scoring-Engine (optimiert). Wandelt ROHE Fundamentaldaten in 1-10 Sub-Scores
und aggregiert zu drei Bloecken, wendet Gates an (Bilanz, Ertragsqualitaet,
Beneish-M) und leitet Status + Projektion + Konfidenz ab.

Neu integriert: Piotroski-Score, Accruals, Sektor-relative Perzentile.
Netzwerkfrei -> offline testbar (run.py --mock).
"""
from __future__ import annotations
import statistics as st
from config import (
    WACC, BLOCK_WEIGHTS, QUALITY_WEIGHTS, VALUATION_WEIGHTS,
    GATE_MIN_BALANCE, GATE_MIN_EARNINGS_QUALITY, GATE_BENEISH_M, GATE_CAP,
    Q_HIGH, V_CHEAP, SOURCE_QUALITY,
)
from metrics_extra import piotroski_score, accruals_score


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lin(x, lo, hi):
    if x is None:
        return None
    if hi == lo:
        return 5.5
    return clamp(1 + (x - lo) / (hi - lo) * 9.0, 1, 10)


def zscore_cheap(now, mean, std):
    if now is None or mean is None or not std:
        return None
    return clamp(5.5 + (mean - now) / std * 2.0, 1, 10)


# ------------------------------- QUALITAET -------------------------------- #
def score_quality(r):
    s = {}
    s["roic"] = lin(r["roic"] - WACC, -0.05, 0.20) if r.get("roic") is not None else None
    s["roic_trend"] = lin(r.get("incremental_roic"), 0.0, 0.25)
    # Piotroski
    s["piotroski"] = piotroski_score(r.get("piotroski_raw"), r.get("piotroski_max"))
    # Ertragsqualitaet = Mittel aus Cash Conversion und Accruals-Score
    cc = lin(r.get("cash_conversion"), 0.4, 1.2)
    ac = accruals_score(r.get("accruals"))
    eq = [x for x in (cc, ac) if x is not None]
    s["earnings_quality"] = sum(eq) / len(eq) if eq else None
    # Margenstabilitaet
    gm = r.get("gross_margin_series")
    if gm and len(gm) >= 3 and st.mean(gm):
        cv = st.pstdev(gm) / abs(st.mean(gm))
        s["margin_stability"] = clamp(10 - cv * 45, 1, 10)
    else:
        s["margin_stability"] = None
    s["balance"] = lin(-(r["netdebt_ebitda"]) if r.get("netdebt_ebitda") is not None else None, -4.0, 1.0)
    sc = r.get("shares_cagr")
    s["dilution"] = lin(-sc if sc is not None else None, -0.05, 0.03)
    return s


# ------------------------------- BEWERTUNG -------------------------------- #
def score_valuation(r):
    s = {}
    s["pe_vs_hist"] = zscore_cheap(r.get("pe_now"), r.get("pe_hist_mean"), r.get("pe_hist_std"))
    s["pe_vs_sector"] = r.get("pe_sector_score")
    s["ev_vs_hist"] = zscore_cheap(r.get("ev_now"), r.get("ev_hist_mean"), r.get("ev_hist_std"))
    s["pfcf_vs_hist"] = zscore_cheap(r.get("pfcf_now"), r.get("pfcf_hist_mean"), r.get("pfcf_hist_std"))
    ig, eg = r.get("implied_growth"), r.get("expected_growth")
    s["reverse_dcf"] = clamp(5.5 + (eg - ig) * 25, 1, 10) if (ig is not None and eg is not None) else None
    s["margin_of_safety"] = lin(r.get("mos"), -0.20, 0.50)
    return s


# ------------------------------ DISLOKATION ------------------------------- #
def score_dislocation(r, q, v):
    events = r.get("events") or []
    emo_down = sum(-e["move"] for e in events if e["move"] < 0 and e["type"] != "fundamental")
    fun_down = sum(-e["move"] for e in events if e["move"] < 0 and e["type"] == "fundamental")
    emotional = emo_down > fun_down and emo_down > 0
    dd = r.get("drawdown")
    disl = 5.0
    if emotional: disl += 2.0
    if v >= 6: disl += 1.5
    if q >= Q_HIGH: disl += 1.5
    if fun_down > emo_down: disl -= 2.2
    if dd is not None and dd < -30: disl += 0.5
    disl = clamp(disl, 1, 10)
    signal = emotional and q >= Q_HIGH and v >= 5.5
    if fun_down > emo_down and fun_down > 0:
        verdict = "Juengste Schwaeche ist fundamental begruendet - Vorsicht, kein reines Sentiment."
    elif emotional:
        verdict = ("Schwaeche ueberwiegend emotional/makrogetrieben - Fundamentaldaten intakt. "
                   "Moegliches Einstiegsfenster." if q >= Q_HIGH else
                   "Schwaeche emotional getrieben, Qualitaet aber nicht ueberzeugend.")
    else:
        verdict = "Juengste Bewegung fundamental gestuetzt."
    return disl, signal, verdict


# ------------------------------ AGGREGATION ------------------------------- #
def _block_value(sub, weights):
    num = den = covered = total = 0
    for k, w in weights.items():
        total += 1
        v = sub.get(k)
        if v is None:
            v = 5.5
        else:
            covered += 1
        num += v * w
        den += w
    return num / den, covered, total


def status_from(q, v, gate_ok):
    if not gate_ok: return "Overvalued"
    if q >= Q_HIGH and v >= V_CHEAP: return "Outlier"
    if q >= Q_HIGH and v < V_CHEAP: return "Solid"
    if q < 4.5 and v >= V_CHEAP: return "Value Trap"
    if q >= 5.5 and v >= 5.5: return "Solid"
    if v >= V_CHEAP and q >= 4.5: return "Neutral"
    if q >= Q_HIGH: return "Solid"
    return "Overvalued" if v < 4.5 else "Neutral"


def projection(overall):
    a = (overall - 5) * 3.2 + 8
    comp = lambda rr: (pow(1 + rr / 100, 3) - 1) * 100
    return {"annual": round(a, 1), "base3": round(comp(a)),
            "low3": round(comp(a - 9)), "high3": round(comp(a + 9)),
            "prob": round(clamp(42 + (overall - 5) * 8, 30, 88))}


def compute(raw: dict) -> dict:
    qsub = score_quality(raw)
    vsub = score_valuation(raw)
    q, qcov, qtot = _block_value(qsub, QUALITY_WEIGHTS)
    v, vcov, vtot = _block_value(vsub, VALUATION_WEIGHTS)
    disl, signal, verdict = score_dislocation(raw, q, v)

    # Gates: Bilanz, Ertragsqualitaet, Beneish-M
    m = raw.get("mscore")
    beneish_flag = (m is not None and m > GATE_BENEISH_M)
    gate_ok = ((qsub.get("balance") or 5.5) >= GATE_MIN_BALANCE and
               (qsub.get("earnings_quality") or 5.5) >= GATE_MIN_EARNINGS_QUALITY and
               not beneish_flag)

    overall = (q * BLOCK_WEIGHTS["quality"] + v * BLOCK_WEIGHTS["valuation"]
               + disl * BLOCK_WEIGHTS["dislocation"])
    if not gate_ok:
        overall = min(overall, GATE_CAP)
    status = status_from(q, v, gate_ok)

    coverage = (qcov + vcov) / (qtot + vtot)
    src = SOURCE_QUALITY.get(raw.get("source", "yfinance"), 0.7)
    confidence = round(clamp(40 + coverage * 45 * src
                             - (0 if raw.get("realistic", True) else 6)
                             - (5 if raw.get("is_financial") else 0), 40, 96))

    return {
        "quality": round(q, 1), "valuation": round(v, 1), "dislocation": round(disl, 1),
        "overall": round(overall, 1), "status": status, "signal": bool(signal),
        "verdict": verdict, "gate_ok": gate_ok, "beneish_flag": bool(beneish_flag),
        "mscore": m, "piotroski_raw": raw.get("piotroski_raw"),
        "confidence": confidence, "coverage": round(coverage, 2),
        "source": raw.get("source", "yfinance"),
        "quality_sub": {k: (round(x, 1) if x is not None else None) for k, x in qsub.items()},
        "valuation_sub": {k: (round(x, 1) if x is not None else None) for k, x in vsub.items()},
        "projection": projection(overall),
    }
