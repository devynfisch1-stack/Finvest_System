import React, { useState, useMemo, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import {
  Search, Info, RefreshCw, ChevronLeft, ChevronRight, TrendingUp, TrendingDown, Scale,
  Gauge, BarChart3, X, Zap, Newspaper, Crosshair, AlertTriangle, FileText,
  Flag, Archive, Download, Printer, LayoutGrid, ShieldCheck, LineChart,
} from "lucide-react";

/* ================================================================== */
/*  ENGINE — Quality / Valuation / Dislocation, gates, KGV-vs-history. */
/*  Historical P/E anchors curated (realistic); current price, current */
/*  P/E and ATH-distance illustrative until wired to a live data feed. */
/* ================================================================== */
const clampI = (x) => Math.max(1, Math.min(10, Math.round(x)));
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const hash = (s) => { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) & 0xffffffff; return Math.abs(h); };
const mulberry = (a) => () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const weighted = (o, w) => { let s = 0, tw = 0; for (const k in w) { s += o[k] * w[k]; tw += w[k]; } return s / tw; };

const INFO = {
  quality: { name: "Block: Qualität", w: "45 %", what: "Wie gut das Geschäft an sich ist – Moat, Kapitaleffizienz, Ertragsqualität, Bilanz.", why: "Eine schlechte Firma wird auch günstig selten ein gutes Investment. Qualität ist das Fundament vor jeder Bewertung." },
  valuation: { name: "Block: Bewertung", w: "40 %", what: "Wie günstig die Aktie ist – v.a. aktuelles KGV gegen die eigene Historie, plus EV/EBITDA, P/FCF und Reverse-DCF.", why: "Auch die beste Firma kann zu teuer sein. Hier entscheidet sich die Sicherheitsmarge." },
  dislocation: { name: "Block: Dislokation", w: "15 %", what: "Fehlbewertung durch Sentiment – Abstand vom Allzeithoch und Kategorisierung der Abverkäufe (fundamental vs. emotional).", why: "Emotionaler Abverkauf bei intakten Fundamentaldaten ist das klassische Einstiegsfenster." },
  roic: { name: "ROIC vs. Kapitalkosten", w: "28 %", what: "Return on Invested Capital gegen WACC.", why: "Der stärkste Moat-Indikator: dauerhaft mehr verdienen als das Kapital kostet." },
  roicTrend: { name: "ROIC-Trend / inkrementell", w: "18 %", what: "Richtung des ROIC und Rendite auf NEU investiertes Kapital.", why: "Zeigt die Reinvestitions-Landebahn – reine Niveaus verpassen das." },
  eq: { name: "Ertragsqualität", w: "22 %", what: "Cash Conversion (FCF/Gewinn), Accruals, Piotroski-F- und Beneish-M-Logik.", why: "Deckt auf, ob der Gewinn echt ist oder buchhalterisch aufgehübscht." },
  marginStab: { name: "Margenstabilität", w: "14 %", what: "Stabilität der Marge über den Zyklus.", why: "Stabile Margen = Preissetzungsmacht = echter Wettbewerbsvorteil." },
  balance: { name: "Bilanzstärke (Gate)", w: "12 %", what: "Nettoverschuldung/EBITDA, Zinsdeckung.", why: "Zugleich ein Veto: eine zu schwache Bilanz deckelt den Gesamt-Score, egal wie gut der Rest ist." },
  dilution: { name: "Verwässerung", w: "6 %", what: "Trend der Aktienanzahl.", why: "Wer 'wächst' und dich jährlich verwässert, schafft weniger Wert als er vorgibt." },
  pe: { name: "KGV vs. eigene Historie", w: "34 %", what: "Aktuelles KGV als Abweichung zum eigenen 5–10-Jahres-Median.", why: "Eine der stärksten Einzelmetriken. Nicht 'KGV 18 = günstig', sondern günstig RELATIV zur eigenen Historie – das Mean-Reversion-Signal." },
  ev: { name: "EV/EBITDA vs. Historie", w: "20 %", what: "Enterprise Value zu EBITDA gegen die eigene Historie.", why: "Berücksichtigt Schulden und Abschreibungen – dort, wo das KGV lügt." },
  drawdown: { name: "Abstand vom Allzeithoch", w: "—", what: "Wie weit der Kurs unter seinem letzten Hoch liegt.", why: "Kein Fundamentalwert, sondern ein Dislokations-Input. Stark erst in Kombination mit der News-Kategorisierung." },
  revdcf: { name: "Reverse-DCF", w: "18 %", what: "Welches Wachstum preist der aktuelle Kurs bereits ein?", why: "Dreht den DCF um: statt zu schätzen, prüfst du nur noch, ob die eingepreiste Erwartung realistisch ist." },
  news: { name: "Preistreiber & News", w: "—", what: "Nicht nur die letzten Meldungen, sondern die grössten Kursbewegungen der Aktie – jede klassifiziert als fundamental (Guidance, Zahlen) vs. emotional/makro (Sentiment, Zinsen, Rotation).", why: "Emotionaler Abverkauf bei stabilen Fundamentaldaten = Einstiegsfenster. Fundamentaler Abverkauf = Warnsignal." },
};

/* Reduzierte Farbsprache: nur Schwarz/Weiss/Grau + Blau als Akzent, dazu
   Grün/Rot als einzige Ausnahme für die eine zentrale Gut/Schlecht-Aussage
   (Status-Badge, KGV-Abweichung, Kursrichtung) — wie in professionellen
   Finanz-Tools üblich, nicht als Deko auf jeder einzelnen Kennzahl. */
