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
import config

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


_TYPE_LABEL = {"fundamental": "Fundamental", "emotional": "Emotional / Sentiment", "makro": "Makro / Marktweit"}


def _fact_bullets(title: str, type_: str, abn: float, strength: str, date_str: str) -> list[str]:
    """Reine Fakten (kein Urteil): was ist gemeldet worden, wie hat der Kurs
    reagiert, wie ist das Ereignis eingeordnet. Die Einschaetzung kommt
    bewusst NICHT hier rein, sondern separat ueber _assessment()."""
    richtung = "Anstieg" if abn > 0 else "Rückgang"
    return [
        f"Auslöser: {title}",
        f"Kursreaktion am {date_str}: {abn:+.1f}\u202f% {richtung} (marktbereinigt gegenüber dem Referenzindex)",
        f"Einordnung: {_TYPE_LABEL.get(type_, 'Makro / Marktweit')} · Stärke {strength}",
    ]


def _assessment(type_: str, abn: float, strength: str) -> str:
    """GENAU EIN Satz -- unsere Einschaetzung, getrennt von den Fakten oben.
    Wird im Frontend optisch abgesetzt dargestellt (eigenes Feld, nicht Teil
    der bullets-Liste)."""
    if type_ == "fundamental":
        meaning = ("ein konkreter operativer Fortschritt, der sich bei anhaltendem Trend in den kommenden "
                   "Quartalszahlen bestätigen sollte" if abn > 0 else
                   "ein echter geschäftlicher Rückschlag, der sich erst in den kommenden Quartalszahlen "
                   "bestätigen oder relativieren wird")
    elif type_ == "emotional":
        meaning = "vor allem Stimmung und Positionierung — an der operativen Substanz hat sich nichts geändert"
    else:
        meaning = "eine Bewegung, die Gesamtmarkt oder Sektor gleichermassen betrifft und wenig unternehmensspezifisch aussagt"
    weight = {"Hoch": "Wir stufen die Tragweite als hoch ein.",
              "Mittel": "Wir stufen die Tragweite als spürbar, aber nicht dramatisch ein."}.get(
              strength, "Wir stufen die Tragweite als begrenzt ein.")
    return f"Unsere Einschätzung: Für das Unternehmen bedeutet das {meaning}. {weight}"


def _narrative(name: str, title: str, type_: str, abn: float, strength: str, date_str: str) -> str:
    """Der ausfuehrliche 'Bericht'-Text, klar dreiteilig:
    (a) was ist passiert, (b) was bedeutet das fuer das Unternehmen kuenftig,
    (c) wie gravierend schaetzen wir das ein."""
    richtung = "stieg" if abn > 0 else "fiel"
    a = (f"Am {date_str} {richtung} der Kurs von {name} marktbereinigt um {abn:+.1f}\u202f% "
         f"infolge der Meldung: {title}.")

    if type_ == "fundamental":
        b = ("Das ist durch echte Geschäftszahlen oder eine veränderte Guidance gestützt und damit ein Signal, "
             "das über den Tag hinaus relevant sein kann — entscheidend wird, ob sich der Trend in den "
             "kommenden Quartalszahlen bestätigt.")
    elif type_ == "emotional":
        b = ("Das ist überwiegend sentimentgetrieben, ohne dass sich an den zugrunde liegenden Geschäftszahlen "
             "etwas verändert hätte — solche Bewegungen klingen erfahrungsgemäss ab, sobald sich die Stimmung "
             "wieder normalisiert.")
    else:
        b = ("Das hängt in erster Linie an der Entwicklung des Gesamtmarkts oder Sektors, etwa Zinserwartungen "
             "oder einer Rotation zwischen Branchen, und sagt für sich genommen wenig über das Unternehmen "
             "selbst aus.")

    c = {
        "Hoch": "Angesichts der Stärke der Kursreaktion stufen wir das als eine der gewichtigeren Meldungen der letzten Zeit ein.",
        "Mittel": "In der Gesamtschau ist das spürbar, aber nicht dramatisch — eine Beobachtungsgrösse, kein Alarmsignal.",
    }.get(strength, "Die Tragweite schätzen wir insgesamt als begrenzt ein.")

    return f"{a} {b} {c}"


def fetch_events(yf_symbol: str, stock_ret, bench_ret, limit=8, name: str | None = None):
    """Liste klassifizierter Ereignisse mit abnormaler Rendite.

    Rauschfilter: Ereignisse ohne verlaessliche oder spuerbare marktbereinigte
    Kursreaktion (< config.NEWS_MIN_ABS_MOVE) werden aussortiert, statt als
    "Tief"-Eintrag trotzdem zu erscheinen -- sonst ertrinkt die eine wichtige
    Meldung der Woche in vielen belanglosen."""
    display_name = name or yf_symbol
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
        if abn is None or abs(abn) < config.NEWS_MIN_ABS_MOVE:
            continue
        type_ = classify(title)
        strength = strength_from(abn)
        date_str = date.strftime("%d.%m.%Y")
        events.append({
            "t": title,
            "d": date_str,
            "move": abn,
            "type": type_,
            "s": strength,
            "bullets": _fact_bullets(title, type_, abn, strength, date_str),
            "assessment": _assessment(type_, abn, strength),
            "sum": _narrative(display_name, title, type_, abn, strength, date_str),
        })
    return events
