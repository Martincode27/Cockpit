# CLAUDE.md — Projekt "Cockpit"

> Diese Datei wird von Claude Code zu Beginn **jeder** Session automatisch gelesen.
> Sie enthält nur Regeln und Architektur. Dieses Repo ist **öffentlich** — hier gehören keine
> Notizen, Befunde, Changelogs oder privaten Details hinein.

**Wissen, Backlog, Entscheidungen, Changelog:** Obsidian-Vault unter
**`D:\Vault\Projects\Cockpit\`** (maßgeblich). Zu Beginn jeder Session dort `00_Start.md` und
`Backlog.md` lesen, am Ende dort dokumentieren.

---

## 1. Sicherheitsregeln

- Claude lädt/installiert nichts ohne ausdrückliche Freigabe des Nutzers.
- Erlaubte Quellen: offizielle Herstellerseiten/offizielle GitHub-Repos, npm-Registry, PyPI.
- API-Keys/Secrets niemals in Code, Git oder Chat — nur in `.env` (in `.gitignore`).
- Claude erstellt **keine** Accounts bei Drittanbietern — das macht der Nutzer selbst.
- Private Daten sind nur nach Login sichtbar; jede Cockpit-Tabelle bekommt RLS nur für
  eingeloggte Nutzer. Nichts Privates darf ohne Login über eine öffentliche URL abrufbar sein.
- **Nicht ohne Freigabe pushen.** Push nur, wenn sich die Webseite selbst ändert.

## 2. Arbeitsweise

- Sprache: Deutsch. Kleine Schritte: erst Konzept abstimmen, dann umsetzen.
- Design ist zweitrangig, bis die echten Daten drin sind. Muss auf dem Handy gut funktionieren.

## 3. Architektur

- **Frontend:** eine HTML-Datei (`index.html`), Vanilla-JS, ohne Bibliotheken.
- **Daten:** Supabase (gleiches Projekt wie das Rezeptbuch). Der Publishable Key steht bewusst im
  Frontend; geschützt wird über Login + RLS. Das Cockpit rechnet nichts selbst aus, sondern zeigt
  an, was die Projekte liefern.
- **Login:** Supabase Auth (E-Mail + Passwort) per `fetch` gegen `/auth/v1/token`. Sitzung in
  `localStorage` (`cockpit_session`), automatischer Token-Refresh. Der Login sperrt nur die
  Oberfläche — echter Schutz entsteht erst durch RLS `to authenticated` auf jeder neuen Tabelle.
- **Hosting:** GitHub Pages aus `main`, `/ (root)`.