const GREEN = "#3ecf72", RED = "#e2584f", GRAY = "#8b8d92", BLUE = "#4c9eea";
function hx(c) { const n = parseInt(c.slice(1), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
function mix(c1, c2, t) {
  const [r1, g1, b1] = hx(c1), [r2, g2, b2] = hx(c2);
  return `rgb(${Math.round(r1 + (r2 - r1) * t)},${Math.round(g1 + (g2 - g1) * t)},${Math.round(b1 + (b2 - b1) * t)})`;
}
/* KGV aktuell vs. Historie: je stärker UNTER dem Schnitt, desto grüner; je
   stärker DARÜBER, desto röter. Weiss bei ~0% Abweichung. Deckel bei ±30%. */
function peColor(now, hist) {
  if (now == null || hist == null || !hist) return "#fff";
  const dev = Math.max(-0.3, Math.min(0.3, (now - hist) / hist));
  const t = Math.abs(dev) / 0.3;
  return mix("#ffffff", dev < 0 ? GREEN : RED, t);
}

function statusTone(s) {
  return { Outlier: GREEN, Solid: BLUE, Neutral: GRAY, "Value Trap": RED, Overvalued: RED }[s];
}
/* Metrik-Punkte: monochrome Grau→Blau-Skala statt Regenbogen — zeigt das
   Gefälle klar, ohne dass jede Zeile in einer anderen Farbe leuchtet. */
function scoreColor(s) {
  const c = clamp(s, 1, 10);
  const t = (c - 1) / 9;                                  // 0..1
  const light = 42 + t * 30;                               // dunkelgrau -> hellblau
  const sat = t * 62;
  return `hsl(212, ${sat}%, ${light}%)`;
}

/* -------- curated historical P/E anchors (approx. 5–10y average) -------- */
const PE_HIST = {
  AAPL: 26, MSFT: 32, NVDA: 45, AMZN: 55, GOOGL: 25, META: 24, "BRK.B": 21, LLY: 40, AVGO: 24, JPM: 12,
  V: 32, XOM: 13, UNH: 22, MA: 37, COST: 38, HD: 22, PG: 25, JNJ: 17, KO: 25, UBER: 35, BN: 18, QSR: 22,
  NESN: 21, ROG: 16, NOVN: 15, UBSG: 10, CFR: 22, ZURN: 12, ABBN: 24, LONN: 30, SIKA: 33, HOLN: 12,
  ALC: 32, GIVN: 34, SREN: 11, PGHN: 24, SCMN: 16, SLHN: 11, GEBN: 28, LOGN: 20,
};

/* -------- news: flagship price-drivers mit echten Stichpunkten und einer
   persönlichen Einschätzung im Ton des Finvest-Teams (Meinung, gestützt auf
   Daten) statt trockener Kennzahlen-Auflistung. Templated Fallback darunter. */
const G = (t, m, type, s, bullets, sum) => ({ t, m, type, s, bullets, sum });
const NEWS = {
  MSFT: [
    G("Angst vor hohen KI-Investitionen (Capex)", -6.1, "emotional", "Tief",
      ["Die grossen Cloud-Anbieter erhöhen ihre KI-Infrastruktur-Ausgaben spürbar",
       "Anleger befürchten kurzfristig sinkende Free-Cashflow-Margen",
       "Azure und die Cloud-Nachfrage wachsen im selben Zeitraum weiter zweistellig"],
      "Für uns ist dieser Rückgang um 6,1 % klar eine Überreaktion. Die Sorge um hohe Investitionsausgaben ist nachvollziehbar, übersieht aber, dass Azure weiterhin zweistellig wächst und die Marge intakt bleibt. Aus unserer Sicht bezahlt der Markt hier kurzfristige Nervosität, keine echte Verschlechterung des Geschäfts. Wir behalten die Position im Blick, sehen aber kein Alarmsignal."),
    G("Makro-Zinssorgen belasten Tech breit", -3.2, "makro", "Tief",
      ["Zinserwartungen belasten den gesamten Tech-Sektor, nicht nur Microsoft",
       "Der Rücksetzer ist indexgetrieben, kein firmenspezifischer Auslöser",
       "Vergleichbare Bewegungen sahen wir zuletzt auch bei anderen Mega-Caps"],
      "Diese Bewegung würden wir nicht überbewerten – sie hat wenig mit Microsoft selbst zu tun und viel mit der allgemeinen Zinsdiskussion. Wenn der ganze Sektor gleichzeitig nachgibt, ist das Makro-Beta, kein Urteil über das einzelne Geschäft. Wir würden hier eher an den Fundamentaldaten festhalten als am Kursverlauf dieser Woche."),
    G("Azure-Cloud-Wachstum über Erwartung", 4.8, "fundamental", "Hoch",
      ["Azure wächst schneller als vom Markt erwartet",
       "Die Marge lag über dem Analysten-Konsens",
       "Die Cloud-Nachfrage zeigt keine Anzeichen einer Abschwächung"],
      "Das ist für uns die Art von Nachricht, die wirklich zählt. Ein Wachstum über Erwartung bei gleichzeitig stabiler Marge bestätigt genau die These, auf der unsere positive Einschätzung zu Microsoft beruht. Wir werten das als eines der stärkeren fundamentalen Signale der letzten Wochen."),
  ],
  NVDA: [
    G("Rotation aus KI-Highflyern (kein Firmennews)", -8.4, "emotional", "Tief",
      ["Anleger nehmen nach dem starken Lauf Gewinne mit",
       "Es gibt keine neue Unternehmensmeldung, die den Rückgang erklärt",
       "Ähnliche Rotationen sahen wir bereits mehrfach im aktuellen KI-Zyklus"],
      "Ein Rückgang von über 8 % klingt dramatisch, ist für uns aber vor allem Positionsbereinigung nach einem starken Lauf. Ohne neue Unternehmensmeldung sehen wir keinen Grund, an der fundamentalen Story etwas zu ändern. Für uns bleibt das Rauschen, nicht Substanz."),
    G("Rechenzentrums-Umsatz erneut Rekord", 6.2, "fundamental", "Hoch",
      ["Der Umsatz im Rechenzentrumsgeschäft erreichte einen neuen Rekord",
       "Sowohl Nachfrage als auch Marge lagen über den Erwartungen",
       "Das bestätigt die zentrale These hinter der aktuellen Bewertung"],
      "Genau das wollten wir sehen: ein weiterer Rekord im margenstärksten Segment. Für uns bestätigt das die These, dass die Nachfrage nach KI-Rechenleistung noch lange nicht ausgereizt ist. Wir sehen darin ein starkes fundamentales Signal für die kommenden Quartale."),
    G("China-Exportbeschränkungen (Schlagzeile)", -3.8, "fundamental", "Mittel",
      ["Neue regulatorische Beschränkungen betreffen einen Teil des China-Geschäfts",
       "Der Umsatzanteil ist real, aber begrenzt",
       "Bislang keine Anzeichen für eine Ausweitung auf andere Regionen"],
      "Diesen Punkt nehmen wir ernster als reine Sentiment-Nachrichten, weil hier ein echter Umsatzbezug besteht. Ganz abtun würden wir das nicht, auch wenn der betroffene Anteil überschaubar bleibt. Wir behalten das als einen der wenigen Punkte mit echtem Beobachtungsbedarf im Blick."),
  ],
  AAPL: [
    G("China-Absatzsorgen (Presseberichte)", -4.1, "emotional", "Mittel",
      ["Presseberichte deuten auf schwächere iPhone-Verkäufe in China hin",
       "Bislang gibt es dazu keine bestätigten harten Zahlen",
       "Der Kurs reagierte deutlicher, als die Faktenlage bisher hergibt"],
      "Für uns ist das aktuell mehr Schlagzeile als Fakt. Solange keine bestätigten Zahlen vorliegen, behandeln wir das als Sentiment-Risiko und nicht als erwiesene Schwäche. Trotzdem behalten wir China im Auge, weil dort tatsächlich ein reales Risiko für Apple liegt – nur eben noch unbestätigt."),
    G("Services-Marge über Erwartung", 3.0, "fundamental", "Mittel",
      ["Das margenstarke Services-Geschäft übertraf die Erwartungen",
       "Das stützt die Diversifizierung weg vom reinen Hardware-Geschäft",
       "Die Wiederholrate bei Abonnements bleibt stabil"],
      "Das ist für uns eine der unterschätzten Stärken bei Apple: Services liefert zuverlässig und mit hoher Marge, während die Aufmerksamkeit meist auf dem iPhone-Zyklus liegt. Wir sehen darin ein solides, wenn auch wenig spektakuläres Signal für die Substanz des Geschäfts."),
    G("Sorge um iPhone-Zyklus", -2.6, "emotional", "Tief",
      ["Zweifel am nächsten Upgrade-Zyklus kursieren ohne konkrete Datenbasis",
       "Vergleichbare Sorgen gab es bereits vor früheren Zyklen",
       "Bisher liegt keine belastbare Verkaufszahl vor, die das stützt"],
      "Diese Art Sorge kennen wir vor praktisch jedem iPhone-Zyklus, und sie hat sich in der Vergangenheit selten bestätigt. Ohne konkrete Verkaufszahlen ist das für uns Spekulation, keine Einschätzung auf Faktenbasis. Wir würden hier abwarten statt vorschnell zu reagieren."),
  ],
  GOOGL: [
    G("Kartellrechts-Schlagzeilen", -5.0, "emotional", "Tief",
      ["Neue kartellrechtliche Schlagzeilen dominieren die Berichterstattung",
       "Ein kurzfristiger operativer Effekt ist bislang nicht erkennbar",
       "Vergleichbare Verfahren zogen sich in der Vergangenheit über Jahre hin"],
      "Wir nehmen regulatorische Risiken bei Google grundsätzlich ernst, aber diese Reaktion wirkt uns überzogen für das, was bisher bekannt ist. Solche Verfahren ziehen sich erfahrungsgemäss lange hin, ohne das operative Geschäft kurzfristig zu belasten. Für uns überwiegt hier die Schlagzeile die tatsächliche Faktenlage."),
    G("Werbeumsatz beschleunigt", 4.4, "fundamental", "Hoch",
      ["Der Werbeumsatz wuchs schneller als im Vorquartal",
       "Das Kerngeschäft zeigt keine Anzeichen von Reife oder Sättigung",
       "Cloud liefert zusätzlich einen wachsenden Wachstumsbeitrag"],
      "Das ist für uns das eigentlich relevante Signal der Woche: Das Kerngeschäft beschleunigt statt zu stagnieren. Wir sehen darin eine Bestätigung, dass die Sorgen um ein reifes, langsamer wachsendes Werbegeschäft aktuell nicht zutreffen."),
  ],
  META: [
    G("Sorge um Metaverse-Ausgaben", -5.6, "emotional", "Tief",
      ["Die hohen Reality-Labs-Ausgaben stehen erneut in der Kritik",
       "Das Werbegeschäft selbst bleibt davon unberührt und stark",
       "Der Markt bestraft die Ausgabenseite stärker als er die Ertragsseite honoriert"],
      "Wir verstehen die Skepsis gegenüber den Metaverse-Investitionen, sehen aber einen wichtigen Unterschied: Das Kerngeschäft mit Werbung läuft davon völlig unberührt weiter stark. Für uns überwiegt aktuell die Sorge um Ausgaben die tatsächliche Ertragslage – das halten wir für eine Fehlgewichtung des Marktes."),
    G("Nutzer & Werbemarge stark", 5.1, "fundamental", "Hoch",
      ["Nutzerwachstum und Monetarisierung lagen beide über Erwartung",
       "Die Werbemarge verbesserte sich gegenüber dem Vorquartal",
       "Das bestätigt die Stabilität des Kerngeschäfts trotz der Ausgabendiskussion"],
      "Das ist für uns der Gegenbeweis zur Ausgabensorge: Nutzerzahlen und Marge entwickeln sich klar in die richtige Richtung. Wir werten das als eines der stärkeren Argumente dafür, dass die Substanz bei Meta intakt bleibt, unabhängig von der Diskussion um Zukunftsinvestitionen."),
  ],
  "BRK.B": [
    G("Marktbreiter Rücksetzer (Beta)", -3.4, "makro", "Tief",
      ["Der Rückgang folgt einer breiten Marktbewegung, nicht firmenspezifischen Gründen",
       "Berkshires defensive Positionierung dämpft solche Bewegungen meist zusätzlich",
       "Keine neuen Meldungen aus dem Portfolio oder dem operativen Geschäft"],
      "Bei einem so breit diversifizierten Konglomerat wie Berkshire ordnen wir Bewegungen wie diese fast immer dem Gesamtmarkt zu, nicht dem Unternehmen selbst. Für uns ist das ein Non-Ereignis, das sich mit der Marktbreite erklärt, nicht mit irgendetwas, das Berkshire betrifft."),
    G("Rekord-Cashposition im Bericht", 1.8, "fundamental", "Mittel",
      ["Der Cashbestand erreichte einen neuen Höchststand",
       "Das verschafft Spielraum für Zukäufe bei einer Marktkorrektur",
       "Es zeigt zugleich, dass aktuell wenig attraktiv bewertete Ziele gefunden werden"],
      "Eine hohe Cashposition lesen wir bei Berkshire immer zweifach: als Stärke, weil sie Optionalität schafft, aber auch als Signal, dass das Management aktuell wenig überzeugende Kaufgelegenheiten sieht. Für uns überwiegt der positive Aspekt – Pulver trocken zu halten ist selten ein Fehler."),
  ],
  NESN: [
    G("Konsumgüter-Sektor out of favour", -3.9, "emotional", "Tief",
      ["Der gesamte defensive Konsumgütersektor verlor an Zuspruch",
       "Kein unternehmensspezifischer Auslöser bei Nestlé selbst erkennbar",
       "Rotation in zyklischere Sektoren scheint der Haupttreiber zu sein"],
      "Diese Schwäche lastet unserer Einschätzung nach auf dem ganzen Sektor, nicht spezifisch auf Nestlé. Wenn Anleger in zyklischere Titel rotieren, trifft das defensive Namen wie diesen fast automatisch, unabhängig von der eigentlichen Geschäftsentwicklung. Wir sehen das als vorübergehende Stimmungsfrage."),
    G("Organisches Wachstum unter Plan", -2.1, "fundamental", "Mittel",
      ["Das organische Umsatzwachstum blieb leicht unter den eigenen Zielen",
       "Volumen entwickelte sich schwächer als Preis",
       "Kein Strukturbruch, aber ein realer, wenn auch milder Dämpfer"],
      "Das ist einer der wenigen Punkte, die wir bei Nestlé aktuell wirklich im Auge behalten. Ein verfehltes Wachstumsziel ist kein Drama, aber es ist auch kein Nichts – wir würden das über die nächsten Quartale weiterverfolgen, um zu sehen, ob sich ein Muster verfestigt."),
  ],
  ROG: [
    G("Pharma-Rotation (kein Studien-Setback)", -4.2, "emotional", "Tief",
      ["Der gesamte Pharma-Sektor gab nach, ohne unternehmensspezifischen Auslöser",
       "Keine negativen Studienergebnisse oder Zulassungsprobleme bei Roche",
       "Vergleichbare Sektorrotationen gab es in den letzten Quartalen mehrfach"],
      "Ohne einen negativen Studienauslöser sehen wir hier vor allem Sektor-Rotation am Werk, nicht ein Problem bei Roche selbst. Für uns ist das genau die Art Rücksetzer, die sich häufig innerhalb weniger Wochen wieder relativiert, wenn keine echten Nachrichten dahinterstehen."),
    G("Pipeline-Meilenstein erreicht", 3.6, "fundamental", "Hoch",
      ["Ein wichtiger Meilenstein in der Studienpipeline wurde erreicht",
       "Das stärkt die mittelfristigen Wachstumsaussichten",
       "Der Markt reagierte mit spürbarem, aber nicht übertriebenem Kursplus"],
      "Pipeline-Fortschritte wie dieser sind für uns bei einem Pharmakonzern eines der aussagekräftigsten Signale überhaupt, weil sie direkt die zukünftige Ertragsbasis betreffen. Wir werten das als einen der stärkeren fundamentalen Datenpunkte der letzten Zeit."),
  ],
};

/* Templated Fallback für alle übrigen Titel: type-basierte Stichpunkte und
   eine kurze persönliche Einordnung im gleichen Ton. */
function fallbackBullets(title, type, move) {
  if (type === "fundamental") return [
    `${title} beruht auf echten Geschäftszahlen, nicht auf Stimmung`,
    `Der Kurs reagierte mit ${move > 0 ? "+" : ""}${move}\u202f%`,
    "Solche Bewegungen haben erfahrungsgemäss mehr Bestand als reine Sentiment-Ausschläge",
  ];
  if (type === "makro") return [
    `${title} betrifft den Gesamtmarkt, nicht nur diesen Titel`,
    `Der Kurs bewegte sich um ${move > 0 ? "+" : ""}${move}\u202f%, im Einklang mit dem breiten Markt`,
    "Für die Einzelaktie sagt das wenig über die operative Verfassung aus",
  ];
  return [
    `${title} sorgt kurzfristig für Verunsicherung`,
    "Bislang keine bestätigten Zahlen, die das rechtfertigen würden",
    `Der Kurs reagierte mit ${move > 0 ? "+" : ""}${move}\u202f%, obwohl sich am Geschäft nichts geändert hat`,
  ];
}
function fallbackSum(name, type, move) {
  if (type === "fundamental") return `Das ist für uns die Art von Nachricht, die tatsächlich zählt: ein Effekt von ${move > 0 ? "+" : ""}${move}\u202f%, der auf echten Zahlen beruht statt auf Stimmung. Wir gewichten solche Bewegungen in unserer Einschätzung von ${name} stärker als reines Marktrauschen, weil sie in der Regel eine gewisse Halbwertszeit haben. Für uns bleibt das ein solides, sachlich begründetes Signal.`;
  if (type === "makro") return `Diese Bewegung bei ${name} würden wir nicht überbewerten – sie hängt unserer Einschätzung nach mehr am Gesamtmarkt als am Unternehmen selbst. Wenn ein ganzer Sektor oder Index sich gleichzeitig bewegt, ist das Makro-Beta, kein eigenständiges Urteil über die Substanz. Wir würden uns hier eher an den Fundamentaldaten orientieren als am Kurs dieser Woche.`;
  return `Für uns liest sich das aktuell mehr wie eine Stimmungsreaktion als wie ein fundamentales Problem bei ${name}. Solange keine bestätigten Zahlen vorliegen, die diese Bewegung von ${move > 0 ? "+" : ""}${move}\u202f% rechtfertigen, behandeln wir das mit Vorsicht statt es überzubewerten. Trotzdem verfolgen wir das weiter, weil sich Sentiment gelegentlich als Vorbote echter Probleme entpuppt.`;
}

const DOWN_EMO = ["Sektorrotation belastet", "Zins-/Makrosorgen drücken breit", "Gewinnmitnahmen nach Lauf", "Risk-off-Stimmung"];
const DOWN_FUN = ["Guidance gesenkt", "Margendruck im Kerngeschäft", "Auftragseingang schwächer"];
const UP_FUN = ["Gewinn über Erwartung", "Guidance angehoben", "Grossauftrag gewonnen"];
function genNews(ticker, name, rnd, cheap) {
  if (NEWS[ticker]) return NEWS[ticker];
  const ev = [];
  const emo = rnd() < (cheap ? 0.7 : 0.45);
  const dPool = emo ? DOWN_EMO : DOWN_FUN;
  const t1 = dPool[Math.floor(rnd() * dPool.length)];
  const type1 = emo ? (rnd() < 0.5 ? "emotional" : "makro") : "fundamental";
  const m1 = -+(3 + rnd() * 5).toFixed(1);
  ev.push(G(t1, m1, type1, emo ? "Tief" : "Hoch", fallbackBullets(t1, type1, m1), fallbackSum(name, type1, m1)));
  const t2 = UP_FUN[Math.floor(rnd() * UP_FUN.length)], m2 = +(2 + rnd() * 4).toFixed(1);
  ev.push(G(t2, m2, "fundamental", "Hoch", fallbackBullets(t2, "fundamental", m2), fallbackSum(name, "fundamental", m2)));
  const t3 = "Marktbreiter Rücksetzer", m3 = -+(2 + rnd() * 3).toFixed(1);
  ev.push(G(t3, m3, "makro", "Tief", fallbackBullets(t3, "makro", m3), fallbackSum(name, "makro", m3)));
  return ev;
}

const FINANCIALS = new Set(["UBSG", "ZURN", "SREN", "SLHN", "JPM"]);
const DATES = ["02.04.2026", "28.03.2026", "12.03.2026", "24.02.2026", "05.02.2026", "20.01.2026"];

function computeStock(row, region) {
  const [ticker, name, domain, cap, subs] = row;
  const rnd = mulberry(hash(ticker));
  const isFin = FINANCIALS.has(ticker);

  const qIn = { roic: subs[0], roicTrend: clampI((subs[0] + subs[3]) / 2), eq: clampI((subs[2] + subs[5]) / 2), marginStab: subs[5], balance: subs[4], dilution: subs[7] };
  const q = weighted(qIn, { roic: 28, roicTrend: 18, eq: 22, marginStab: 14, balance: 12, dilution: 6 });

  const relval = subs[6], mos = subs[1];
  const peHist = PE_HIST[ticker] || +(16 + (q - 5) * 1.6).toFixed(1);
  const peDev = ((5.5 - relval) / 9) * 0.5;
  const peNow = +(peHist * (1 + peDev)).toFixed(1);
  const evHist = +(peHist * 0.72).toFixed(1), evNow = +(peNow * 0.72).toFixed(1);
  const revScore = isFin ? 5 : mos;
  const v = weighted({ pe: relval, ev: clampI((relval * 2 + subs[0]) / 3), pfcf: clampI((relval + subs[2]) / 2), rev: revScore, mos }, { pe: 34, ev: 20, pfcf: 16, rev: 18, mos: 12 });
  const impliedGrowth = Math.max(0, Math.round((peNow - 8) * 0.9));
  const realistic = impliedGrowth <= Math.round(subs[3] * 2.2) + 3;
  const drawdown = -clamp(8 + rnd() * 26 + (10 - relval) * 1.3, 5, 60);

  const cheap = v >= 6;
  const events = genNews(ticker, name, rnd, cheap).map((e, i) => ({ ...e, d: DATES[i % DATES.length] }));
  let emoDown = 0, funDown = 0;
  events.forEach((e) => { if (e.m < 0) { if (e.type === "fundamental") funDown += -e.m; else emoDown += -e.m; } });
  const emotional = emoDown > funDown && emoDown > 0;
  let disl = 5;
  if (emotional) disl += 2; if (v >= 6) disl += 1.5; if (q >= 6.5) disl += 1.5;
  if (funDown > emoDown) disl -= 2.2; if (drawdown < -30) disl += 0.5;
  disl = clamp(disl, 1, 10);
  const signal = emotional && q >= 6.5 && v >= 5.5;
  let verdict;
  if (funDown > emoDown && funDown > 0) verdict = { txt: "Jüngste Schwäche ist fundamental begründet – Vorsicht, kein reines Sentiment.", warn: true };
  else if (emotional) verdict = { txt: q >= 6.5 ? "Schwäche überwiegend emotional/makrogetrieben – Fundamentaldaten intakt. Mögliches Einstiegsfenster." : "Schwäche emotional getrieben, Qualität aber nicht überzeugend.", warn: false, good: q >= 6.5 };
  else verdict = { txt: "Jüngste Bewegung fundamental gestützt.", warn: false, good: true };

  const gate = qIn.balance >= 3 && qIn.eq >= 3;
  let overall = q * 0.45 + v * 0.4 + disl * 0.15;
  if (!gate) overall = Math.min(overall, 4);
  let status;
  if (!gate) status = "Overvalued";
  else if (q >= 6.5 && v >= 6.0) status = "Outlier";
  else if (q >= 6.5 && v < 6.0) status = "Solid";
  else if (q < 4.5 && v >= 6.0) status = "Value Trap";
  else if (q >= 5.5 && v >= 5.5) status = "Solid";
  else if (v >= 6.0 && q >= 4.5) status = "Neutral";
  else if (q >= 6.5) status = "Solid";
  else status = v < 4.5 ? "Overvalued" : "Neutral";
  const confidence = Math.round(clamp(60 + Math.min(cap / 50, 22) - (realistic ? 0 : 9) - (region === "CH" && cap < 30 ? 6 : 0) - (isFin ? 4 : 0), 45, 92));

  return { ticker, name, domain, cap: +cap, region, isFin, q, v, disl, overall, status, signal, confidence, qIn, peHist, peNow, evHist, evNow, drawdown, impliedGrowth, realistic, events, verdict, gate };
}

const US = [
  ["AAPL","Apple","apple.com",3450,[8,3,4,6,7,9,3,8]],["MSFT","Microsoft","microsoft.com",3300,[9,4,4,8,8,9,5,8]],
  ["NVDA","NVIDIA","nvidia.com",3100,[9,3,3,9,8,9,4,7]],["AMZN","Amazon","amazon.com",2100,[6,5,4,8,6,6,5,7]],
  ["GOOGL","Alphabet","google.com",2050,[8,6,6,7,9,8,7,7]],["META","Meta Platforms","meta.com",1450,[8,6,7,7,8,8,6,6]],
  ["BRK.B","Berkshire Hathaway","berkshirehathaway.com",1050,[7,7,6,6,10,7,7,9]],["LLY","Eli Lilly","lilly.com",820,[8,2,2,9,6,8,2,6]],
  ["AVGO","Broadcom","broadcom.com",790,[8,3,4,8,5,8,3,7]],["JPM","JPMorgan Chase","jpmorganchase.com",720,[6,6,7,5,7,6,6,8]],
  ["V","Visa","visa.com",640,[9,4,5,7,9,10,4,8]],["XOM","Exxon Mobil","exxonmobil.com",560,[6,7,8,4,7,5,7,7]],
  ["UNH","UnitedHealth","unitedhealthgroup.com",520,[7,7,6,7,6,7,7,6]],["MA","Mastercard","mastercard.com",470,[9,3,5,8,8,10,3,8]],
  ["COST","Costco","costco.com",420,[8,2,3,7,7,9,2,8]],["HD","Home Depot","homedepot.com",390,[8,5,6,5,6,8,6,7]],
  ["PG","Procter & Gamble","pg.com",380,[7,6,5,4,7,8,6,7]],["JNJ","Johnson & Johnson","jnj.com",360,[7,7,6,4,8,8,7,7]],
  ["KO","Coca-Cola","coca-colacompany.com",290,[7,5,5,4,6,9,5,7]],["UBER","Uber","uber.com",270,[5,5,4,9,5,5,4,6]],
  ["BN","Brookfield","brookfield.com",110,[6,7,6,7,5,6,7,7]],["QSR","Restaurant Brands","rbi.com",95,[6,7,7,5,5,7,7,6]],
];
const CH = [
  ["NESN","Nestlé","nestle.com",240,[7,7,5,4,6,8,7,7]],["ROG","Roche","roche.com",230,[8,7,6,5,6,8,7,7]],
  ["NOVN","Novartis","novartis.com",210,[7,7,6,5,7,8,7,7]],["UBSG","UBS Group","ubs.com",95,[5,6,7,5,5,5,6,6]],
  ["CFR","Richemont","richemont.com",95,[7,6,6,6,8,8,6,7]],["ZURN","Zurich Insurance","zurich.com",78,[6,6,7,5,7,7,6,7]],
  ["ABBN","ABB","abb.com",72,[7,5,5,6,7,7,5,6]],["LONN","Lonza","lonza.com",55,[7,4,4,7,5,7,4,6]],
  ["SIKA","Sika","sika.com",48,[8,4,5,7,5,8,4,7]],["HOLN","Holcim","holcim.com",44,[6,7,7,5,6,6,7,6]],
  ["ALC","Alcon","alcon.com",42,[6,5,5,6,5,7,5,6]],["GIVN","Givaudan","givaudan.com",38,[7,3,4,6,5,8,3,7]],
  ["SREN","Swiss Re","swissre.com",38,[6,7,7,4,6,6,7,7]],["PGHN","Partners Group","partnersgroup.com",32,[8,4,5,7,5,8,4,7]],
  ["SCMN","Swisscom","swisscom.ch",28,[6,6,6,3,5,7,6,6]],["SLHN","Swiss Life","swisslife.ch",22,[6,7,7,4,7,6,7,7]],
  ["GEBN","Geberit","geberit.com",21,[8,5,6,4,6,9,5,7]],["LOGN","Logitech","logitech.com",13,[7,6,7,4,8,7,6,6]],
];
const UNIVERSE = {
  US: US.map((r) => computeStock(r, "US")).sort((a, b) => b.cap - a.cap),
  CH: CH.map((r) => computeStock(r, "CH")).sort((a, b) => b.cap - a.cap),
};

function priceSeries(stock, tf) {
  const [pts, step] = { "1M": [22, 1], "6M": [26, 4], "1J": [24, 15], "5J": [30, 60] }[tf];
  let seed = hash(stock.ticker + tf);
  const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
  const drift = (stock.overall - 5.5) * 0.0016;
  let price = 60 + (hash(stock.ticker) % 240);
  const out = [], now = new Date();
  for (let i = pts - 1; i >= 0; i--) {
    const d = new Date(now); d.setDate(now.getDate() - i * step);
    price = Math.max(5, price * (1 + drift + (rnd() - 0.5) * 0.05));
    out.push({ t: d.toLocaleDateString("de-CH", { day: "2-digit", month: "short" }), p: +price.toFixed(2) });
  }
  return out;
}
function projection(s) {
  const a = (s.overall - 5) * 3.2 + 8, comp = (r) => (Math.pow(1 + r / 100, 3) - 1) * 100;
  return { annual: a, base3: comp(a), low3: comp(a - 9), high3: comp(a + 9), prob: Math.round(clamp(42 + (s.overall - 5) * 8, 30, 88)) };
}

/* Markenfarbene Logo-Badges — funktionieren garantiert überall (auch in der
   abgeschotteten Artefakt-Vorschau), da keine externe Bildanfrage nötig ist.
   Auf einer echten Website (Base44 etc.) kann zusätzlich USE_REMOTE_LOGOS
   aktiviert werden, um echte Firmenlogos per Bild-URL zu laden. */
const USE_REMOTE_LOGOS = false; // auf true setzen, wenn ausserhalb der Vorschau (eigene Website) gehostet

const BRAND = {
  AAPL: "#a8a8ad", MSFT: "#00a4ef", NVDA: "#76b900", AMZN: "#ff9900", GOOGL: "#4285f4",
  META: "#0866ff", "BRK.B": "#7a1f2b", LLY: "#d52b1e", AVGO: "#cc0000", JPM: "#5a2d81",
  V: "#1a1f71", XOM: "#d0006f", UNH: "#002677", MA: "#eb001b", COST: "#e31837",
  HD: "#f96302", PG: "#004a9c", JNJ: "#d3242a", KO: "#f40009", UBER: "#000000",
  BN: "#f2a900", QSR: "#00693e",
  NESN: "#0057a8", ROG: "#0060a9", NOVN: "#0060a9", UBSG: "#e60100", CFR: "#8a6d3b",
  ZURN: "#0057a8", ABBN: "#ff000f", LONN: "#00539b", SIKA: "#e2001a", HOLN: "#00549f",
  ALC: "#0091da", GIVN: "#f39200", SREN: "#e2001a", PGHN: "#00447c", SCMN: "#0057b8",
  SLHN: "#0f3c5f", GEBN: "#00543d", LOGN: "#00b8fc",
};
function brandColor(ticker) {
  if (BRAND[ticker]) return BRAND[ticker];
  const h = hash(ticker) % 360;
  return `hsl(${h}, 55%, 45%)`;
}
function initialsOf(name) {
  const words = name.replace(/[^\w\s.&]/g, "").split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}
function Badge({ stock, size }) {
  const bg = brandColor(stock.ticker);
  return (
    <div style={{ width: size, height: size, borderRadius: size * 0.28, flexShrink: 0,
      background: `linear-gradient(150deg, ${bg}, ${bg}cc)`, display: "flex", alignItems: "center",
      justifyContent: "center", fontWeight: 800, fontSize: size * 0.36, color: "#fff",
      fontFamily: "var(--sans)", letterSpacing: 0.2, border: "1px solid rgba(255,255,255,.08)" }}>
      {initialsOf(stock.name)}
    </div>
  );
}
function logoSources(domain) {
  return [
    `https://logo.clearbit.com/${domain}`,
    `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
    `https://icons.duckduckgo.com/ip3/${domain}.ico`,
  ];
}
function Logo({ stock, size = 42 }) {
  const srcs = useMemo(() => logoSources(stock.domain), [stock.domain]);
  const [i, setI] = useState(0);
  useEffect(() => { setI(0); }, [stock.domain]);
  if (!USE_REMOTE_LOGOS || i >= srcs.length) return <Badge stock={stock} size={size} />;
  return (
    <img src={srcs[i]} key={srcs[i]} onError={() => setI((n) => n + 1)} alt={stock.name}
      width={size} height={size} style={{ borderRadius: size * 0.28, background: "#fff", objectFit: "contain", padding: size * 0.14, flexShrink: 0, border: "1px solid #1c1c22" }} />
  );
}
const Dot = ({ v }) => <span style={{ width: 9, height: 9, borderRadius: 5, background: scoreColor(v), display: "inline-block", flexShrink: 0 }} />;

/* ================================================================== */
export default function App() {
  const [region, setRegion] = useState("US");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [tf, setTf] = useState("1J");
  const [stamp, setStamp] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState(null);
  const [favorites, setFavorites] = useState(() => new Set());
  const [archive, setArchive] = useState([]);        // [{ticker,name,domain,region,date,headline}]
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archivePick, setArchivePick] = useState(null); // {ticker,region,date}

  const list = useMemo(() => {
    const q = query.trim().toLowerCase(), base = UNIVERSE[region];
    return q ? base.filter((s) => s.name.toLowerCase().includes(q) || s.ticker.toLowerCase().includes(q)) : base;
  }, [region, query]);
  const stock = selected ? UNIVERSE[selected.region].find((s) => s.ticker === selected.ticker) : null;
  const series = useMemo(() => (stock ? priceSeries(stock, tf) : []), [stock, tf, stamp]);
  useEffect(() => { setTf("1J"); }, [selected]);
  const refresh = () => { setBusy(true); setTimeout(() => { setBusy(false); setStamp(Date.now()); }, 1400); };

  const toggleFavorite = (ticker) => setFavorites((prev) => {
    const next = new Set(prev);
    next.has(ticker) ? next.delete(ticker) : next.add(ticker);
    return next;
  });

  const onArchive = (st, data) => {
    const today = new Date().toISOString().slice(0, 10);
    setArchive((prev) => {
      if (prev.some((e) => e.ticker === st.ticker && e.date === today)) return prev;
      return [{ ticker: st.ticker, name: st.name, domain: st.domain, region: st.region, date: today, headline: data.headline }, ...prev].slice(0, 200);
    });
  };

  const archiveStock = archivePick ? UNIVERSE[archivePick.region].find((s) => s.ticker === archivePick.ticker) : null;

  return (
    <div style={S.root}>
      <style>{CSS}</style>
      <header style={S.header}>
        <div style={{ width: 34 }} />
        <div style={S.wordmark}>Finvest</div>
        <button style={S.headerIconBtn} onClick={() => setArchiveOpen(true)} aria-label="Berichte"><Archive size={18} /></button>
      </header>
      <div style={S.blueLine} />
      {archiveOpen ? (
        <ReportsOverview archive={archive} onBack={() => setArchiveOpen(false)}
          onPick={(e) => { setArchivePick(e); setArchiveOpen(false); }} />
      ) : !stock
        ? <ListView {...{ list, region, setRegion, query, setQuery, onPick: setSelected, stamp, favorites, toggleFavorite }} />
        : <DetailView {...{ stock, series, tf, setTf, onBack: () => setSelected(null), onInfo: setInfo, busy, refresh, onArchive }} />}
      {!stock && !archiveOpen && <button style={S.fab} onClick={refresh} disabled={busy} aria-label="Aktualisieren"><RefreshCw size={22} className={busy ? "spin" : ""} color="#fff" /></button>}
      {info && <InfoModal info={info} onClose={() => setInfo(null)} />}
      {archiveStock && <ReportViewer stock={archiveStock} date={archivePick.date} onClose={() => setArchivePick(null)} onArchive={() => {}} />}
    </div>
  );
}

function ReportsOverview({ archive, onBack, onPick }) {
  return (
    <div style={S.body}>
      <div style={S.detailTop}>
        <button style={S.back} onClick={onBack}><ChevronLeft size={17} /> Übersicht</button>
      </div>
      <h1 style={S.title}>Berichte</h1>
      <p style={S.subtitle}>Alle bisher geöffneten Wochenberichte, gesammelt an einem Ort.</p>
      <div style={S.list}>
        {archive.length === 0 && (
          <div style={S.empty}>Noch keine Berichte geöffnet. Öffne bei einer Aktie den „Wochenbericht ansehen"-Button — er erscheint danach hier.</div>
        )}
        {archive.map((e, i) => (
          <button key={e.ticker + e.date + i} className="card" style={S.card} onClick={() => onPick(e)}>
            <Logo stock={e} size={42} />
            <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
              <div style={S.cardName}>{e.name} Report</div>
              <div style={S.cardTicker}>{new Date(e.date).toLocaleDateString("de-CH", { day: "2-digit", month: "long", year: "numeric" })}</div>
            </div>
            <ChevronRight size={17} color="#5a5a60" />
          </button>
        ))}
      </div>
    </div>
  );
}

function InfoModal({ info, onClose }) {
  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.modal} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <h3 style={{ margin: 0, fontSize: 16, color: "#fff" }}>{info.name}</h3>
          <button style={S.iconBtn} onClick={onClose}><X size={16} /></button>
        </div>
        {info.w && info.w !== "—" && <div style={S.modalRow}><span style={S.modalK}>Gewichtung</span><span style={S.modalV}>{info.w}</span></div>}
        <div style={S.modalBlock}><div style={S.modalLabel}>Was es misst</div><p style={S.modalP}>{info.what}</p></div>
        <div style={S.modalBlock}><div style={S.modalLabel}>Warum es wichtig ist</div><p style={S.modalP}>{info.why}</p></div>
      </div>
    </div>
  );
}

