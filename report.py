"""
Weekly-Report-Generator (vertieft). Erzeugt einen mehrseitigen, in der Tiefe
gestaffelten Bericht -- von der aktuellen Woche bis zum grossen Bild --
statt einer oberflaechlichen Kurzzusammenfassung.

Struktur (siehe auch dashboard/FinvestFundamental.jsx -> ReportViewer):
  headline      -- spannungserzeugender Übertitel dieser Ausgabe
  weekRange     -- "30.06. - 06.07.2026"
  pages: [
    { title: "Diese Woche",     paragraphs: [...] }  # kurzfristige Treiber
    { title: "Dieser Trend",    paragraphs: [...] }  # mittelfristig, Bewertung
    { title: "Das grosse Bild", paragraphs: [...] }  # langfristige These, Moat/Innovation
  ]

- Standard: ausführliche Text-Vorlage (kostenlos, offline, deterministisch).
- Optional: natuerlichere / tiefere Formulierung ueber die Anthropic-API,
  wenn ANTHROPIC_API_KEY gesetzt ist.

Wird vom woechentlichen Workflow (Sonntag 18:00 CH-Zeit) aufgerufen und unter
data/reports/{ticker}/{datum}.json gespeichert (siehe reports_index.py).
"""
from __future__ import annotations
import os
import json
import datetime as dt

STATUS_PLAIN = {
    "Outlier": "ein möglicher Ausreisser nach oben – hohe Qualität trifft aktuell auf einen günstigen Kurs",
    "Solid": "solide, aber derzeit nicht besonders günstig bewertet – eher eine Beobachtungsposition",
    "Neutral": "in einem ausgeglichenen Zustand – weder ein klares Schnäppchen noch ein Warnsignal",
    "Value Trap": "eine mögliche Value-Falle – günstig bewertet, aber die Geschäftsqualität überzeugt nicht",
    "Overvalued": "aktuell wenig attraktiv – zu teuer bewertet oder mit einem aktiven Warnsignal",
}
ART = {
    "fundamental": "auf Basis echter Geschäftszahlen",
    "emotional": "eher aus Stimmung und Sorge heraus, ohne dass sich an den Zahlen etwas geändert hätte",
    "makro": "im Sog des Gesamtmarkts, etwa wegen Zinserwartungen oder einer Sektorrotation",
}


def _variant_seed(stock: dict, salt: str) -> int:
    """Deterministisch pro Aktie + Woche + Textbaustein -- stabil innerhalb
    einer Woche, aber unterschiedlich zwischen Aktien und über die Wochen
    hinweg. Python-Aequivalent des Frontend-Varianz-Systems."""
    s = f"{stock.get('ticker', '')}-{_week_range()}-{salt}"
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def _pick(stock: dict, salt: str, variants: list):
    return variants[_variant_seed(stock, salt) % len(variants)]


def _week_range():
    today = dt.date.today()
    start = today - dt.timedelta(days=today.weekday() + 1)  # letzter Sonntag
    end = start + dt.timedelta(days=6)
    return f"{start.strftime('%d.%m.')} – {end.strftime('%d.%m.%Y')}"


def _headline(stock: dict) -> str:
    """Spannungserzeugender Übertitel, abgeleitet vom staerksten Treiber der Woche."""
    events = sorted(stock.get("events", []), key=lambda e: abs(e.get("m", e.get("move", 0))), reverse=True)
    name = stock["name"]
    if events:
        top = events[0]
        move = top.get("m", top.get("move", 0))
        if top.get("type") == "emotional" and move < 0 and stock.get("quality", 0) >= 6.5:
            return f"Warum der Markt bei {name} gerade übertreibt"
        if top.get("type") == "fundamental" and move > 0:
            return f"{name} liefert – und der Kurs zieht nach"
        if top.get("type") == "fundamental" and move < 0:
            return f"{name}: Ein Rückgang, den man ernst nehmen sollte"
        if move < 0:
            return f"{name} im Ausverkauf – Substanz oder Sentiment?"
        return f"{name}: Ruhige Woche, klarer Trend"
    return f"{name} im Wochenüberblick"


