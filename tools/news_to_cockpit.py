"""Nachrichten-Kachel "Aktuelles": Feed holen und Zusammenfassung ins Cockpit (Supabase) schreiben.

Wird von der geplanten Claude-Aufgabe "nachrichten" aufgerufen (6:30 + 18:30).
Claude fasst die Meldungen selbst zusammen; dieses Skript holt nur den Feed und speichert das Ergebnis:

  python tools/news_to_cockpit.py feed
      Gibt die aktuellen Meldungen von tagesschau.de (RSS) als JSON aus:
      [{"titel", "teaser", "url", "zeit"}] (ohne Video-/Sendungs-Einträge)

  python tools/news_to_cockpit.py push <morgen|abend> <datei.json>
      JSON-Liste [{"titel", "satz", "url", "rubrik"}] -> Upsert in news_digest (id = <datum>-<ausgabe>)

Anmeldung als Bot-Nutzer über tools/.env (wie mail_to_cockpit.py). Schema + RLS:
D:\\Vault\\Projects\\Cockpit\\SQL\\009_news.sql. Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from mail_to_cockpit import login, req

FEED = "https://www.tagesschau.de/index~rss2.xml"
QUELLE = "tagesschau.de (RSS)"


def feed() -> list[dict]:
    r = urllib.request.Request(FEED, headers={"User-Agent": "Cockpit-Nachrichten/1.0"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        root = ET.fromstring(resp.read())
    out = []
    for it in root.iter("item"):
        url = (it.findtext("link") or "").strip()
        if "/video-" in url or "/audio-" in url:  # Sendungen (tagesschau 20 Uhr …) überspringen
            continue
        zeit = it.findtext("pubDate")
        out.append({
            "titel": (it.findtext("title") or "").strip(),
            "teaser": (it.findtext("description") or "").strip(),
            "url": url,
            "zeit": parsedate_to_datetime(zeit).isoformat() if zeit else None,
        })
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 2 and sys.argv[1] == "feed":
        print(json.dumps(feed(), ensure_ascii=False, indent=1))
        return
    if len(sys.argv) < 4 or sys.argv[1] != "push" or sys.argv[2] not in ("morgen", "abend"):
        raise SystemExit(__doc__)
    ausgabe = sys.argv[2]
    punkte = [{k: p.get(k) for k in ("titel", "satz", "url", "rubrik")}
              for p in json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")) if p.get("titel")]
    if not punkte:
        raise SystemExit("Keine Punkte in der Datei")
    jetzt = datetime.now().astimezone()
    req("POST", "/rest/v1/news_digest?on_conflict=id",
        [{"id": f"{jetzt.date().isoformat()}-{ausgabe}", "ausgabe": ausgabe,
          "erstellt": datetime.now(timezone.utc).isoformat(), "punkte": punkte, "quelle": QUELLE}],
        login(), "resolution=merge-duplicates,return=minimal")
    print(f"{len(punkte)} Punkte gemeldet ({ausgabe})")


if __name__ == "__main__":
    main()