/* ---------------- list ---------------- */
function StockRow({ s, onPick, favorites, toggleFavorite }) {
  const fav = favorites.has(s.ticker);
  return (
    <div style={S.stockCard} className="card">
      <button style={S.rowClickArea} onClick={() => onPick(s)}>
        <Logo stock={s} />
        <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
          <div style={S.cardName}>{s.name}</div>
          <div style={S.cardTicker}>{s.ticker}</div>
        </div>
      </button>
      <span style={{ ...S.status, color: statusTone(s.status), borderColor: statusTone(s.status) + "44" }}>{s.status}</span>
      <button style={S.favBtn} onClick={(e) => { e.stopPropagation(); toggleFavorite(s.ticker); }} aria-label="Favorit">
        <Flag size={15} color={fav ? BLUE : "#3a3a42"} fill={fav ? BLUE : "none"} />
      </button>
    </div>
  );
}
function ListView({ list, region, setRegion, query, setQuery, onPick, stamp, favorites, toggleFavorite }) {
  const run = new Date(stamp).toLocaleDateString("de-CH", { day: "2-digit", month: "2-digit", year: "numeric" });
  const favList = list.filter((s) => favorites.has(s.ticker));
  const restList = list.filter((s) => !favorites.has(s.ticker));
  return (
    <div style={S.body}>
      <h1 style={S.title}>Fundamental-Screen</h1>
      <p style={S.subtitle}>Qualität · Bewertung · Dislokation</p>
      <div style={S.pills}>{["US", "CH"].map((r) => (
        <button key={r} onClick={() => setRegion(r)} style={{ ...S.pill, ...(region === r ? S.pillOn : {}) }}>{r === "US" ? "S&P 100" : "SMI 50"}</button>))}
      </div>
      <div style={S.searchBox}><Search size={17} color="#5a5a60" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Suche…" style={S.searchInput} /></div>
      <div style={S.stampRow}>Letzter Durchlauf {run} · <span style={{ color: "#8b8d92" }}>Beispieldaten</span></div>

      {favList.length > 0 && (
        <>
          <div style={S.sectionLabel}>Favoriten</div>
          <div style={{ ...S.list, marginBottom: 18 }}>
            {favList.map((s) => <StockRow key={s.ticker} s={s} onPick={onPick} favorites={favorites} toggleFavorite={toggleFavorite} />)}
          </div>
          <div style={S.sectionLabel}>Alle Titel</div>
        </>
      )}
      <div style={S.list}>
        {restList.map((s) => <StockRow key={s.ticker} s={s} onPick={onPick} favorites={favorites} toggleFavorite={toggleFavorite} />)}
        {list.length === 0 && <div style={S.empty}>Keine Treffer.</div>}
      </div>
    </div>
  );
}