def _section_week(stock: dict) -> list[str]:
    """Kurzfristig: was ist passiert, was hat es ausgeloest, was bedeutet es
    langfristig -- als Erzaehlung, keine Kategorien-Sprache."""
    events = sorted(stock.get("events", []), key=lambda e: abs(e.get("m", e.get("move", 0))), reverse=True)
    name = stock["name"]
    if not events:
        return [_pick(stock, "week-quiet", [
            f"Für {name} gab es in dieser Woche keine grösseren Kursausschläge mit erkennbarem Auslöser. "
            f"Der Kurs bewegte sich im Rahmen des breiten Marktes, ohne dass ein einzelnes Ereignis die "
            f"Richtung vorgegeben hätte. Das ist an sich keine schlechte Nachricht – ruhige Wochen sind für "
            f"langfristig orientierte Anleger oft unauffälliger, aber nicht weniger wichtig, weil sie "
            f"zeigen, dass keine akute Störung im Geschäftsmodell vorliegt.",
            f"{name} zeigte diese Woche kaum Ausschläge, die über das normale Marktrauschen hinausgingen. "
            f"Kein einzelnes Ereignis hat den Kurs spürbar bewegt. Für langfristige Anleger ist das eher "
            f"beruhigend als langweilig: Stille Wochen bedeuten meist, dass im operativen Geschäft nichts "
            f"Grundlegendes aus der Bahn geraten ist.",
            f"Diese Woche verlief bei {name} unauffällig – die Bewegungen blieben im Rahmen dessen, was man "
            f"als normales Marktrauschen bezeichnen würde. Das heisst nicht, dass nichts passiert ist, "
            f"sondern nur, dass nichts gross genug war, um die Richtung zu bestimmen.",
        ])]

    top = events[0]
    top_title = top.get("t", top.get("title", ""))
    top_move = top.get("m", top.get("move", 0))
    top_type = top.get("type", "makro")
    top_sum = top.get("sum")

    intro = _pick(stock, "week-intro", [
        f"Diese Woche drehte sich bei {name} vieles um {top_title}.",
        f"Im Zentrum der Woche stand bei {name}: {top_title}.",
        f"Was diese Woche bei {name} auffiel: {top_title}.",
    ])
    p1 = intro + (f" {top_sum}" if top_sum else
                  f" Der Kurs bewegte sich um {'+' if top_move > 0 else ''}{top_move}\u202f%.")

    short_term_cause = {
        "fundamental": "konkrete, neue Geschäftszahlen oder eine veränderte Guidance",
        "emotional": "Stimmung und Positionierung, ohne dass sich an den Zahlen etwas geändert hätte",
        "makro": "die Entwicklung des Gesamtmarkts, etwa Zinserwartungen oder eine Sektorrotation",
    }.get(top_type, "eine Mischung aus mehreren Faktoren")
    others = events[1:3]
    others_txt = ""
    if others:
        titles = " und ".join(f"„{e.get('t', e.get('title', ''))}\"" for e in others)
        others_txt = f" Daneben spielte auch {titles} eine Rolle, wenn auch mit geringerem Gewicht."
    q = stock.get("quality", 5)
    if q >= 6.5:
        long_term = (f"Für die langfristige Substanz von {name} ändert das nach aktuellem Stand wenig – die "
                     f"Kapitalrendite und die Bilanz bleiben die eigentlichen Massstäbe, nicht die "
                     f"Kursbewegung dieser Woche.")
    elif q >= 5:
        long_term = ("Ob das langfristig etwas verändert, ist noch offen – dafür lohnt sich ein Blick auf "
                     "die kommenden Quartalszahlen mehr als auf den Kurs dieser Woche.")
    else:
        long_term = (f"Langfristig bleibt bei {name} ohnehin die wichtigere Frage, ob sich die operative "
                     f"Substanz verbessert – und da gibt es aktuell mehr offene Punkte als diese eine "
                     f"Kursbewegung beantworten kann.")
    p2 = _pick(stock, "week-shortlong", [
        f"Kurzfristig ausgelöst hat das vor allem {short_term_cause}.{others_txt} {long_term}",
        f"Der unmittelbare Auslöser war {short_term_cause}.{others_txt} {long_term}",
    ])
    return [p1, p2]


