# Entscheidungen — Cockpit

## 2026-09-23
- **Eigenes Projekt + eigenes Repo** `Martincode27/Cockpit` (privat), getrennt vom Rezeptbuch.
- **Zugriff:** nur ich, aber von überall → Login (Supabase Auth, Registrierung aus), Datenbank-Regeln nur für mein Konto.
- **Das Cockpit rechnet nichts selbst.** Jedes Projekt liefert seine Kennzahlen, das Cockpit zeigt an. Neue Projekte = neue Kachel.
- **Kennzahlen fürs eigene Trading** mit denselben Definitionen wie im Trading-Journal (`calcMetrics`), damit die Zahlen übereinstimmen.
- **Design später.** Erst die echten Daten anbinden, dann Optik anpassen. Muss am Handy funktionieren.
- **Projektfarbe in Obsidian: Rot.**
- **Trading-Journal nicht so veröffentlichen, wie es ist** (siehe [[Trading-Journal]], Sicherheitsbefund).

- **Hosting:** GitHub Pages, Repo `Cockpit` dafür **öffentlich** gestellt. Im Code stehen keine Geheimnisse; die Daten liegen hinter dem Login.
- **Gleiches Supabase-Projekt wie das Rezeptbuch.** Login über Supabase Auth, nur mein Konto, Registrierung aus.
- **Jede neue Cockpit-Tabelle bekommt RLS nur für eingeloggte Nutzer.** Der Login allein sperrt nur die Oberfläche.
