"""Schreibt die Ergebnisse der E-Mail-Sortierung ins Cockpit (Supabase).

Wird von der geplanten Claude-Aufgabe "E-Mail sortieren" aufgerufen (7:00 + 17:00).
Claude sortiert die Mails selbst über den Gmail-Connector (nur Labels, nichts löschen/antworten)
und übergibt diesem Skript nur das Ergebnis:

  python tools/mail_to_cockpit.py items <datei.json>
      JSON-Liste wichtiger Mails: [{"thread_id", "absender", "betreff", "zusammenfassung",
      "datum" (ISO), "konto", "gmail_url"}] -> Upsert in mail_items (erledigt bleibt unverändert)

  python tools/mail_to_cockpit.py run <wichtig> <info> <unwichtig>
      Zeitstempel + Zählung des Laufs -> mail_runs (für die Ampel im Cockpit)

Anmeldung als Bot-Nutzer; Zugangsdaten in tools/.env (COCKPIT_BOT_EMAIL / COCKPIT_BOT_PASSWORD, nie in Git).
Schema + RLS: D:\\Vault\\Projects\\Cockpit\\SQL\\008_mail.sql. Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPABASE_URL = "https://qqsxtzbukkneptegkbkf.supabase.co"
SUPABASE_KEY = "sb_publishable_pOBjg9lbOcJwV-4qz9ilAw_YZwADBCT"  # öffentlich gedacht, Schutz über Login + RLS
FIELDS = ("thread_id", "absender", "betreff", "zusammenfassung", "datum", "konto", "gmail_url", "kategorie")


def env() -> dict:
    out = {}
    for line in (HERE / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def req(method: str, path: str, body=None, token: str | None = None, prefer: str | None = None):
    h = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    if prefer:
        h["Prefer"] = prefer
    r = urllib.request.Request(SUPABASE_URL + path, method=method, headers=h,
                               data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Supabase {method} {path.split('?')[0]}: HTTP {e.code} {e.read().decode()[:300]}")


def login() -> str:
    e = env()
    return req("POST", "/auth/v1/token?grant_type=password",
               {"email": e["COCKPIT_BOT_EMAIL"], "password": e["COCKPIT_BOT_PASSWORD"]})["access_token"]


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("items", "run"):
        raise SystemExit(__doc__)
    token = login()
    now = datetime.now(timezone.utc).isoformat()
    if sys.argv[1] == "items":
        items = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        rows = [{**{k: it.get(k) for k in FIELDS if k in it}, "kategorie": it.get("kategorie", "wichtig"),
                 "aktualisiert": now} for it in items if it.get("thread_id")]
        if rows:
            req("POST", "/rest/v1/mail_items?on_conflict=thread_id", rows, token,
                "resolution=merge-duplicates,return=minimal")
        print(f"{len(rows)} wichtige Mails gemeldet")
    else:
        w, i, u = (int(x) for x in sys.argv[2:5])
        req("POST", "/rest/v1/mail_runs?on_conflict=id",
            [{"id": "letzter", "gelaufen": now, "neu_wichtig": w, "neu_info": i, "neu_unwichtig": u}],
            token, "resolution=merge-duplicates,return=minimal")
        print(f"Lauf gemeldet: {w} wichtig, {i} Info, {u} unwichtig")


if __name__ == "__main__":
    main()
