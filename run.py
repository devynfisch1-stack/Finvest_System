"""
Einstiegspunkt (optimiert, zwei Pass).

Live:            python run.py
Offline-Test:    python run.py --mock

Ablauf live:
  Pass 1  -> je Titel Rohmetriken holen (EDGAR/yfinance, optional FMP-Overlay)
  Sektor  -> Sektor-relative Perzentile ueber das ganze Universum injizieren
  Pass 2  -> scoring.compute() je Titel
  Ausgabe -> data/stocks.json  +  Punkt-in-Zeit-Snapshot in data/history/
"""
from __future__ import annotations
import json, os, sys, time, datetime as dt
import config
from config import UNIVERSE, BENCHMARK
import scoring
from metrics_extra import inject_sector_percentiles

HERE = os.path.dirname(__file__)


def fetch_raw(entry, region):
    import prices as P, news as NEWS
    from fundamentals import from_edgar, from_yfinance
    price = P.price_block(entry["yf"]); price.update(P.historical_pe(entry["yf"]))
    price["events"] = NEWS.fetch_events(entry["yf"], P.stock_returns(entry["yf"]),
                                        P.benchmark_returns(BENCHMARK[region]))
    fmp = {}
    if config.FMP_ENABLED and entry["edgar"]:
        try:
            from fmp import fmp_block
            fmp = fmp_block(entry["yf"])
        except Exception:
            fmp = {}
    if entry["edgar"]:
        from edgar import fetch_edgar_fundamentals
        raw = from_edgar(fetch_edgar_fundamentals(entry["ticker"]), price, entry["ticker"], entry["sector"], fmp)
    else:
        raw = from_yfinance(entry["yf"], price, entry["ticker"], entry["sector"])
    raw["_entry"], raw["_region"], raw["_price"] = entry, region, price
    return raw


def assemble(raw, result):
    e, price = raw["_entry"], raw["_price"]
    row = {
        "ticker": e["ticker"], "name": e["name"], "domain": e["domain"], "sector": e["sector"],
        "region": raw["_region"], "isFin": e["ticker"] in config.FINANCIALS,
        "marketCap": price.get("market_cap"), "price": price.get("price"),
        "drawdown": price.get("drawdown"), "peNow": raw.get("pe_now"), "peHist": raw.get("pe_hist_mean"),
        "impliedGrowth": None if raw.get("implied_growth") is None else round(raw["implied_growth"] * 100),
        "realistic": raw.get("realistic", True), "events": raw.get("events", []), **result,
    }
    # Der Bericht (inkl. optionalem Anthropic-API-Aufruf fuer natuerlichere
    # Sprache) wird bewusst NUR beim woechentlichen Lauf erzeugt -- nicht bei
    # jedem taeglichen Score-Update. Das Dashboard hat ohnehin einen eigenen,
    # kostenlosen Fallback-Generator (buildReportPages in FinvestFundamental.jsx),
    # der greift, wenn "report" im JSON fehlt. So faellt der Anthropic-Verbrauch
    # nur 1x/Woche an statt 7x/Woche.
    if os.environ.get("FINVEST_WEEKLY") == "1":
        from report import build as build_report
        row["report"] = build_report(row)
        from reports_archive import save_report
        try:
            save_report(row["ticker"], row["name"], row["domain"], row["region"], row["report"])
        except Exception as ex:
            print(f"Archiv-Fehler {row['ticker']}: {ex}")
    return row


def run_live():
    payload = {"generated": dt.datetime.utcnow().isoformat() + "Z", "regions": {}}
    for region, entries in UNIVERSE.items():
        raws = []
        for e in entries:
            try:
                raws.append(fetch_raw(e, region)); print(f"[{region}] {e['ticker']:6s} ok")
            except Exception as ex:
                print(f"[{region}] {e['ticker']:6s} FEHLER: {ex}")
            time.sleep(0.4)
        inject_sector_percentiles(raws)                       # Sektor-Perzentile
        rows = [assemble(r, scoring.compute(r)) for r in raws]
        rows.sort(key=lambda x: (x.get("marketCap") or 0), reverse=True)
        payload["regions"][region] = rows
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "stocks.json"), "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    _snapshot(payload)
    print(f"\nFertig -> data/stocks.json  ({sum(len(v) for v in payload['regions'].values())} Titel)")


def _snapshot(payload):
    """Punkt-in-Zeit-Snapshot: baut ueber die Zeit den eigenen PIT-Datensatz auf."""
    d = os.path.join(HERE, "data", "history"); os.makedirs(d, exist_ok=True)
    slim = {"generated": payload["generated"], "scores": {
        r["ticker"]: {"overall": r["overall"], "quality": r["quality"], "valuation": r["valuation"],
                      "status": r["status"], "peNow": r.get("peNow"), "drawdown": r.get("drawdown")}
        for region in payload["regions"].values() for r in region}}
    fn = dt.datetime.utcnow().strftime("%Y-%m-%d") + ".json"
    with open(os.path.join(d, fn), "w") as f:
        json.dump(slim, f, ensure_ascii=False, indent=2)


# ------------------------------- Offline-Test ----------------------------- #
def _mock_raw(qb, cheap, sector, region, manip=False):
    return {
        "roic": 0.10 + qb * 0.03, "incremental_roic": 0.08 + qb * 0.02, "cash_conversion": 0.7 + qb * 0.1,
        "accruals": 0.02 if not manip else 0.18, "gross_margin_series": [0.44, 0.45, 0.46, 0.45, 0.46],
        "netdebt_ebitda": 1.5 - qb * 0.4, "shares_cagr": -0.01,
        "piotroski_raw": 4 + qb, "piotroski_max": 9,
        "pe_now": (22 if cheap else 34), "pe_hist_mean": 30, "pe_hist_std": 5,
        "pe_sector_score": (8.0 if cheap else 3.5), "fcf_yield": 0.05, "roic_val": 0.13,
        "implied_growth": 0.10, "expected_growth": 0.12, "mos": (0.2 if cheap else -0.1),
        "drawdown": (-32 if cheap else -6), "mscore": (-1.2 if manip else -2.6),
        "sector": sector, "region": region, "source": "mock", "is_financial": False, "realistic": True,
        "events": [
            {"t": "Angst vor KI-Investitionen", "d": "02.04.2026", "move": -6.1, "type": "emotional", "s": "Tief", "sum": ""},
            {"t": "Cloud ueber Erwartung", "d": "15.02.2026", "move": 4.8, "type": "fundamental", "s": "Hoch", "sum": ""},
        ],
    }


def run_mock():
    cases = [("Qualitaet+guenstig", 3, True, False), ("Qualitaet+teuer", 3, False, False),
             ("Schwach", -2, True, False), ("Manipulationsverdacht", 3, True, True)]
    out = []
    for name, qb, cheap, manip in cases:
        res = scoring.compute(_mock_raw(qb, cheap, "Technology", "US", manip))
        out.append({"name": name, **res})
        print(f"{name:22s} Q={res['quality']:>4} V={res['valuation']:>4} D={res['dislocation']:>4} "
              f"=>{res['overall']:>4} {res['status']:11s} sig={str(res['signal']):5s} "
              f"F={res['piotroski_raw']} M={res['mscore']} gate={res['gate_ok']} conf={res['confidence']}%")
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "mock_output.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nOffline-Selbsttest ok -> data/mock_output.json")


if __name__ == "__main__":
    run_mock() if "--mock" in sys.argv else run_live()