def _section_trend(stock: dict) -> list[str]:
    """Mittelfristig: Bewertung, Trend, wo die Aktie im eigenen historischen Kontext steht."""
    name = stock["name"]
    pe, peh = stock.get("peNow"), stock.get("peHist")
    dd = stock.get("drawdown")
    v = stock.get("valuation", 5)
    q = stock.get("quality", 5)

    if pe and peh:
        rel = "günstiger" if pe < peh else "teurer"
        diff = abs(round((pe - peh) / peh * 100))
        p1 = _pick(stock, "trend-pe", [
            f"Zieht man den Blick etwas weiter, zeigt sich {name} beim Kurs-Gewinn-Verhältnis mit {pe} "
            f"gegenüber dem eigenen historischen Schnitt von {peh} rund {diff}\u202f% {rel} bewertet als "
            f"sonst üblich. Das misst die Aktie an ihrer eigenen Vergangenheit, nicht an einem "
            f"willkürlichen Schwellenwert, und ist damit eine der aussagekräftigsten Grössen für die "
            f"Frage, ob der aktuelle Kurs eher eine Chance oder eine Warnung ist.",
            f"Mit etwas mehr Abstand betrachtet: Das Kurs-Gewinn-Verhältnis von {name} liegt aktuell bei "
            f"{pe}, gegenüber einem eigenen historischen Mittel von {peh} – also rund {diff}\u202f% {rel} "
            f"als üblich. Dieser Vergleich mit der eigenen Historie sagt mehr aus als ein absoluter "
            f"Schwellenwert, weil er berücksichtigt, wie der Markt diese Aktie normalerweise bewertet.",
        ])
    else:
        p1 = (f"Zur Einordnung der Bewertung von {name} liegen aktuell keine ausreichend verlässlichen "
              f"historischen Vergleichswerte vor.")

    if dd is not None:
        p2 = (f"Vom letzten Allzeithoch ist der Kurs {abs(dd):.0f}\u202f% entfernt. Für sich allein sagt "
              f"das wenig aus – ein Rückgang kann eine Kaufgelegenheit oder eine berechtigte Neubewertung "
              f"sein. Entscheidend ist, wie sich dieser Abstand mit der Qualität des Geschäfts und der "
              f"vorherigen Wocheneinordnung deckt: {('Ein deutlicher Rückgang bei intakten Fundamentaldaten ist ein Muster, das in der Vergangenheit häufiger zu überdurchschnittlichen Erholungen geführt hat.' if dd < -20 and q >= 6.5 else 'Solange kein grösserer Rückgang vorliegt, bleibt dieser Punkt vor allem eine Beobachtungsgrösse.')}")
    else:
        p2 = "Zum Abstand vom Allzeithoch liegen aktuell keine verlässlichen Daten vor."

    if v >= 6.5:
        p3 = _pick(stock, "trend-cheap", [
            "Insgesamt spricht die aktuelle Bewertung eher für die Aktie: Sie handelt mit einem gewissen "
            "Sicherheitsabschlag gegenüber ihrem geschätzten fairen Wert, was zukünftigen Anlegern etwas "
            "mehr Puffer nach unten verschafft.",
            "Unter dem Strich wirkt die Bewertung derzeit eher einladend: Der Kurs liegt mit spürbarem "
            "Abschlag zum geschätzten fairen Wert, was das Abwärtsrisiko etwas begrenzt.",
        ])
    elif v <= 4:
        p3 = _pick(stock, "trend-expensive", [
            "Insgesamt ist die aktuelle Bewertung eher ein Gegenargument: Der Markt preist bereits recht "
            "viel Optimismus ein, was den Spielraum für weitere Kursgewinne einschränkt und das Risiko "
            "bei Enttäuschungen erhöht.",
            "Unter dem Strich mahnt die Bewertung eher zur Vorsicht: Im aktuellen Kurs steckt schon "
            "einiges an Optimismus, was bei einer Enttäuschung mehr Fallhöhe bedeutet.",
        ])
    else:
        p3 = ("Insgesamt bewegt sich die Bewertung in einem neutralen Bereich – weder ein klarer Rabatt "
              "noch eine deutliche Überhitzung.")
    return [p1, p2, p3]


