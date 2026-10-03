"""Assistent: trägt Sprachnachrichten-Notizen in die Arbeit-Tabellen des Cockpits ein (Supabase).

Fester Aufruf (immer gleich, damit eine einmalige "Immer erlauben"-Freigabe greift):
  python tools/assistent.py
Liest tools/tmp/assistent.json, eine Liste von Aktionen:
  {"aktion": "erfolg",   "titel": "...", "wirkung": "...", "zahl": "...", "kategorie": "...", "datum": "YYYY-MM-DD"}
  {"aktion": "vorhaben", "titel": "...", "beschreibung": "...", "status": "idee|laeuft|umgesetzt|verworfen"}
  {"aktion": "tag",      "tag": "YYYY-MM-DD", "art": "arbeit|urlaub|krank|feiertag",
                         "beginn": "HH:MM", "ende": "HH:MM", "pause_min": 45, "notiz": "..."}
  {"aktion": "lesen",    "was": "erfolge|vorhaben|tage", "anzahl": 10}
Zeiten bei "tag" sind Ortszeit des PCs (Europe/Berlin). Bestehende Tage werden ergänzt (nur übergebene Felder).
Nichts wird gelöscht. Rechte: SQL 013 (Bot darf lesen/anlegen/ändern, nicht löschen).
Anmeldung als Bot-Nutzer über tools/.env (wie mail_to_cockpit.py). Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

from mail_to_cockpit import login, req

DATEI = Path(__file__).resolve().parent / "tmp" / "assistent.json"
KATEGORIEN = {"Zeit", "Geld", "Qualität", "Sicherheit", "Team", "Kunde", "Prozess", "Sonstiges"}


def ts(tag: str, hhmm: str | None) -> str | None:
    if not hhmm:
        return None
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(*(int(x) for x in tag.split("-")), h, m).astimezone().isoformat()  # PC-Zeitzone


def main() -> None:
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    aktionen = json.loads(DATEI.read_text(encoding="utf-8-sig"))
    if isinstance(aktionen, dict):
        aktionen = [aktionen]
    token = login()
    for a in aktionen:
        art = a.get("aktion")
        if art == "erfolg":
            row = {"titel": a["titel"], "wirkung": a.get("wirkung"), "zahl": a.get("zahl"),
                   "kategorie": a.get("kategorie") if a.get("kategorie") in KATEGORIEN else "Sonstiges",
                   "datum": a.get("datum") or date.today().isoformat()}
            req("POST", "/rest/v1/work_wins", [row], token, "return=minimal")
            print(f"Erfolg eingetragen: {row['datum']} – {row['titel']}")
        elif art == "vorhaben":
            row = {"titel": a["titel"], "beschreibung": a.get("beschreibung"), "status": a.get("status") or "idee"}
            req("POST", "/rest/v1/work_plans", [row], token, "return=minimal")
            print(f"Vorhaben eingetragen: {row['titel']} ({row['status']})")
        elif art == "tag":
            tag = a["tag"]
            row = {"tag": tag, "updated_at": datetime.now().astimezone().isoformat()}
            for k in ("art", "pause_min", "notiz"):
                if a.get(k) is not None:
                    row[k] = a[k]
            if a.get("beginn"):
                row["beginn"] = ts(tag, a["beginn"])
            if a.get("ende"):
                row["ende"] = ts(tag, a["ende"])
            req("POST", "/rest/v1/work_days?on_conflict=tag", [row], token, "resolution=merge-duplicates,return=minimal")
            print(f"Arbeitstag {tag} gespeichert: " + ", ".join(f"{k}={v}" for k, v in a.items() if k not in ("aktion", "tag")))
        elif art == "lesen":
            tab, order = {"erfolge": ("work_wins", "datum.desc"), "vorhaben": ("work_plans", "updated_at.desc"),
                          "tage": ("work_days", "tag.desc")}[a.get("was", "erfolge")]
            for r in req("GET", f"/rest/v1/{tab}?select=*&order={order}&limit={int(a.get('anzahl', 10))}", None, token) or []:
                print(json.dumps(r, ensure_ascii=False))
        else:
            print(f"Unbekannte Aktion übersprungen: {a}")


if __name__ == "__main__":
    main()
