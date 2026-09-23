# CLAUDE.md — Projekt "Cockpit"

> Diese Datei wird von Claude Code zu Beginn **jeder** Session automatisch gelesen.
> Sie ist das verbindliche Regelwerk für dieses Projekt.
> Claude: Aktualisiere Abschnitt 7 (Changelog) am Ende jeder Session.

Wissensspeicher/Notizen (Backlog, Entscheidungen, Journal) liegen im Obsidian-Vault unter
**`D:\Vault\Projects\Cockpit\`** (Projektfarbe in Obsidian: **Rot**). Solange eine Session keinen
Zugriff auf `D:\` hat (z. B. Cloud-Session), liegen die Notizen als kopierfertige Vorlage in
`obsidian/` in diesem Repo — die lokale Claude-Code-Session überträgt sie in den Vault.

Zuletzt aktualisiert: 2026-09-23

---

## 0. Projektziel

Ein persönliches Dashboard ("Cockpit"), auf dem der Nutzer alle seine Projekte auf einen Blick sieht:

- **Trading-Bots:** läuft/gestoppt, Kontostand, Anzahl Trades, Winrate, CRV, Gewinn/Verlust,
  Drawdown, Profit-Faktor, Verlauf.
- **Eigenes Trading:** dieselben Kennzahlen, Quelle ist das eigene Trading-Journal.
- **Rezeptbuch:** Anzahl Rezepte, neue Rezepte diese Woche, Link zur App
  (https://martincode27.github.io/Rezepte/).
- **Trading-Journal:** Link + letzte Einträge, sobald das Journal als Webseite läuft.
- **YouTube-Kanäle:** Abos, Aufrufe, neueste Videos — sobald die Kanäle starten.

Nur der Nutzer selbst greift zu, aber **von überall** (PC + Handy).

---

## 1. Sicherheitsregeln

- Claude lädt/installiert nichts ohne ausdrückliche Freigabe des Nutzers.
- Erlaubte Quellen: offizielle Herstellerseiten/offizielle GitHub-Repos, npm-Registry, PyPI.
- API-Keys/Secrets niemals in Code, Git oder Chat — nur in `.env` (in `.gitignore`).
- Claude erstellt **keine** Accounts bei Drittanbietern — das macht der Nutzer selbst.
- **Kontodaten, Trades und Zugangsdaten sind privat.** Das Dashboard zeigt sie nur nach Login;
  die Datenbank-Regeln (RLS) erlauben Lesen nur für das Konto des Nutzers. Nichts davon darf
  ohne Login über eine öffentliche URL abrufbar sein.

---

## 2. Arbeitsweise

- Sprache: Deutsch.
- Kleine Schritte: erst Konzept abstimmen, dann umsetzen.
- Design ist zweitrangig, bis die echten Daten drin sind (Nutzer-Entscheidung 2026-09-23).
- Muss auf dem Handy gut funktionieren.

---

## 3. Architektur (geplant)

- **Frontend:** eine HTML-Datei (`index.html`), Vanilla-JS, wie beim Rezeptbuch.
- **Daten:** Supabase (dasselbe Projekt wie das Rezeptbuch oder ein eigenes — noch offen).
  Das Dashboard rechnet nichts selbst aus, sondern zeigt an, was die Projekte liefern:
  - Rezeptbuch → liest direkt `recipes` (`created_at` für "neu diese Woche").
  - Trading-Bots → schreiben regelmäßig Status + Kennzahlen in eine eigene Tabelle.
  - Eigenes Trading → aus dem Trading-Journal.
  - YouTube → YouTube Data API.
- **Login:** Supabase Auth, nur ein Konto (Registrierung abgeschaltet).
- **Hosting:** offen — siehe Abschnitt 5.

---

## 4. Trading-Journal (Bestand, Stand 2026-09-23)

Vom Nutzer als Datei geliefert: `trading-journal-stats_19.html` (~9.200 Zeilen, Single-File-App).

- Backend: Google Sheets über eine **Apps-Script-Web-App** (`action=load` / `action=save`),
  plus `localStorage` als Zwischenspeicher. Chart.js für Diagramme.
- Trade-Felder (`TRADE_COLS`): id, symbol, date, time, direction, qty, entry, exit, pnl, commission,
  pnlNet, duration, setup, emotion, notes, status, source, partials, risk, tvlink, possibleTPs,
  errorDesc, errorImg, sweep, entryType, account, entryTF, groupId, statusOverride.
- Kennzahlen (`calcMetrics`): Netto-G/V, Winrate (gespiegelte Trades über mehrere Konten nur einmal
  gezählt), Ø Gewinn/Verlust, RR, Ø CRV (G/V ÷ Risiko), Max. Drawdown, Profit-Faktor, Serie.
  Das Cockpit soll **dieselben Definitionen** verwenden, damit die Zahlen übereinstimmen.
- Weitere Bereiche: Konten/Prop-Firmen (Apex, Topstep, …) mit EOD-Trailing-DD, Payouts, Finanzen
  mit Belegen, Rituale, Reminder, Optimizer, gespeicherte Logins.

### ⚠️ Sicherheitsbefund
Die Apps-Script-URL steht im Klartext im HTML und liefert **ohne Login** alle Daten aus — laut Code
auch einen Anthropic-API-Key (`settings.anthropicApiKey`) und einen Bereich mit gespeicherten
Zugangsdaten (`logins`). Wer die URL kennt, kann alles lesen und überschreiben.
→ Das Journal darf **so nicht** öffentlich ins Netz. Vor der Veröffentlichung: Backend auf
Supabase mit Login umstellen (wie beim Rezeptbuch), API-Key und Zugangsdaten raus aus dem Sheet.
Den API-Key sollte der Nutzer vorsorglich erneuern.

---

## 5. Offene Entscheidungen

- **Hosting:** Das Repo `Martincode27/Cockpit` ist **privat**. GitHub Pages geht mit privaten Repos
  nur mit einem kostenpflichtigen GitHub-Plan (Pro). Optionen: (a) GitHub Pro, (b) Repo öffentlich
  machen — unkritisch, weil im Code keine Geheimnisse stehen und die Daten hinter dem Login liegen,
  (c) anderer kostenloser Hoster, der private Repos kann (neuer Account nötig, legt der Nutzer an).
- Welche Trading-Bots gibt es, wo laufen sie, welche Plattform? → steht im Vault
  (`D:\Vault\Projects\TradingBot\`), in der Cloud-Session nicht lesbar.
- Anzahl und Namen der YouTube-Kanäle.

---

## 6. Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Dashboard — aktuell **Entwurf mit Beispieldaten** |
| `obsidian/` | Kopiervorlage für den Vault-Ordner `Projects\Cockpit\` inkl. roter Projektfarbe |

---

## 7. Session-Changelog

### 2026-09-23 — Session 1 (Cloud-Session, gestartet aus dem Rezepte-Repo)
- Idee und Konzept abgestimmt: Dashboard für Bots, eigenes Trading, Rezeptbuch, Journal, YouTube.
- Klickbarer Entwurf mit Beispieldaten gebaut (`index.html`); Nutzer: Design später, erst Daten.
- Repo `Martincode27/Cockpit` vom Nutzer angelegt (privat).
- Trading-Journal-HTML analysiert (Datenmodell, Kennzahlen, Sicherheitsbefund → Abschnitt 4).
- Obsidian-Vault war aus der Cloud-Session nicht erreichbar → Notizen als Vorlage in `obsidian/`.