/* ---------------- detail ---------------- */
function MetricRow({ id, val, onInfo }) {
  return (
    <div style={S.mRow}>
      <span style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
        <span style={S.mName}>{INFO[id].name}</span>
        <button style={S.infoBtn} onClick={() => onInfo(INFO[id])}><Info size={11} /></button>
        <span style={S.weight}>{INFO[id].w}</span>
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 9 }}><Dot v={val} /><span style={S.mScore}>{val}/10</span></span>
    </div>
  );
}
function Quadrant({ stock }) {
  const x = 52 + ((stock.v - 1) / 9) * (280 - 52);
  const y = 194 - ((stock.q - 1) / 9) * (194 - 22);
  const tone = statusTone(stock.status);
  return (
    <svg viewBox="0 0 300 222" style={{ width: "100%", height: "auto" }}>
      <text x="272" y="38" fill="#5a5a60" fontSize="9" textAnchor="end" fontWeight="700">OUTLIER</text>
      <text x="60" y="38" fill="#5a5a60" fontSize="9" fontWeight="700">SOLID</text>
      <text x="60" y="205" fill="#5a5a60" fontSize="9" fontWeight="700">OVERVALUED</text>
      <text x="272" y="205" fill="#5a5a60" fontSize="9" textAnchor="end" fontWeight="700">VALUE TRAP</text>
      <line x1="166" y1="22" x2="166" y2="194" stroke="#26262c" strokeDasharray="3 3" />
      <line x1="52" y1="108" x2="280" y2="108" stroke="#26262c" strokeDasharray="3 3" />
      <text x="52" y="216" fill="#55555c" fontSize="8">← teuer · günstig →</text>
      <text x="12" y="112" fill="#55555c" fontSize="8" transform="rotate(-90 12 112)">← tief · hohe Qual. →</text>
      <circle cx={x} cy={y} r="7" fill={tone} />
      <circle cx={x} cy={y} r="12" fill="none" stroke={tone} strokeOpacity="0.4" />
    </svg>
  );
}

/* Vertiefter Wochenbericht — von der aktuellen Woche bis zum grossen Bild,
   spiegelt exakt die Struktur des Backend-Generators (report.py). Nutzt
   stock.report vom Backend, falls vorhanden, sonst clientseitig berechnet. */
function weekRangeNow() {
  const today = new Date();
  const day = today.getDay();
  const start = new Date(today); start.setDate(today.getDate() - ((day + 1) % 7));
  const end = new Date(start); end.setDate(start.getDate() + 6);
  const f = (d) => d.toLocaleDateString("de-CH", { day: "2-digit", month: "2-digit" });
  return `${f(start)} – ${end.toLocaleDateString("de-CH", { day: "2-digit", month: "2-digit", year: "numeric" })}`;
}
function reportHeadline(stock) {
  const events = [...(stock.events || [])].sort((a, b) => Math.abs(b.m) - Math.abs(a.m));
  const name = stock.name;
  if (events.length) {
    const top = events[0];
    if (top.type === "emotional" && top.m < 0 && stock.q >= 6.5) return `Warum der Markt bei ${name} gerade übertreibt`;
    if (top.type === "fundamental" && top.m > 0) return `${name} liefert – und der Kurs zieht nach`;
    if (top.type === "fundamental" && top.m < 0) return `${name}: Ein Rückgang, den man ernst nehmen sollte`;
    if (top.m < 0) return `${name} im Ausverkauf – Substanz oder Sentiment?`;
    return `${name}: Ruhige Woche, klarer Trend`;
  }
  return `${name} im Wochenüberblick`;
}

