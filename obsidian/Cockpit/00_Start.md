---
projekt: Cockpit
farbe: rot
repo: https://github.com/Martincode27/Cockpit
tags: [projekt, cockpit]
---
# Cockpit

Persönliches Dashboard mit allen Projekten auf einen Blick. Nur ich greife darauf zu, aber von überall (PC + Handy).

## Was drauf soll
- **Trading-Bots:** läuft/gestoppt, Kontostand, Trades, Winrate, CRV, G/V, Drawdown, Profit-Faktor, Verlauf
- **Eigenes Trading:** dieselben Kennzahlen, Quelle: [[Trading-Journal]]
- **Rezeptbuch:** Anzahl Rezepte, neu diese Woche, Link → https://martincode27.github.io/Rezepte/
- **Trading-Journal:** Link + letzte Einträge, sobald es als Webseite läuft
- **YouTube-Kanäle:** Abos, Aufrufe, neueste Videos, sobald die Kanäle starten

## Architektur (geplant)
- Eine HTML-Datei (Vanilla-JS) wie beim Rezeptbuch
- Daten aus Supabase; jedes Projekt liefert seine Kennzahlen, das Cockpit zeigt sie nur an
- Login über Supabase Auth, nur mein Konto
- Code: Repo `Martincode27/Cockpit` (privat)

Siehe [[Entscheidungen]] · [[Backlog]]
