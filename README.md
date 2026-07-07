# Finvest Fundamental – Backend

Zieht echte Fundamentaldaten, berechnet die drei Blöcke (Qualität / Bewertung /
Dislokation), klassifiziert Abverkäufe und schreibt `data/stocks.json` – genau
die Struktur, die das Finvest-Dashboard lädt.

## Datenquellen

| Baustein | Quelle | Kosten |
|---|---|---|
| US-Bilanzen (10-K/10-Q) | SEC EDGAR `companyfacts` | kostenlos, kein Key (nur User-Agent) |
| CH-Bilanzen | yfinance-Abschlüsse | kostenlos |
| Kurse, ATH, KGV-Historie | yfinance | kostenlos |
| News + Preistreiber | yfinance-Headlines + Event-Study | kostenlos |
| News-Klassifikation (optional besser) | Anthropic-API | API-Key nötig |

## Schnellstart

```bash
pip install -r requirements.txt

# Offline-Selbsttest der Scoring-Engine (kein Internet):
python run.py --mock

# Echtlauf (zieht reale Daten, dauert einige Minuten):
export EDGAR_UA="Finvest research deine@mail.ch"   # SEC verlangt Kontakt
python run.py
# -> data/stocks.json
```

Optional bessere News-Klassifikation:
```bash
export ANTHROPIC_API_KEY=sk-...
```

## Automatisch via GitHub Actions

`.github/workflows/update.yml` läuft jeden Montag und committet die neue
`data/stocks.json`. Im Repo unter **Settings → Secrets** setzen:
- `EDGAR_CONTACT` – deine Kontakt-Mail (für den SEC-User-Agent)
- `ANTHROPIC_API_KEY` – optional

## Gratis-Optimierungen (in dieser Version aktiv)

- **FMP-Gratis-Tier** (250 Calls/Tag, US): echte historische KGV-/EV-Reihe statt
  Naeherung, fertiger Piotroski-Score, geprueftes ROIC. Aktiv, sobald
  `FMP_API_KEY` gesetzt ist. Budget ~90 Calls/Wochenlauf < 250/Tag.
- **Sektor-relative Perzentile**: KGV/ROIC/FCF werden gegen echte Peers im
  gleichen Sektor normalisiert (behebt die Sektorblindheit).
- **Piotroski-F-Score** (0-9), **Beneish-M-Score** (Manipulations-Gate) und
  **Sloan-Accruals** – alle aus vorhandenen Daten berechnet, kostenlos.
- **LLM-News-Klassifikation** als Default, wenn `ANTHROPIC_API_KEY` gesetzt ist.
- **Punkt-in-Zeit-Snapshots**: jeder Lauf schreibt nach `data/history/` und baut
  ueber die Zeit deinen eigenen PIT-Datensatz fuer spaeteres Backtesting auf.

## Wie es rechnet

- **Qualität (45 %)**: ROIC vs. Kapitalkosten, ROIC-Trend, Ertragsqualität
  (Cash Conversion), Margenstabilität, Bilanzstärke, Verwässerung.
- **Bewertung (40 %)**: KGV vs. eigene Historie (Z-Score), EV/EBITDA, P/FCF,
  Reverse-DCF (eingepreistes Wachstum), Margin of Safety (10-Jahres-DCF).
- **Dislokation (15 %)**: Drawdown vom ATH + News-Zerlegung. Jede Bewegung wird
  über die **abnormale Rendite** (Aktie minus Benchmark) marktbereinigt und als
  fundamental / emotional / makro klassifiziert.
- **Gates**: zu schwache Bilanz oder Ertragsqualität deckeln den Score.
- **Status** aus dem 2×2 (Qualität × Bewertung): Outlier / Solid / Neutral /
  Value Trap / Overvalued. Einstiegsfenster-Signal, wenn Qualität intakt +
  Bewertung günstig + Abverkauf emotional.

## Dashboard anbinden

`stocks.json` hat die Form:
```json
{ "generated": "...", "regions": { "US": [ {stock…} ], "CH": [ … ] } }
```
Jeder Titel enthält `ticker, name, domain, overall, status, signal, quality,
valuation, dislocation, quality_sub, valuation_sub, peNow, peHist, drawdown,
impliedGrowth, events, projection, confidence`. Das Frontend ersetzt seine
Beispieldaten einfach durch einen `fetch()` auf diese Datei (z. B. via GitHub
Raw-URL oder in Base44 eingebunden).

## Ehrliche Grenzen

- **KGV-Historie** ist eine Näherung (Jahresend-Kurs / Jahres-EPS) – yfinance
  liefert keine saubere Punkt-in-Zeit-KGV-Reihe. Für Profi-Qualität später eine
  bezahlte Fundamentaldaten-API (z. B. Financial Modeling Prep, Sharadar).
- **News-Klassifikation** ist der schwierigste Teil. Die Schlagwort-Heuristik
  ist ein Startpunkt; die LLM-Option ist deutlich besser, aber keiner von beiden
  ersetzt eine echte, kuratierte Event-Datenbank.
- **XBRL-Tags variieren** je Filer – fehlende Kennzahlen bleiben `None` und
  senken die Konfidenz, statt falsche Werte zu erzwingen.
- yfinance ist inoffiziell und kann sich ändern; für einen Produktivbetrieb ist
  eine bezahlte, stabile Datenquelle empfehlenswert.
- Punkt-in-Zeit-Korrektheit (keine nachträglich revidierten Zahlen) ist für
  echtes Backtesting nötig – hier bewusst noch nicht umgesetzt.
```
