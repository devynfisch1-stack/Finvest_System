"""
News- und Preistreiber-Modul.

Zwei Schritte:
1. EVENT-STUDY: zu jeder Meldung die ABNORMALE Rendite berechnen
   (Aktien-Tagesrendite minus Benchmark-Tagesrendite). So trennen wir
   firmenspezifische Bewegungen von reinem Marktrauschen.
2. KLASSIFIKATION: fundamental (Guidance/Zahlen) vs. emotional (Sentiment)
   vs. makro (Zins/Inflation/Rotation).
   - Standard: transparente Schlagwort-Heuristik (kostenlos, offline).
   - Optional: LLM-Klassifikation über die Anthropic-API, falls
     ANTHROPIC_API_KEY gesetzt ist (deutlich treffsicherer).

EHRLICH: Das ist der am schwersten zu automatisierende Teil. Die Heuristik
ist ein solider Startpunkt, ersetzt aber keine echte Modell-Klassifikation.
"""
from __future__ import annotations
import os
import datetime as dt
import yfinance as yf

FUNDAMENTAL_KW = ["guidance", "earnings", "revenue", "profit", "margin", "forecast",
                  "results", "beats", "misses", "downgrade", "upgrade", "order",
                  "contract", "lawsuit", "fda", "approval", "dividend", "buyback",
                  "outlook", "sales", "loss", "warning", "cuts", "raises"]
MACRO_KW = ["fed", "rate", "rates", "inflation", "cpi", "tariff", "yields",
            "recession", "macro", "treasury", "jobs", "gdp", "central bank"]


def _classify_heuristic(title: str) -> str:
    t = title.lower()
    if any(k in t for k in MACRO_KW):
        return "makro"
    if any(k in t for k in FUNDAMENTAL_KW):
        return "fundamental"
    return "emotional"


def _classify_llm(title: str):
    """Optionaler LLM-Aufruf. Gibt None zurück, wenn kein Key/Fehler."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content":
                       "Klassifiziere diese Börsen-Schlagzeile in genau EIN Wort: "
                       "'fundamental' (Zahlen/Guidance/operativ), 'emotional' "
                       "(Sentiment/Angst/Hype ohne harte Zahlen) oder 'makro' "
                       "(Zinsen/Inflation/Marktrotation). Nur das Wort.\n\n"
                       f"Schlagzeile: {title}"}],
        )
        word = msg.content[0].text.strip().lower()
        return word if word in ("fundamental", "emotional", "makro") else None
    except Exception:
        return None


def classify(title: str) -> str:
    return _classify_llm(title) or _classify_heuristic(title)


def _abnormal_return(date, stock_ret, bench_ret):
    """Aktien- minus Benchmark-Rendite am (nächstgelegenen) Handelstag in %."""
    if stock_ret is None:
        return None
    try:
        d = date.date() if isinstance(date, dt.datetime) else date
        sr = stock_ret[stock_ret.index.date == d]
        if not len(sr):
            return None
        s = float(sr.iloc[0])
        b = 0.0
        if bench_ret is not None:
            br = bench_ret[bench_ret.index.date == d]
            b = float(br.iloc[0]) if len(br) else 0.0
        return round((s - b) * 100, 1)
    except Exception:
        return None


def strength_from(abn):
    a = abs(abn or 0)
    return "Hoch" if a >= 4 else "Mittel" if a >= 2 else "Tief"


def fetch_events(yf_symbol: str, stock_ret, bench_ret, limit=8):
    """Liste klassifizierter Ereignisse mit abnormaler Rendite."""
    tk = yf.Ticker(yf_symbol)
    try:
        raw = tk.news or []
    except Exception:
        raw = []
    events = []
    for n in raw[:limit]:
        content = n.get("content", n)
        title = content.get("title") or n.get("title")
        if not title:
            continue
        ts = n.get("providerPublishTime")
        date = dt.datetime.fromtimestamp(ts) if ts else dt.datetime.now()
        abn = _abnormal_return(date, stock_ret, bench_ret)
        events.append({
            "t": title,
            "d": date.strftime("%d.%m.%Y"),
            "move": abn if abn is not None else 0.0,
            "type": classify(title),
            "s": strength_from(abn),
            "sum": f"Abnormale Tagesrendite {abn if abn is not None else 'n/a'} % "
                   f"(firmenspezifisch, marktbereinigt). Automatische Klassifikation: "
                   f"{classify(title)}.",
        })
    return events
