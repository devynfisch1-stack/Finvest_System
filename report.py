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
    """Kurzfristig: was ist DIESE Woche konkret passiert."""
    events = sorted(stock.get("events", []), key=lambda e: abs(e.get("m", e.get("move", 0))), reverse=True)
    name = stock["name"]
    if not events:
        return [f"Für {name} gab es in dieser Woche keine grösseren Kursausschläge mit erkennbarem Auslöser. "
                f"Der Kurs bewegte sich im Rahmen des breiten Marktes, ohne dass ein einzelnes Ereignis "
                f"die Richtung vorgegeben hätte. Das ist an sich keine schlechte Nachricht – ruhige Wochen "
                f"sind für langfristig orientierte Anleger oft unauffälliger, aber nicht weniger wichtig, "
                f"weil sie zeigen, dass keine akute Störung im Geschäftsmodell vorliegt."]

    p1_parts = []
    for e in events[:3]:
        move = e.get("m", e.get("move", 0))
        typ = e.get("type", "makro")
        title = e.get("t", e.get("title", ""))
        richtung = "fiel" if move < 0 else "stieg"
        p1_parts.append(f"{richtung} die Aktie um {abs(move):.1f}\u202f% – {ART.get(typ, '')} ({title})")
    p1 = (f"Die auffälligste Bewegung dieser Woche: die Aktie " + "; ausserdem ".join(p1_parts) + ". "
          f"Für die Einschätzung ist entscheidend, ob eine Bewegung von echten Geschäftszahlen getragen wird "
          f"oder eher Ausdruck von Stimmung ist – nur Ersteres verändert den inneren Wert des Unternehmens "
          f"nachhaltig, Zweiteres ist Rauschen, das sich oft wieder relativiert.")

    fun = [e for e in events if e.get("type") == "fundamental"]
    emo = [e for e in events if e.get("type") != "fundamental"]
    if fun and not emo:
        p2 = ("In dieser Woche standen fundamentale Auslöser klar im Vordergrund. Das bedeutet: die "
              "Kursbewegung spiegelt tatsächlich eine veränderte Einschätzung des operativen Geschäfts "
              "wider, nicht nur eine Stimmungsschwankung. Solche Bewegungen verdienen mehr Gewicht in der "
              "eigenen Einschätzung, weil sie in der Regel eine gewisse Halbwertszeit haben.")
    elif emo and not fun:
        p2 = ("Auffällig ist, dass die Bewegung dieser Woche überwiegend nicht durch neue Geschäftszahlen "
              "ausgelöst wurde, sondern durch Stimmung, Positionierung oder die allgemeine Marktlage. "
              "Solche Bewegungen sagen wenig über den langfristigen Wert des Unternehmens aus und kehren "
              "sich häufiger wieder um, sobald sich die Aufmerksamkeit verschiebt.")
    else:
        p2 = ("Diese Woche mischten sich fundamentale und stimmungsgetriebene Impulse. Das macht die "
              "Einordnung etwas anspruchsvoller: ein Teil der Bewegung dürfte bestehen bleiben, ein anderer "
              "Teil ist eher Rauschen, das sich in den kommenden Wochen wieder glätten kann.")
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
        p1 = (f"Zieht man den Blick etwas weiter, zeigt sich {name} beim Kurs-Gewinn-Verhältnis mit {pe} "
              f"gegenüber dem eigenen historischen Schnitt von {peh} rund {diff}\u202f% {rel} bewertet als "
              f"sonst üblich. Das ist mehr als eine Momentaufnahme: es misst die Aktie an ihrer eigenen "
              f"Vergangenheit, nicht an einem willkürlichen Schwellenwert, und ist damit eine der "
              f"aussagekräftigsten Grössen für die Frage, ob der aktuelle Kurs eher eine Chance oder eher "
              f"eine Warnung ist.")
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
        p3 = ("Insgesamt spricht die aktuelle Bewertung eher für die Aktie: Sie handelt mit einem gewissen "
              "Sicherheitsabschlag gegenüber ihrem geschätzten fairen Wert, was zukünftigen Anlegern etwas "
              "mehr Puffer nach unten verschafft.")
    elif v <= 4:
        p3 = ("Insgesamt ist die aktuelle Bewertung eher ein Gegenargument: Der Markt preist bereits recht "
              "viel Optimismus ein, was den Spielraum für weitere Kursgewinne einschränkt und das Risiko "
              "bei Enttäuschungen erhöht.")
    else:
        p3 = ("Insgesamt bewegt sich die Bewertung in einem neutralen Bereich – weder ein klarer Rabatt "
              "noch eine deutliche Überhitzung.")
    return [p1, p2, p3]


def _section_big_picture(stock: dict) -> list[str]:
    """Langfristig: das grosse Bild, Moat/Innovation, wohin die Reise geht."""
    name, q = stock["name"], stock.get("quality", 5)
    sector = stock.get("sector", "")
    p1 = (f"Zoomt man ganz heraus, bleibt die eigentlich entscheidende Frage bei {name}: trägt das "
          f"Geschäftsmodell über die kommenden Jahre einen echten, verteidigbaren Vorteil gegenüber der "
          f"Konkurrenz – sei es durch Marke, Skaleneffekte, Netzwerkeffekte oder technologischen Vorsprung? "
          f"Kurzfristige Kursbewegungen, wie die dieser Woche, sagen darüber praktisch nichts aus. Sie sind "
          f"Rauschen um einen langsamer verlaufenden, aber deutlich wichtigeren Trend.")
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
