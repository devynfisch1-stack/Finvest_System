# Ablauf: hochladen, laufen lassen, Dashboard nutzen

## 1. Repo anlegen & Code hochladen
1. Auf GitHub ein neues (privates) Repository erstellen, z. B. `finvest-fundamental`.
2. Den kompletten Inhalt des Ordners `finvest-backend/` hochladen (inkl. dem
   versteckten Ordner `.github/`). Am einfachsten:
   ```bash
   cd finvest-backend
   git init && git add . && git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/DEINNAME/finvest-fundamental.git
   git push -u origin main
   ```

## 2. Secrets setzen (Repo → Settings → Secrets and variables → Actions)
- `EDGAR_CONTACT` = deine E-Mail (SEC verlangt einen Kontakt im User-Agent) — **Pflicht**
- `FMP_API_KEY` = dein gratis FMP-Key (financialmodelingprep.com, 250 Calls/Tag) — optional, macht US-Daten besser
- `ANTHROPIC_API_KEY` = dein Anthropic-Key — optional, macht News-Klassifikation + Wochenbericht natürlicher

## 3. Erster Lauf
- **Manuell auf GitHub:** Tab **Actions** → Workflow „Fundamental-Analyse (täglich)" → **Run workflow**.
  Danach läuft er automatisch **jeden Morgen um ~05:00** (03:00 UTC).
- **Oder lokal testen:**
  ```bash
  pip install -r requirements.txt
  export EDGAR_UA="Finvest research deine@mail.ch"
  export FMP_API_KEY=...        # optional
  export ANTHROPIC_API_KEY=...  # optional
  python run.py                 # -> data/stocks.json
  ```
- Ergebnis: der Bot committet `data/stocks.json` (+ Snapshot in `data/history/`) zurück ins Repo.

## 4. Dashboard mit echten Daten verbinden
Die Datei ist öffentlich abrufbar unter der **Raw-URL**:
```
https://raw.githubusercontent.com/DEINNAME/finvest-fundamental/main/data/stocks.json
```
Im Dashboard beim Start diese URL laden und die Beispieldaten ersetzen:
```js
const res = await fetch("https://raw.githubusercontent.com/DEINNAME/finvest-fundamental/main/data/stocks.json");
const data = await res.json();      // data.regions.US / data.regions.CH
```
Jeder Titel bringt bereits `report` (Wochenbericht) mit — der Button im Dashboard
zeigt ihn automatisch an; ohne Backend baut das Dashboard den Bericht selbst.

## Wichtig
- Der **Live-Lauf braucht offenes Internet** (sec.gov, Yahoo, FMP). GitHub Actions
  hat das — läuft dort ganz normal. Nur die Test-Sandbox, in der der Code gebaut
  wurde, hatte keinen Netzzugang.
- FMP-Budget: ~88 Calls pro Tageslauf, klar unter 250/Tag.
- Läuft der Bot ohne Secrets, nutzt er die Gratis-Quellen (EDGAR + yfinance) und
  die Text-Vorlage für den Bericht — funktioniert, ist nur etwas weniger fein.