def _section_big_picture(stock: dict) -> list[str]:
    """Langfristig: das grosse Bild, Moat/Innovation, wohin die Reise geht."""
    name, q = stock["name"], stock.get("quality", 5)
    sector = stock.get("sector", "")
    p1 = _pick(stock, "big-intro", [
        f"Zoomt man ganz heraus, bleibt die eigentlich entscheidende Frage bei {name}: trägt das "
        f"Geschäftsmodell über die kommenden Jahre einen echten, verteidigbaren Vorteil gegenüber der "
        f"Konkurrenz – sei es durch Marke, Skaleneffekte, Netzwerkeffekte oder technologischen Vorsprung? "
        f"Kurzfristige Kursbewegungen, wie die dieser Woche, sagen darüber praktisch nichts aus. Sie sind "
        f"Rauschen um einen langsamer verlaufenden, aber deutlich wichtigeren Trend.",
        f"Mit etwas Distanz betrachtet, zählt bei {name} eigentlich nur eine Frage: Hat das Unternehmen "
        f"über die kommenden Jahre einen Vorteil, den Wettbewerber nicht einfach kopieren können – durch "
        f"Marke, Grösse, Netzwerkeffekte oder technologischen Vorsprung? Was diese Woche am Kurs passiert "
        f"ist, beantwortet diese Frage nicht. Es ist Rauschen über einem viel langsameren, aber "
        f"wichtigeren Trend.",
    ])
    if q >= 6.5:
        p2 = (f"Die aktuellen Kennzahlen deuten darauf hin, dass dieser Vorteil bei {name} nach wie vor "
              f"intakt ist: eine überdurchschnittliche Kapitalrendite und eine stabile Bilanz sind genau die "
              f"Signale, die auf einen funktionierenden Burggraben hindeuten, statt auf ein Geschäft, das "
              f"nur von günstigen Marktbedingungen profitiert.")
    else:
        p2 = (f"Die aktuellen Kennzahlen liefern hier kein eindeutiges Bild – weder ein klarer Beleg für "
              f"einen starken Wettbewerbsvorteil noch ein akutes Warnsignal. Das lohnt sich, in den "
              f"kommenden Quartalen weiter zu beobachten, insbesondere ob sich Marge und Kapitalrendite "
              f"eher verbessern oder verschlechtern.")
    p3 = (f"Strukturell prägend für die {sector or 'Branche'}, in der {name} tätig ist, sind aktuell "
          f"technologische Verschiebungen – von Automatisierung über Dateninfrastruktur bis zu neuen "
          f"KI-gestützten Anwendungen, die bestehende Geschäftsmodelle sowohl bedrohen als auch neue Wege "
          f"eröffnen können. Wer hier auf der richtigen Seite steht, kann seinen Vorsprung über Jahre "
          f"ausbauen; wer den Anschluss verliert, sieht selbst solide Fundamentaldaten schrittweise "
          f"erodieren. Das ist der eigentliche Massstab, an dem sich diese Position über die kommenden "
          f"Jahre messen lassen muss – nicht die Kursbewegung dieser einen Woche.")
    return [p1, p2, p3]


def _template(stock: dict) -> dict:
    return {
        "headline": _headline(stock),
        "weekRange": _week_range(),
        "pages": [
            {"title": "Diese Woche", "paragraphs": _section_week(stock)},
            {"title": "Dieser Trend", "paragraphs": _section_trend(stock)},
            {"title": "Das grosse Bild", "paragraphs": _section_big_picture(stock)},
        ],
    }


def _llm(stock: dict):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        ctx = {k: stock.get(k) for k in ("name", "sector", "status", "quality", "valuation",
               "dislocation", "peNow", "peHist", "drawdown", "signal", "gate_ok")}
        ctx["events"] = stock.get("events", [])[:5]
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=1400,
            messages=[{"role": "user", "content":
                "Du bist Finanzredakteur bei Finvest und schreibst einen vertieften, gut lesbaren "
                "Wochenbericht fuer Privatanleger auf Deutsch -- kein Fachjargon, keine Kaufempfehlung, "
                "aber wirklich informativ und mit Substanz, nicht oberflaechlich. "
                "Antworte NUR als JSON mit: headline (spannungserzeugender Uebertitel), weekRange "
                "(z.B. '30.06. - 06.07.2026'), pages (Array von 3 Objekten mit title und paragraphs "
                "[2-3 Saetze-Absaetze als Array]). Die drei Seiten, von kurz- zu langfristig: "
                "'Diese Woche' (was diese Woche konkret passierte), 'Dieser Trend' (Bewertung/KGV im "
                "eigenen historischen Kontext, mittelfristig), 'Das grosse Bild' (Wettbewerbsvorteil, "
                "Branchentrends wie KI/Innovation, langfristige These).\n\n"
                f"Daten: {json.dumps(ctx, ensure_ascii=False)}"}])
        txt = msg.content[0].text.strip().strip("`")
        if txt.startswith("json"):
            txt = txt[4:]
        data = json.loads(txt)
        if all(k in data for k in ("headline", "weekRange", "pages")) and len(data["pages"]) >= 3:
            return data
    except Exception:
        pass
    return None


def build(stock: dict) -> dict:
    return _llm(stock) or _template(stock)
