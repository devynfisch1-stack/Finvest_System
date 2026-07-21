# Ablauf: hochladen, laufen lassen, Dashboard nutzen

## Struktur (neu, seit der Umstellung auf Vercel)
```
/                       <- React/Vite-Frontend liegt HIER im Hauptverzeichnis
  package.json
  vite.config.js
  index.html
  src/App.jsx           <- das Dashboard
  src/main.jsx
  backend/              <- das komplette Python-System, in einem Unterordner
    run.py, config.py, scoring.py, ...
    requirements.txt
    data/                (stocks.json + history/ landen hier)
  .github/workflows/     <- die zwei automatischen Ablaeufe
```
Der Grund fuer diese Aufteilung: Deploy-Dienste wie Vercel suchen automatisch im
**Hauptverzeichnis** nach einer `package.json`. Laege das Frontend in einem
Unterordner, muesste man das manuell konfigurieren (Root Directory) -- das hat
oefter zu Verwirrung gefuehrt. So funktioniert Vercel ohne jede Zusatzeinstellung.

## 1. Repo anlegen & Code hochladen
1. Auf GitHub ein neues (privates) Repository erstellen.
2. Den kompletten Ordnerinhalt hochladen (inkl. `.github/`, `backend/`, `src/`).

## 2. Secrets setzen (Repo -> Settings -> Secrets and variables -> Actions)
- `EDGAR_CONTACT` = deine E-Mail (SEC verlangt einen Kontakt im User-Agent) -- **Pflicht**
- `FMP_API_KEY` = dein gratis FMP-Key (financialmodelingprep.com, 250 Calls/Tag) -- optional
- `ANTHROPIC_API_KEY` = dein Anthropic-Key -- optional, macht Texte natuerlicher

## 3. Erster Lauf (Backend)
- **Auf GitHub:** Tab **Actions** -> Workflow "Fundamental-Analyse (taeglich)" -> **Run workflow**.
  Danach laeuft er automatisch **jeden Morgen um ~05:00** (03:00 UTC).
- Ergebnis: der Bot committet `backend/data/stocks.json` zurueck ins Repo.
- Wochenbericht separat testen: Workflow "Wochenbericht (Sonntag 18:00)" -> **Run workflow**.
  Ergebnis: zusaetzlich `backend/data/reports/` mit dem Berichts-Archiv.

## 4. Frontend auf Vercel deployen
1. Auf vercel.com mit GitHub einloggen, "Add New Project", das Repo auswaehlen.
2. Vercel erkennt automatisch **Vite** als Framework, weil `package.json` jetzt im
   Hauptverzeichnis liegt -- **keine Root-Directory-Einstellung noetig.**
3. "Deploy" klicken. Nach ein paar Minuten gibt es eine Live-URL (`etwas.vercel.app`).
4. Jeder weitere Push auf `main` loest automatisch einen neuen Deploy aus.

Das Dashboard laedt die echten Daten selbst zur Laufzeit von:
```
https://raw.githubusercontent.com/DEINNAME/DEINREPO/main/backend/data/stocks.json
```
Das ist in `src/App.jsx` als `LIVE_DATA_URL` hinterlegt -- anpassen, falls sich
dein GitHub-Nutzername oder Repo-Name aendert.

## Wichtig
- Der **Live-Lauf braucht offenes Internet** (sec.gov, Yahoo, FMP) -- auf GitHub
  Actions kein Problem.
- FMP-Budget: ~88 Calls pro Tageslauf, klar unter 250/Tag.
- Laeuft der Bot ohne `ANTHROPIC_API_KEY`, nutzt er die Gratis-Quellen (EDGAR +
  yfinance) und die eingebaute Text-Vorlage mit sprachlicher Varianz -- voll
  funktionsfaehig, nur sprachlich etwas weniger vielfaeltig.
- Findet das Dashboard keine `stocks.json` (z. B. weil der erste Lauf noch nicht
  passiert ist), zeigt es automatisch die eingebauten Beispieldaten -- nichts bricht.
