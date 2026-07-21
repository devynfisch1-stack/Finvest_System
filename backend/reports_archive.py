"""
Berichts-Archiv: speichert jeden wöchentlich generierten Bericht dauerhaft
unter data/reports/{ticker}/{datum}.json und pflegt einen Gesamtindex unter
data/reports/index.json (für die "Berichte"-Übersicht im Dashboard -- wie
die Aktienliste, aber mit Firma + Datum je Bericht).
"""
from __future__ import annotations
import json
import os
import datetime as dt

HERE = os.path.dirname(__file__)
REPORTS_DIR = os.path.join(HERE, "data", "reports")


def save_report(ticker: str, name: str, domain: str, region: str, report: dict):
    os.makedirs(os.path.join(REPORTS_DIR, ticker), exist_ok=True)
    today = dt.date.today().isoformat()
    path = os.path.join(REPORTS_DIR, ticker, f"{today}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"ticker": ticker, "name": name, "date": today, **report}, f, ensure_ascii=False, indent=2)
    _update_index(ticker, name, domain, region, today, report.get("headline", ""))


def _update_index(ticker, name, domain, region, date, headline):
    idx_path = os.path.join(REPORTS_DIR, "index.json")
    idx = []
    if os.path.exists(idx_path):
        with open(idx_path, encoding="utf-8") as f:
            idx = json.load(f)
    idx = [e for e in idx if not (e["ticker"] == ticker and e["date"] == date)]  # kein Duplikat
    idx.append({"ticker": ticker, "name": name, "domain": domain, "region": region,
                "date": date, "headline": headline})
    idx.sort(key=lambda e: e["date"], reverse=True)
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx[:200], f, ensure_ascii=False, indent=2)  # 200 neueste behalten
