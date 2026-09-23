# Trading-Journal

Datei: `trading-journal-stats_19.html` (~9.200 Zeilen, eine HTML-Datei wie das alte Rezeptbuch).

## Aufbau
- Backend: Google Sheets über Apps-Script-Web-App (`action=load` / `action=save`), `localStorage` als Zwischenspeicher
- Diagramme: Chart.js
- Bereiche: Trades, Fehler/Review, Konten + Prop-Firmen (Apex, Topstep …) mit EOD-Trailing-DD, Payouts, Finanzen mit Belegen, Rituale, Reminder, Optimizer, Logins

## Kennzahlen (`calcMetrics`)
Netto-G/V · Winrate (gespiegelte Trades über mehrere Konten nur einmal gezählt) · Ø Gewinn/Verlust · RR · Ø CRV (G/V ÷ Risiko) · Max. Drawdown · Profit-Faktor · Serie

## ⚠️ Sicherheitsbefund (2026-09-23)
Die Apps-Script-URL steht im Klartext im HTML und liefert **ohne Login** alle Daten, laut Code auch den **Anthropic-API-Key** und die **gespeicherten Logins**. Wer die URL kennt, kann alles lesen und überschreiben.
→ Nicht so veröffentlichen. Erst auf Supabase mit Login umstellen, Key + Logins raus aus dem Sheet, Key erneuern.