/* Seeded Auswahl aus mehreren Formulierungen: pro Aktie + Woche stabil (kein
   Flackern beim Neuladen), aber unterschiedlich zwischen Aktien und Wochen,
   damit sich der Bericht nicht wie ein Lückentext liest. */
function variantSeed(stock, salt) {
  const s = `${stock.ticker}-${weekRangeNow()}-${salt}`;
  let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}
function pick(stock, salt, variants) {
  return variants[variantSeed(stock, salt) % variants.length];
}

function buildReportPages(stock) {
  if (stock.report && Array.isArray(stock.report.pages)) return stock.report;

  const name = stock.name, events = [...(stock.events || [])].sort((a, b) => Math.abs(b.m) - Math.abs(a.m));

  // Seite 1 — diese Woche: was ist passiert, was hat es kurzfristig ausgelöst,
  // was bedeutet es langfristig — als echte Erzählung, keine Kategorien-Sprache.
  let weekP;
  if (!events.length) {
    weekP = [pick(stock, "week-quiet", [
      `Für ${name} gab es in dieser Woche keine grösseren Kursausschläge mit erkennbarem Auslöser. Der Kurs bewegte sich im Rahmen des breiten Marktes, ohne dass ein einzelnes Ereignis die Richtung vorgegeben hätte. Das ist an sich keine schlechte Nachricht – ruhige Wochen sind für langfristig orientierte Anleger oft unauffälliger, aber nicht weniger wichtig, weil sie zeigen, dass keine akute Störung im Geschäftsmodell vorliegt.`,
      `${name} zeigte diese Woche kaum Ausschläge, die über das normale Marktrauschen hinausgingen. Kein einzelnes Ereignis hat den Kurs spürbar bewegt. Für langfristige Anleger ist das eher beruhigend als langweilig: Stille Wochen bedeuten meist, dass im operativen Geschäft nichts Grundlegendes aus der Bahn geraten ist.`,
      `Diese Woche verlief bei ${name} unauffällig – die Bewegungen blieben im Rahmen dessen, was man als normales Marktrauschen bezeichnen würde. Das heisst nicht, dass nichts passiert, sondern nur, dass nichts gross genug war, um die Richtung zu bestimmen. Auch das ist eine Beobachtung wert.`,
    ])];
  } else {
    const top = events[0];
    const introVariant = pick(stock, "week-intro", [
      (t) => `Diese Woche drehte sich bei ${name} vieles um ${t}.`,
      (t) => `Im Zentrum der Woche stand bei ${name}: ${t}.`,
      (t) => `Was diese Woche bei ${name} auffiel: ${t}.`,
    ]);
    const p1 = introVariant(top.t) + (top.sum ? ` ${top.sum}` : ` Der Kurs bewegte sich um ${top.m > 0 ? "+" : ""}${top.m}\u202f%.`);

    // Zweiter Absatz: explizit kurzfristiger Auslöser vs. langfristige Bedeutung
    const shortTermCause = {
      fundamental: "konkrete, neue Geschäftszahlen oder eine veränderte Guidance",
      emotional: "Stimmung und Positionierung, ohne dass sich an den Zahlen etwas geändert hätte",
      makro: "die Entwicklung des Gesamtmarkts, etwa Zinserwartungen oder eine Sektorrotation",
    }[top.type] || "eine Mischung aus mehreren Faktoren";
    const others = events.slice(1, 3);
    const othersTxt = others.length
      ? ` Daneben spielte auch ${others.map((e) => `„${e.t}"`).join(" und ")} eine Rolle, wenn auch mit geringerem Gewicht.`
      : "";
    const longTerm = stock.q >= 6.5
      ? `Für die langfristige Substanz von ${name} ändert das nach aktuellem Stand wenig – die Kapitalrendite und die Bilanz bleiben die eigentlichen Massstäbe, nicht die Kursbewegung dieser Woche.`
      : stock.q >= 5
      ? `Ob das langfristig etwas verändert, ist noch offen – dafür lohnt sich ein Blick auf die kommenden Quartalszahlen mehr als auf den Kurs dieser Woche.`
      : `Langfristig bleibt bei ${name} ohnehin die wichtigere Frage, ob sich die operative Substanz verbessert – und da gibt es aktuell mehr offene Punkte als diese eine Kursbewegung beantworten kann.`;
    const p2 = pick(stock, "week-shortlong", [
      `Kurzfristig ausgelöst hat das vor allem ${shortTermCause}.${othersTxt} ${longTerm}`,
      `Der unmittelbare Auslöser war ${shortTermCause}.${othersTxt} ${longTerm}`,
    ]);
    weekP = [p1, p2];
  }

  // Seite 2 — Trend / Bewertung
  const trendP = [];
  if (stock.peNow && stock.peHist) {
    const rel = stock.peNow < stock.peHist ? "günstiger" : "teurer";
    const diff = Math.abs(Math.round((stock.peNow - stock.peHist) / stock.peHist * 100));
    trendP.push(pick(stock, "trend-pe", [
      `Zieht man den Blick etwas weiter, zeigt sich ${name} beim Kurs-Gewinn-Verhältnis mit ${stock.peNow} gegenüber dem eigenen historischen Schnitt von ${stock.peHist} rund ${diff}\u202f% ${rel} bewertet als sonst üblich. Das misst die Aktie an ihrer eigenen Vergangenheit, nicht an einem willkürlichen Schwellenwert, und ist damit eine der aussagekräftigsten Grössen für die Frage, ob der aktuelle Kurs eher eine Chance oder eine Warnung ist.`,
      `Mit etwas mehr Abstand betrachtet: Das Kurs-Gewinn-Verhältnis von ${name} liegt aktuell bei ${stock.peNow}, gegenüber einem eigenen historischen Mittel von ${stock.peHist} – also rund ${diff}\u202f% ${rel} als üblich. Dieser Vergleich mit der eigenen Historie sagt mehr aus als ein absoluter Schwellenwert, weil er berücksichtigt, wie der Markt diese Aktie normalerweise bewertet.`,
    ]));
  } else {
    trendP.push(`Zur Einordnung der Bewertung von ${name} liegen aktuell keine ausreichend verlässlichen historischen Vergleichswerte vor.`);
  }
  if (stock.drawdown != null) {
    const strong = stock.drawdown < -20 && stock.q >= 6.5;
    trendP.push(`Vom letzten Allzeithoch ist der Kurs ${Math.abs(stock.drawdown).toFixed(0)}\u202f% entfernt. Für sich allein sagt das wenig aus – ein Rückgang kann eine Kaufgelegenheit oder eine berechtigte Neubewertung sein. ${strong ? "Ein deutlicher Rückgang bei intakten Fundamentaldaten ist ein Muster, das in der Vergangenheit häufiger zu überdurchschnittlichen Erholungen geführt hat." : "Solange kein grösserer Rückgang vorliegt, bleibt dieser Punkt vor allem eine Beobachtungsgrösse."}`);
  }
  trendP.push(stock.v >= 6.5
    ? pick(stock, "trend-cheap", [
        "Insgesamt spricht die aktuelle Bewertung eher für die Aktie: Sie handelt mit einem gewissen Sicherheitsabschlag gegenüber ihrem geschätzten fairen Wert, was Anlegern etwas mehr Puffer nach unten verschafft.",
        "Unter dem Strich wirkt die Bewertung derzeit eher einladend: Der Kurs liegt mit spürbarem Abschlag zum geschätzten fairen Wert, was das Abwärtsrisiko etwas begrenzt.",
      ])
    : stock.v <= 4
    ? pick(stock, "trend-expensive", [
        "Insgesamt ist die aktuelle Bewertung eher ein Gegenargument: Der Markt preist bereits recht viel Optimismus ein, was den Spielraum für weitere Kursgewinne einschränkt und das Risiko bei Enttäuschungen erhöht.",
        "Unter dem Strich mahnt die Bewertung eher zur Vorsicht: Im aktuellen Kurs steckt schon einiges an Optimismus, was bei einer Enttäuschung mehr Fallhöhe bedeutet.",
      ])
    : "Insgesamt bewegt sich die Bewertung in einem neutralen Bereich – weder ein klarer Rabatt noch eine deutliche Überhitzung.");

  // Seite 3 — das grosse Bild
  const bigP = [
    pick(stock, "big-intro", [
      `Zoomt man ganz heraus, bleibt die eigentlich entscheidende Frage bei ${name}: trägt das Geschäftsmodell über die kommenden Jahre einen echten, verteidigbaren Vorteil gegenüber der Konkurrenz – sei es durch Marke, Skaleneffekte, Netzwerkeffekte oder technologischen Vorsprung? Kurzfristige Kursbewegungen, wie die dieser Woche, sagen darüber praktisch nichts aus. Sie sind Rauschen um einen langsamer verlaufenden, aber deutlich wichtigeren Trend.`,
      `Mit etwas Distanz betrachtet, zählt bei ${name} eigentlich nur eine Frage: Hat das Unternehmen über die kommenden Jahre einen Vorteil, den Wettbewerber nicht einfach kopieren können – durch Marke, Grösse, Netzwerkeffekte oder technologischen Vorsprung? Was diese Woche am Kurs passiert ist, beantwortet diese Frage nicht. Es ist Rauschen über einem viel langsameren, aber wichtigeren Trend.`,
    ]),
    stock.q >= 6.5
      ? `Die aktuellen Kennzahlen deuten darauf hin, dass dieser Vorteil bei ${name} nach wie vor intakt ist: eine überdurchschnittliche Kapitalrendite und eine stabile Bilanz sind genau die Signale, die auf einen funktionierenden Burggraben hindeuten, statt auf ein Geschäft, das nur von günstigen Marktbedingungen profitiert.`
      : `Die aktuellen Kennzahlen liefern hier kein eindeutiges Bild – weder ein klarer Beleg für einen starken Wettbewerbsvorteil noch ein akutes Warnsignal. Das lohnt sich, in den kommenden Quartalen weiter zu beobachten, insbesondere ob sich Marge und Kapitalrendite eher verbessern oder verschlechtern.`,
    `Strukturell prägend für die ${stock.sector || "Branche"}, in der ${name} tätig ist, sind aktuell technologische Verschiebungen – von Automatisierung über Dateninfrastruktur bis zu neuen KI-gestützten Anwendungen, die bestehende Geschäftsmodelle sowohl bedrohen als auch neue Wege eröffnen können. Wer hier auf der richtigen Seite steht, kann seinen Vorsprung über Jahre ausbauen; wer den Anschluss verliert, sieht selbst solide Fundamentaldaten schrittweise erodieren. Das ist der eigentliche Massstab, an dem sich diese Position über die kommenden Jahre messen lassen muss – nicht die Kursbewegung dieser einen Woche.`,
  ];

  return {
    headline: reportHeadline(stock),
    weekRange: weekRangeNow(),
    pages: [
      { title: "Diese Woche", paragraphs: weekP },
      { title: "Dieser Trend", paragraphs: trendP },
      { title: "Das grosse Bild", paragraphs: bigP },
    ],
  };
}
function downloadReportText(stock, data) {
  const lines = [`FINVEST — WOCHENBERICHT`, `${stock.name} · ${data.weekRange}`, "", data.headline, "", ""];
  data.pages.forEach((p) => { lines.push(p.title.toUpperCase()); lines.push(""); p.paragraphs.forEach((t) => { lines.push(t); lines.push(""); }); });
  lines.push("Automatisch erzeugte Zusammenfassung · keine Anlageempfehlung");
  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `Finvest-Wochenbericht-${stock.ticker}.txt`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function CoverPage({ stock, weekRange }) {
  return (
    <div style={S.reportCoverWrap}>
      <div style={S.articleHero}><Logo stock={stock} size={68} /></div>
      <div style={S.reportCover}>
        <div style={S.coverBlueLine} />
        <h1 style={S.coverTitle}>Finvest Marketreport</h1>
        <div style={S.coverRow}>
          <span style={S.coverRowItem}>{stock.name}</span>
          <span style={S.coverRowItemSmall}>{weekRange}</span>
        </div>
        <div style={S.coverSub}>Fundamentalanalyse</div>
      </div>
    </div>
  );
}

function ReportViewer({ stock, onClose, onArchive, date }) {
  const data = useMemo(() => buildReportPages(stock), [stock]);
  const [page, setPage] = useState(0);              // 0 = Deckblatt, 1..N = Inhalt
  const total = data.pages.length + 1;
  useEffect(() => { onArchive && onArchive(stock, data); }, []); // eslint-disable-line
  const printRef = useMemo(() => "finvest-report-print", []);

  const go = (d) => setPage((p) => Math.max(0, Math.min(total - 1, p + d)));
  const isCover = page === 0;

  return (
    <div style={S.reportOverlay} onClick={onClose}>
      <div style={S.reportOuter} onClick={(e) => e.stopPropagation()}>
        {/* Persistenter Chrome-Header nur auf den Inhaltsseiten — das Cover
            trägt seine eigene, vollständige Markenoptik ohne Wiederholung. */}
        {isCover ? (
          <div style={S.reportHeadMin} className="no-print">
            <button style={S.iconBtnLight} onClick={onClose}><X size={17} /></button>
          </div>
        ) : (
          <div style={S.reportHead} className="no-print">
            <span style={S.reportWordmark}>Finvest</span>
            <button style={S.iconBtnLight} onClick={onClose}><X size={17} /></button>
          </div>
        )}

        <div style={S.reportShell} id={printRef}>
          <div className="no-print">
            {isCover ? (
              <CoverPage stock={stock} weekRange={data.weekRange} />
            ) : (
              <div style={S.reportPage}>
                <div style={S.pageHeadBar}>{stock.ticker} · Seite {page} / {data.pages.length}</div>
                <h1 style={S.reportTitle}>{data.pages[page - 1].title}</h1>
                {data.pages[page - 1].paragraphs.map((p, i) => <p key={i} style={S.reportPara}>{p}</p>)}
              </div>
            )}
          </div>

          {/* Vollständiges Dokument, nur für den Druck/PDF-Export sichtbar (alle Seiten am Stück, echtes A4) */}
          <div className="print-only" style={S.printDoc}>
            <CoverPage stock={stock} weekRange={data.weekRange} />
            {data.pages.map((p, pi) => (
              <div key={pi} style={{ ...S.reportPage, pageBreakBefore: "always" }}>
                <div style={S.pageHeadBar}>{stock.ticker} · Seite {pi + 1} / {data.pages.length}</div>
                <h1 style={S.reportTitle}>{p.title}</h1>
                {p.paragraphs.map((t, i) => <p key={i} style={S.reportPara}>{t}</p>)}
              </div>
            ))}
          </div>
        </div>

        <div style={S.reportNav} className="no-print">
          <button style={S.reportNavBtn} onClick={() => go(-1)} disabled={page === 0}><ChevronLeft size={16} /></button>
          <div style={S.reportDots}>
            {Array.from({ length: total }).map((_, i) => (
              <span key={i} style={{ ...S.reportDot, ...(i === page ? S.reportDotOn : {}) }} onClick={() => setPage(i)} />
            ))}
          </div>
          <button style={S.reportNavBtn} onClick={() => go(1)} disabled={page === total - 1}><ChevronRight size={16} /></button>
        </div>

        <div style={S.reportActions} className="no-print">
          <button style={S.reportActionBtn} onClick={() => window.print()}><Printer size={14} /> Als PDF speichern</button>
          <button style={S.reportActionBtn} onClick={() => downloadReportText(stock, data)}><Download size={14} /> Herunterladen</button>
        </div>
      </div>
    </div>
  );
}

function DetailView({ stock, series, tf, setTf, onBack, onInfo, busy, refresh, onArchive }) {
  const [newsOpen, setNewsOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [newsTab, setNewsTab] = useState("neu");
  const [newsSel, setNewsSel] = useState(null);
  useEffect(() => { setNewsOpen(false); setReportOpen(false); }, [stock.ticker]);
  const reportPreview = useMemo(() => buildReportPages(stock), [stock]);

  if (newsOpen) return (
    <NewsScreen stock={stock} tab={newsTab} setTab={setNewsTab} onBack={() => setNewsOpen(false)} sel={newsSel} setSel={setNewsSel} onInfo={onInfo} />
  );

  const proj = projection(stock);
  const currentPrice = series.length ? series[series.length - 1].p : null;
  const athPrice = currentPrice != null ? currentPrice / (1 + stock.drawdown / 100) : null;
  const cc = BLUE;

  return (
    <div style={S.body}>
      <div style={S.detailTop}>
        <button style={S.back} onClick={onBack}><ChevronLeft size={17} /> Übersicht</button>
        <button style={S.reBtn} onClick={refresh} disabled={busy}><RefreshCw size={13} className={busy ? "spin" : ""} /> {busy ? "Analysiert…" : "Neu analysieren"}</button>
      </div>

      <div style={S.idCard}>
        <Logo stock={stock} size={56} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={S.idName}>{stock.name}</div>
          <div style={S.idMeta}>{stock.ticker} · {stock.region === "US" ? "NYSE / Nasdaq" : "SIX"}{stock.isFin ? " · Finanz" : ""}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={S.bigScore}>{stock.overall.toFixed(1)}<span style={S.of10}>/10</span></div>
          <span style={{ ...S.status, color: statusTone(stock.status), borderColor: statusTone(stock.status) + "44" }}>{stock.status}</span>
        </div>
      </div>

      
      <div style={S.newsBlock}>
        <div style={S.newsHeading}><FileText size={15} color="#fff" /> Marktbericht</div>
        <div style={S.newsTeaserWrap}>
          <div style={S.newsTeaserBlur}>
            <div style={S.teaserRow}><span style={S.teaserTitle}>{reportPreview.headline}</span></div>
            <div style={S.teaserRow}>
              <span style={S.teaserTitle}>{reportPreview.pages.map((p) => p.title).join(" · ")}</span>
              <span style={S.teaserMeta}>{reportPreview.weekRange}</span>
            </div>
          </div>
          <button style={S.teaserBtn} onClick={() => setReportOpen(true)}>Bericht</button>
        </div>
      </div>

      {/* gesamtbild */}
      <div style={S.card2}>
        <div style={S.cardHead}><span style={S.headL}><LayoutGrid size={15} color="#fff" /> Gesamtbild</span></div>
        <div style={S.blockRow}>
          {[["Qualität", stock.q, "quality"], ["Bewertung", stock.v, "valuation"], ["Dislokation", stock.disl, "dislocation"]].map(([l, val, id]) => (
            <div key={id} style={S.blockCell}>
              <div style={S.blockTop}><span style={S.blockLabel}>{l}</span><button style={S.infoBtn} onClick={() => onInfo(INFO[id])}><Info size={10} /></button></div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 7 }}><Dot v={val} /><span style={S.blockVal}>{val.toFixed(1)}</span></div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 6 }}><Quadrant stock={stock} /></div>
      </div>

      {/* chart */}
      <div style={S.card2}>
        <div style={S.cardHead}><span style={S.headL}><BarChart3 size={15} color="#fff" /> Kursverlauf</span>
          <div style={S.tfRow}>{["1M", "6M", "1J", "5J"].map((t) => (<button key={t} onClick={() => setTf(t)} style={{ ...S.tf, ...(tf === t ? S.tfOn : {}) }}>{t}</button>))}</div>
        </div>
        <div style={{ height: 200, marginTop: 8 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} margin={{ top: 6, right: 4, left: -20, bottom: 0 }}>
              <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={cc} stopOpacity={0.28} /><stop offset="100%" stopColor={cc} stopOpacity={0} /></linearGradient></defs>
              <XAxis dataKey="t" tick={{ fill: "#55555c", fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={28} />
              <YAxis tick={{ fill: "#55555c", fontSize: 10 }} axisLine={false} tickLine={false} width={46} domain={["auto", "auto"]} />
              <Tooltip contentStyle={S.tip} labelStyle={{ color: "#8b8d92" }} formatter={(x) => [x + " $", "Kurs"]} />
              <Area type="monotone" dataKey="p" stroke={cc} strokeWidth={2} fill="url(#g)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* günstigkeit */}
      <div style={S.card2}>
        <div style={S.cardHead}><span style={S.headL}><Scale size={15} color="#fff" /> Günstigkeitsbewertung</span></div>
        <div style={S.valGrid}>
          <div style={{ ...S.valCell, gridColumn: "1 / -1" }}>
            <div style={S.valTop}><span style={S.valK}>KGV — Aktuell vs. Ø-Historie</span><button style={S.infoBtn} onClick={() => onInfo(INFO.pe)}><Info size={10} /></button></div>
            <div style={S.peRow}>
              <div style={S.peCol}>
                <div style={{ ...S.peNum, color: peColor(stock.peNow, stock.peHist) }}>{stock.peNow}</div>
                <div style={S.peLabel}>Aktuell</div>
              </div>
              <div style={S.peDivider} />
              <div style={S.peCol}>
                <div style={S.peNum}>{stock.peHist}</div>
                <div style={S.peLabel}>Ø-Historie</div>
              </div>
            </div>
          </div>
          <div style={{ ...S.valCell, gridColumn: "1 / -1" }}>
            <div style={S.valTop}><span style={S.valK}>EV/EBITDA — Aktuell vs. Ø-Historie</span><button style={S.infoBtn} onClick={() => onInfo(INFO.ev)}><Info size={10} /></button></div>
            <div style={S.peRow}>
              <div style={S.peCol}>
                <div style={{ ...S.peNum, color: peColor(stock.evNow, stock.evHist) }}>{stock.evNow}</div>
                <div style={S.peLabel}>Aktuell</div>
              </div>
              <div style={S.peDivider} />
              <div style={S.peCol}>
                <div style={S.peNum}>{stock.evHist}</div>
                <div style={S.peLabel}>Ø-Historie</div>
              </div>
            </div>
          </div>
          <div style={{ ...S.valCell, gridColumn: "1 / -1" }}>
            <div style={S.valTop}><span style={S.valK}>Abstand vom Allzeithoch</span><button style={S.infoBtn} onClick={() => onInfo(INFO.drawdown)}><Info size={10} /></button></div>
            <div style={S.athRow}>
              <div style={S.peCol}>
                <div style={S.peNum}>{athPrice != null ? athPrice.toFixed(0) : "—"}</div>
                <div style={S.peLabel}>ATH-Preis</div>
              </div>
              <div style={S.peDivider} />
              <div style={S.peCol}>
                <div style={S.peNum}>{currentPrice != null ? currentPrice.toFixed(0) : "—"}</div>
                <div style={S.peLabel}>Aktueller Preis</div>
              </div>
              <div style={S.peDivider} />
              <div style={S.peCol}>
                <div style={S.peNum}>{stock.drawdown.toFixed(0)}%</div>
                <div style={S.peLabel}>Abstand</div>
              </div>
            </div>
          </div>
          <div style={{ ...S.valCell, gridColumn: "1 / -1" }}>
            <div style={S.valTop}><span style={S.valK}>Reverse-DCF</span><button style={S.infoBtn} onClick={() => onInfo(INFO.revdcf)}><Info size={10} /></button></div>
            <div style={S.valV}>{stock.impliedGrowth}%</div><div style={S.valSub}>eingepreist</div>
            <div style={{ ...S.valTag, color: stock.realistic ? GREEN : GRAY }}>{stock.realistic ? "realistisch" : "ambitioniert"}</div>
          </div>
        </div>
        <div style={S.liveNote}>KGV-Ø kuratiert · aktuelles KGV &amp; ATH illustrativ bis Kurs-API</div>
      </div>

      {/* news — verschwommener Teaser + Button */}
      <div style={S.newsBlock}>
        <div style={S.cardHead}><span style={S.newsHeading}><Newspaper size={15} color="#fff" /> News</span>
          <button style={S.infoBtn} onClick={() => onInfo(INFO.news)}><Info size={11} /></button></div>
        <div style={S.newsTeaserWrap}>
          <div style={S.newsTeaserBlur}>
            {stock.events.slice(0, 3).map((e, i) => (
              <div key={i} style={S.teaserRow}>
                <span style={S.teaserTitle}>{e.t}</span>
                <span style={S.teaserMeta}>{e.d} · {e.m > 0 ? "+" : ""}{e.m}%</span>
              </div>
            ))}
          </div>
          <button style={S.teaserBtn} onClick={() => setNewsOpen(true)}>Anschauen</button>
        </div>
      </div>

      {/* quality detail — dots */}
      <div style={S.card2}>
        <div style={S.cardHead}><span style={S.headL}><ShieldCheck size={15} color="#fff" /> Qualität im Detail</span>
          {!stock.gate && <span style={S.gateTag}><AlertTriangle size={11} /> Gate aktiv</span>}</div>
        <div style={{ marginTop: 8 }}>
          {["roic", "roicTrend", "eq", "marginStab", "balance", "dilution"].map((id) => <MetricRow key={id} id={id} val={stock.qIn[id]} onInfo={onInfo} />)}
        </div>
      </div>

      {/* projection */}
      <div style={S.card2}>
        <div style={S.cardHead}><span style={S.headL}><LineChart size={15} color="#fff" /> Projektion 3 J. &amp; Konfidenz</span></div>
        <div style={S.projGrid}>
          <div style={S.projCell}><div style={S.projLabel}>Basis p.a.</div><div style={S.projVal}>{proj.annual >= 0 ? "+" : ""}{proj.annual.toFixed(1)}%</div></div>
          <div style={S.projCell}><div style={S.projLabel}>Kumuliert</div><div style={S.projVal}>{proj.base3 >= 0 ? "+" : ""}{proj.base3.toFixed(0)}%</div></div>
          <div style={S.projCell}><div style={S.projLabel}>Bandbreite</div><div style={{ ...S.projVal, fontSize: 14 }}>{proj.low3.toFixed(0)}…{proj.high3.toFixed(0)}%</div></div>
          <div style={S.projCell}><div style={S.projLabel}>Konfidenz</div><div style={{ display: "flex", alignItems: "center", gap: 7 }}><Dot v={stock.confidence / 10} /><span style={S.projVal}>{stock.confidence}%</span></div></div>
        </div>
        <div style={S.note}>Konfidenz = wie stark der Score auf harten Zahlen statt Schätzungen ruht. Kein Kursziel, keine Anlageempfehlung.</div>
      </div>

      <div style={S.foot}>Gesamt-Score = 45 % Qualität + 40 % Bewertung + 15 % Dislokation, gedeckelt durch Bilanz-/Ertragsqualitäts-Gate.</div>

      {reportOpen && <ReportViewer stock={stock} onClose={() => setReportOpen(false)} onArchive={onArchive} />}
    </div>
  );
}

/* ---------------- news screen ---------------- */
function NewsScreen({ stock, tab, setTab, onBack, sel, setSel, onInfo }) {
  const events = tab === "treiber"
    ? [...stock.events].sort((a, b) => Math.abs(b.m) - Math.abs(a.m))
    : stock.events;
  return (
    <div style={S.body}>
      <div style={S.detailTop}>
        <button style={S.back} onClick={onBack}><ChevronLeft size={17} /> Analyse</button>
        <button style={S.infoBtn} onClick={() => onInfo(INFO.news)}><Info size={12} /></button>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
        <Logo stock={stock} size={34} /><h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>News · {stock.ticker}</h2>
      </div>
      <p style={S.subtitle}>{tab === "treiber" ? "Grösste Kursbewegungen – nach Aussagekraft sortiert." : "Aktuellste Ereignisse zuerst."}</p>

      <div style={S.tabs}>
        {[["neu", "Neuigkeiten"], ["treiber", "Preistreiber"]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} style={{ ...S.tab2, ...(tab === k ? S.tab2On : {}) }}>{l}</button>))}
      </div>

      <div style={S.list}>
        {events.map((e, i) => (
          <button key={i} className="card" style={S.card} onClick={() => setSel(e)}>
            <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
              <div style={S.cardName}>{e.t}</div>
              <div style={S.newsRowDate}>{e.d}</div>
            </div>
            <span style={{ fontFamily: "var(--mono)", fontWeight: 800, fontSize: 14, color: e.m < 0 ? RED : GREEN, display: "flex", alignItems: "center", gap: 5 }}>
              {e.m < 0 ? <TrendingDown size={14} /> : <TrendingUp size={14} />}{e.m > 0 ? "+" : ""}{e.m}%
            </span>
          </button>
        ))}
      </div>

      {sel && <NewsArticle stock={stock} event={sel} onClose={() => setSel(null)} />}
    </div>
  );
}

function NewsArticle({ stock, event, onClose }) {
  const typeMeta = { fundamental: { l: "Fundamental" }, emotional: { l: "Emotional" }, makro: { l: "Makro" } }[event.type] || { l: "Makro" };
  const typeExplain = { fundamental: "gestützt durch echte Geschäftszahlen", emotional: "Sentiment-getrieben, ohne neue Zahlen", makro: "durch den Gesamtmarkt ausgelöst" }[event.type] || "";
  return (
    <div style={S.reportOverlay} onClick={onClose}>
      <div style={S.reportOuter} onClick={(e) => e.stopPropagation()}>
        <div style={S.reportHeadMin} className="no-print">
          <button style={S.iconBtnLight} onClick={onClose}><X size={17} /></button>
        </div>
        <div style={{ ...S.reportShell, overflowY: "auto" }}>
          <div style={S.articleHero}>
            <Logo stock={stock} size={72} />
          </div>
          <div style={S.reportPage}>
            <div style={S.pageHeadBar}>{stock.ticker} · {typeMeta.l} · {event.d}</div>
            <h1 style={S.reportTitle}>{event.t}</h1>
            <div style={S.articleMove}>
              {event.m < 0 ? <TrendingDown size={16} color={RED} /> : <TrendingUp size={16} color={GREEN} />}
              <span style={{ color: event.m < 0 ? RED : GREEN, fontFamily: "var(--mono)", fontWeight: 800 }}>{event.m > 0 ? "+" : ""}{event.m}%</span>
              <span style={{ color: "#7a7a82" }}>am {event.d}</span>
            </div>

            <div style={S.articleKicker}>Das Wichtigste in Kürze</div>
            <ul style={S.articleBullets}>
              {(event.bullets || [
                `Kursbewegung: ${event.m > 0 ? "+" : ""}${event.m}% am ${event.d}`,
                `Einordnung: ${typeMeta.l} — ${typeExplain}`,
                `Aussagekraft: ${event.s}`,
              ]).map((b, i) => <li key={i} className="article-bullet" style={S.articleBulletItem}>{b}</li>)}
            </ul>

            <div style={S.articleKicker}>Bericht</div>
            <p style={S.reportPara}>{event.sum || "Für dieses Ereignis liegt noch keine ausführliche Einordnung vor."}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------------- styles ---------------- */
const CSS = `
:root{--mono:ui-monospace,'SF Mono',Menlo,monospace;--sans:-apple-system,'SF Pro Display','Segoe UI',Roboto,sans-serif;}
*{box-sizing:border-box;}
.spin{animation:sp 1s linear infinite;}@keyframes sp{to{transform:rotate(360deg);}}
.card{transition:transform .12s,border-color .12s,background .12s;}
.article-bullet::before{content:"•";position:absolute;left:0;color:#4c9eea;font-weight:800;}
.card:hover{border-color:#2a2a32 !important;background:#111116 !important;}
.card:active{transform:scale(.99);}
input::placeholder{color:#5a5a60;}
::-webkit-scrollbar{width:8px;}::-webkit-scrollbar-thumb{background:#1c1c22;border-radius:6px;}
@media (prefers-reduced-motion:reduce){.spin{animation:none;}}
@media print{
  @page{ size: A4; margin: 0; }
  body *{visibility:hidden;}
  #finvest-report-print, #finvest-report-print *{visibility:visible;}
  #finvest-report-print{position:absolute;left:0;top:0;width:210mm;}
  .no-print{display:none !important;}
  .print-only{display:block !important;}
}
`;
const S = {
  root: { minHeight: "100vh", background: "#000", color: "#fff", fontFamily: "var(--sans)", paddingBottom: 90 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 18px 15px" },
  headerIconBtn: { width: 34, height: 34, borderRadius: 10, background: "transparent", border: "1px solid #1c1c22", color: "#b6b8bd", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" },
  wordmark: { fontSize: 22, fontWeight: 800, letterSpacing: 0.3 },
  blueLine: { height: 2, background: "linear-gradient(90deg,transparent,#23a0f2 30%,#23a0f2 70%,transparent)", opacity: 0.85 },
  body: { maxWidth: 720, margin: "0 auto", padding: "22px 18px 0" },
  title: { fontSize: 29, fontWeight: 800, margin: 0, letterSpacing: -0.5 },
  subtitle: { fontSize: 14, color: "#8b8d92", margin: "6px 0 18px" },
  pills: { display: "flex", gap: 10, marginBottom: 14 },
  pill: { background: "#0d0d10", border: "1px solid #1e1e24", color: "#b6b8bd", padding: "10px 20px", borderRadius: 12, cursor: "pointer", fontSize: 14, fontWeight: 700 },
  pillOn: { background: "#08243b", border: "1px solid #23a0f2", color: "#eaf5ff" },
  searchBox: { display: "flex", alignItems: "center", gap: 10, background: "#0d0d10", border: "1px solid #1e1e24", borderRadius: 14, padding: "13px 16px" },
  searchInput: { flex: 1, background: "transparent", border: "none", outline: "none", color: "#fff", fontSize: 15 },
  stampRow: { fontSize: 11.5, color: "#5a5a60", margin: "12px 2px 14px" },
  list: { display: "flex", flexDirection: "column", gap: 11 },
  sectionLabel: { fontSize: 11.5, fontWeight: 700, letterSpacing: 0.6, textTransform: "uppercase", color: "#5a5a60", margin: "4px 2px 10px" },
  card: { display: "flex", alignItems: "center", gap: 14, width: "100%", background: "#0c0c0f", border: "1px solid #18181e", borderRadius: 16, padding: "14px 16px", cursor: "pointer", color: "inherit" },
  stockCard: { display: "flex", alignItems: "center", gap: 8, width: "100%", background: "#0c0c0f", border: "1px solid #18181e", borderRadius: 16, padding: "8px 10px 8px 16px", color: "inherit" },
  rowClickArea: { display: "flex", alignItems: "center", gap: 14, flex: 1, minWidth: 0, background: "transparent", border: "none", cursor: "pointer", padding: "6px 0", color: "inherit", textAlign: "left" },
  favBtn: { display: "flex", alignItems: "center", justifyContent: "center", width: 34, height: 34, borderRadius: 9, background: "transparent", border: "none", cursor: "pointer", flexShrink: 0 },
  cardName: { fontSize: 15.5, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  cardTicker: { fontSize: 12, color: "#6a6a72", marginTop: 2, fontFamily: "var(--mono)", letterSpacing: 0.3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  newsRowDate: { fontSize: 12, color: "#fff", marginTop: 3, fontFamily: "var(--mono)" },
  status: { fontSize: 12, fontWeight: 800, borderRadius: 9, padding: "6px 12px", border: "1px solid", whiteSpace: "nowrap", letterSpacing: 0.2, background: "#0a0a0d" },
  empty: { textAlign: "center", color: "#6a6a72", padding: "44px 0", fontSize: 14 },
  fab: { position: "fixed", right: 20, bottom: 24, width: 58, height: 58, borderRadius: 18, border: "none", cursor: "pointer", background: "linear-gradient(145deg,#3fb8ff,#1583e0)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 28px rgba(35,160,242,.5)" },

  detailTop: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  back: { display: "flex", alignItems: "center", gap: 4, background: "transparent", border: "none", color: "#23a0f2", cursor: "pointer", fontSize: 14, fontWeight: 700 },
  reBtn: { display: "flex", alignItems: "center", gap: 6, background: "#0d0d10", color: "#b6b8bd", border: "1px solid #1e1e24", padding: "8px 13px", borderRadius: 10, cursor: "pointer", fontSize: 12.5, fontWeight: 600 },
  idCard: { display: "flex", alignItems: "center", gap: 16, background: "#0c0c0f", border: "1px solid #18181e", borderRadius: 18, padding: "18px", marginBottom: 12 },
  idName: { fontSize: 20, fontWeight: 800 },
  idMeta: { fontSize: 12, color: "#6a6a72", marginTop: 3, fontFamily: "var(--mono)" },
  bigScore: { fontFamily: "var(--mono)", fontWeight: 800, fontSize: 30, lineHeight: 1, marginBottom: 8, color: "#fff" },
  of10: { fontSize: 14, color: "#48484f", fontWeight: 600 },
  signalBar: { display: "flex", alignItems: "center", gap: 9, background: "#0c0c0f", border: "1px solid #1e1e24", borderRadius: 14, padding: "12px 15px", fontSize: 13, color: "#dcdce0", fontWeight: 600, marginBottom: 12 },
  actionBtn: { display: "flex", alignItems: "center", justifyContent: "center", gap: 7, width: "100%", background: "#fff", color: "#0a0a0d", border: "none", borderRadius: 12, padding: "13px", fontSize: 14, fontWeight: 800, cursor: "pointer", marginBottom: 14, boxShadow: "0 6px 18px rgba(0,0,0,.35)" },

  card2: { background: "#0c0c0f", border: "1px solid #18181e", borderRadius: 18, padding: "16px 18px", marginBottom: 14 },
  cardHead: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  headL: { display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 700, color: "#e6e6ea" },
  headLmute: { display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 700, color: "#8b8d92" },

  blockRow: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10, marginTop: 12 },
  blockCell: { background: "#08080b", border: "1px solid #16161c", borderRadius: 12, padding: "12px 12px 14px" },
  blockTop: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  blockLabel: { fontSize: 12, color: "#9a9aa2", fontWeight: 600 },
  blockVal: { fontFamily: "var(--mono)", fontWeight: 800, fontSize: 23, color: "#fff" },

  tfRow: { display: "flex", gap: 3, background: "#08080b", border: "1px solid #1c1c22", borderRadius: 10, padding: 3 },
  tf: { border: "none", background: "transparent", color: "#8b8d92", padding: "5px 11px", borderRadius: 7, cursor: "pointer", fontSize: 12, fontWeight: 700, fontFamily: "var(--mono)" },
  tfOn: { background: "#08243b", color: "#7fc9ff" },
  tip: { background: "#0d0d10", border: "1px solid #1e1e24", borderRadius: 10, fontSize: 12 },

  valGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 10, marginTop: 12 },
  valCell: { background: "#08080b", border: "1px solid #16161c", borderRadius: 12, padding: "12px 13px" },
  valTop: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  valK: { fontSize: 11.5, color: "#8b8d92" },
  valV: { fontFamily: "var(--mono)", fontWeight: 800, fontSize: 21, marginTop: 6, color: "#fff" },
  valSub: { fontSize: 10.5, color: "#5a5a60", marginTop: 2 },
  valTag: { display: "inline-block", marginTop: 8, fontSize: 10.5, fontWeight: 700 },
  peRow: { display: "flex", alignItems: "center", justifyContent: "space-around", marginTop: 10 },
  athRow: { display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 10 },
  peCol: { display: "flex", flexDirection: "column", alignItems: "center", gap: 4 },
  peDivider: { width: 1, height: 34, background: "#1e1e24" },
  peNum: { fontFamily: "var(--mono)", fontWeight: 800, fontSize: 24 },
  peLabel: { fontSize: 10.5, color: "#6a6a72", textTransform: "uppercase", letterSpacing: 0.4 },
  liveNote: { fontSize: 10.5, color: "#4a4a50", marginTop: 12, fontStyle: "italic" },

  newsBlock: { background: "#070709", border: "1px solid #141418", borderRadius: 18, padding: "16px 18px", marginBottom: 14 },
  newsHeading: { display: "flex", alignItems: "center", gap: 8, fontSize: 15, fontWeight: 800, color: "#fff" },
  newsTeaserWrap: { position: "relative", marginTop: 12 },
  newsTeaserBlur: { filter: "blur(3.5px)", opacity: 0.55, pointerEvents: "none", userSelect: "none" },
  teaserRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #17171d" },
  teaserTitle: { fontSize: 13, fontWeight: 600, color: "#fff", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "70%" },
  teaserMeta: { fontSize: 11.5, color: "#fff", fontFamily: "var(--mono)" },
  teaserBtn: { position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", background: "#fff", color: "#0a0a0d", border: "none", borderRadius: 10, padding: "11px 26px", fontSize: 13, fontWeight: 800, cursor: "pointer", boxShadow: "0 8px 24px rgba(0,0,0,.5)", whiteSpace: "nowrap" },
  verdictMute: { display: "flex", alignItems: "flex-start", gap: 9, fontSize: 13, lineHeight: 1.5, margin: "10px 0 14px", fontWeight: 600, color: "#dcdce0" },
  verdictDot: { width: 8, height: 8, borderRadius: 4, display: "inline-block", flexShrink: 0, marginTop: 5 },

  tabs: { display: "flex", gap: 8, marginBottom: 16 },
  tab2: { flex: 1, background: "#0d0d10", border: "1px solid #1e1e24", color: "#b6b8bd", padding: "11px", borderRadius: 12, cursor: "pointer", fontSize: 13.5, fontWeight: 700 },
  tab2On: { background: "#08243b", border: "1px solid #23a0f2", color: "#eaf5ff" },
  typeTag: { fontSize: 11, fontWeight: 700, borderRadius: 6, padding: "3px 9px" },

  gateTag: { display: "flex", alignItems: "center", gap: 4, fontSize: 10.5, fontWeight: 700, color: RED, background: RED + "1c", borderRadius: 6, padding: "3px 8px" },
  mRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #131317" },
  mName: { fontSize: 13.5, fontWeight: 600, color: "#e6e6ea", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  weight: { fontSize: 10.5, fontFamily: "var(--mono)", color: "#5fb0ee", background: "#0a1c2c", border: "1px solid #14344e", borderRadius: 6, padding: "1px 6px" },
  mScore: { fontFamily: "var(--mono)", fontWeight: 800, fontSize: 13, color: "#fff", minWidth: 40, textAlign: "right" },

  projGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(110px,1fr))", gap: 10, marginTop: 12 },
  projCell: { background: "#08080b", border: "1px solid #16161c", borderRadius: 12, padding: "12px 13px" },
  projLabel: { fontSize: 11, color: "#6a6a72", marginBottom: 6 },
  projVal: { fontFamily: "var(--mono)", fontWeight: 800, fontSize: 18, color: "#fff" },
  note: { fontSize: 11, color: "#5a5a60", marginTop: 12, fontStyle: "italic" },
  foot: { fontSize: 11.5, color: "#55555c", lineHeight: 1.65, padding: "2px 2px 10px" },

  overlay: { position: "fixed", inset: 0, background: "#000", display: "flex", alignItems: "center", justifyContent: "center", padding: 18, zIndex: 60 },
  modal: { width: "100%", maxWidth: 430, background: "#0d0d11", border: "1px solid #23232b", borderRadius: 18, padding: "20px", boxShadow: "0 24px 70px rgba(0,0,0,.7)" },
  iconBtn: { background: "transparent", border: "none", color: "#6a6a72", cursor: "pointer" },
  modalRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 15, paddingBottom: 13, borderBottom: "1px solid #1a1a20" },
  modalK: { fontSize: 12.5, color: "#8b8d92" },
  modalV: { fontFamily: "var(--mono)", fontWeight: 800, color: "#7fc9ff" },
  modalBlock: { marginTop: 14 },
  modalLabel: { fontSize: 11, textTransform: "uppercase", letterSpacing: 0.6, color: "#55555c", marginBottom: 5 },
  modalP: { margin: 0, fontSize: 13, lineHeight: 1.6, color: "#dcdce0" },

  /* ---- Wochenbericht: echtes A4-Dokument, schwarz auf weiss ---- */
  reportOverlay: { position: "fixed", inset: 0, background: "#000", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px 12px", zIndex: 70, overflowY: "auto" },
  reportOuter: { width: "100%", maxWidth: 640, display: "flex", flexDirection: "column", maxHeight: "96vh" },
  reportHead: { display: "flex", alignItems: "center", justifyContent: "center", position: "relative", padding: "4px 20px 12px" },
  reportHeadMin: { display: "flex", alignItems: "center", justifyContent: "flex-end", padding: "4px 20px 12px" },
  reportWordmark: { fontSize: 17, fontWeight: 800, color: "#fff", letterSpacing: 0.2 },
  iconBtnLight: { position: "absolute", right: 8, top: 0, background: "transparent", border: "none", color: "#8b8d92", cursor: "pointer" },
  reportBlueLine: { height: 2, background: "linear-gradient(90deg,transparent,#23a0f2 30%,#23a0f2 70%,transparent)", opacity: 0.85 },

  /* echte A4-Seite: Seitenverhältnis 1 : 1.4142 (210mm x 297mm), nicht gestaucht/gestreckt */
  reportShell: { width: "100%", aspectRatio: "210 / 297", maxHeight: "78vh", overflowY: "auto", background: "#0a0a0d", borderRadius: 4, boxShadow: "0 30px 90px rgba(0,0,0,.55)" },

  pageHeadBar: { fontSize: 10.5, fontWeight: 800, letterSpacing: 1.2, color: "#23a0f2", marginBottom: 26, paddingBottom: 12, borderBottom: "2px solid #23a0f2" },
  articleHero: { height: 150, background: "linear-gradient(160deg,#141420,#0a0a0d)", display: "flex", alignItems: "center", justifyContent: "center", borderBottom: "1px solid #1c1c22" },
  articleMove: { display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginBottom: 18 },
  articleKicker: { fontSize: 11, fontWeight: 800, letterSpacing: 0.8, textTransform: "uppercase", color: "#5fb0ee", margin: "0 0 10px" },
  articleBullets: { margin: "0 0 26px", padding: 0, listStyle: "none", color: "#c8c8cd", fontSize: 12.5, lineHeight: 1.55 },
  articleBulletItem: { position: "relative", paddingLeft: 16, marginBottom: 11 },
  reportPage: { background: "#0a0a0d", padding: "38px 42px 34px", minHeight: "100%", boxSizing: "border-box" },
  reportEyebrow: { fontSize: 11, fontWeight: 700, letterSpacing: 0.8, textTransform: "uppercase", color: "#7a7a82", marginBottom: 8 },
  reportTitle: { fontSize: 27, fontWeight: 800, color: "#fff", margin: "0 0 20px", letterSpacing: -0.3 },
  reportPara: { fontSize: 14.5, lineHeight: 1.8, color: "#dcdce0", margin: "0 0 16px", fontFamily: "Georgia, 'Times New Roman', serif" },
  reportFootnote: { fontSize: 10.5, color: "#6a6a72", marginTop: 24, paddingTop: 14, borderTop: "1px solid #232329", fontStyle: "italic" },

  /* Deckblatt: dunkel, im Stil des Finvest-Blueprint-Covers */
  reportCoverWrap: { display: "flex", flexDirection: "column", minHeight: "100%" },
  reportCover: { background: "#0a0a0d", flex: 1, boxSizing: "border-box", padding: "48px 40px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", position: "relative" },
  coverBlueLine: { height: 2, width: 100, background: "#23a0f2", margin: "14px 0 34px" },
  coverTitle: { fontSize: 25, fontWeight: 800, color: "#fff", margin: "0 0 34px", letterSpacing: -0.2 },
  coverRow: { display: "flex", alignItems: "baseline", gap: 14, marginBottom: 10 },
  coverRowItem: { fontSize: 26, fontWeight: 800, color: "#fff", letterSpacing: -0.3, fontFamily: "var(--mono)" },
  coverRowItemSmall: { fontSize: 16, fontWeight: 700, color: "#dcdce0", letterSpacing: -0.1, fontFamily: "var(--mono)" },
  coverSub: { fontSize: 13, color: "#8b8d92", letterSpacing: 0.4 },
  backNote: { fontSize: 12.5, color: "#8b8d92", lineHeight: 1.7, maxWidth: 320, marginTop: 22 },
  backFooter: { position: "absolute", bottom: 26, fontSize: 10, color: "#5a5a60", letterSpacing: 0.3 },

  reportNav: { display: "flex", alignItems: "center", justifyContent: "center", gap: 16, padding: "14px 20px 6px" },
  reportNavBtn: { width: 32, height: 32, borderRadius: 8, border: "1px solid #26262c", background: "#0d0d10", color: "#dcdce0", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" },
  reportDots: { display: "flex", gap: 6 },
  reportDot: { width: 6, height: 6, borderRadius: 4, background: "#3a3a42", cursor: "pointer" },
  reportDotOn: { background: "#23a0f2", width: 16 },
  reportActions: { display: "flex", gap: 10, padding: "10px 20px 4px" },
  reportActionBtn: { flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 7, background: "#fff", color: "#0a0a0d", border: "none", borderRadius: 10, padding: "12px", fontSize: 12.5, fontWeight: 700, cursor: "pointer", boxShadow: "0 6px 18px rgba(0,0,0,.3)" },
  printDoc: { display: "none" },
};
