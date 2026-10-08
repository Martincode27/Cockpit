"""Cockpit-Eingang: überträgt Ergebnisse der geplanten Claude-Aufgaben ins Cockpit (Supabase).

Hintergrund: Geplante Claude-Aufgaben (E-Mail-Sortierung, Nachrichten) sollen ohne Rückfrage durchlaufen.
Sie schreiben/lesen deshalb nur Dateien in tools/tmp/ — dieses Skript (Windows-Taskplaner "Cockpit-Eingang",
alle 5 Minuten, pythonw ohne Fenster) erledigt den Rest:

  - tmp/mail_ergebnis.json neu/geändert  -> wie `mail_to_cockpit.py melden` (wichtige Mails + Lauf)
  - tmp/news.json neu/geändert           -> wie `news_to_cockpit.py push` (Morgen/Abend nach Dateizeit)
  - tmp/feed.json                         -> aktueller tagesschau.de-Feed zum Lesen für die Nachrichten-Aufgabe
                                             (erneuert, wenn älter als 20 Minuten)

Verarbeitete Dateien werden über ihren Änderungszeitpunkt in tmp/eingang_status.json gemerkt (nichts gelöscht).
  - Sport: sport_to_cockpit.py (Formstark lesen -> sport_tage) alle 15 Minuten
Fehler landen in tmp/eingang_log.txt. Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = HERE / "tmp"
STATUS = TMP / "eingang_status.json"
LOG = TMP / "eingang_log.txt"
PY = sys.executable.replace("pythonw.exe", "python.exe")
SCRATCH = Path.home() / "AppData" / "Local" / "Temp" / "claude"  # Scratchpads der Claude-Sitzungen


def log(msg: str) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def run(args: list[str]) -> None:
    r = subprocess.run([PY, *args], cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    log(f"{' '.join(args)} -> {r.returncode}: {(r.stdout or '').strip()[:300]} {(r.stderr or '').strip()[-300:]}")
    if r.returncode != 0:
        raise RuntimeError(f"{args} fehlgeschlagen")


def main() -> None:
    TMP.mkdir(exist_ok=True)
    try:
        status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    except Exception:
        status = {}
    # 1) Feed für die Nachrichten-Aufgabe bereitstellen
    feed = TMP / "feed.json"
    if not feed.exists() or time.time() - feed.stat().st_mtime > 20 * 60:
        try:
            r = subprocess.run([PY, "news_to_cockpit.py", "feed"], cwd=HERE, capture_output=True, text=True,
                               encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and r.stdout.strip().startswith("["):
                feed.write_text(r.stdout, encoding="utf-8")
            else:
                log(f"feed -> {r.returncode}: {(r.stderr or '')[-300:]}")
        except Exception:
            log("feed FEHLER " + traceback.format_exc()[-400:])
    # 2) Ergebnisse übertragen, wenn neu. Die geplanten Aufgaben dürfen ohne Rückfrage nur in ihren eigenen
    #    Scratchpad-Ordner schreiben (…\Temp\claude\<Ordner>\<Sitzung>\scratchpad\cockpit\<datei>) — wir nehmen
    #    die neueste Datei aus allen Scratchpads bzw. aus tools/tmp (z. B. bei Läufen von Hand).
    for name, args in (("mail_ergebnis.json", ["mail_to_cockpit.py", "melden"]),
                       ("news.json", ["news_to_cockpit.py", "push"])):
        cands = [TMP / name] + list(SCRATCH.glob(f"*/*/scratchpad/cockpit/{name}"))
        cands = [c for c in cands if c.exists()]
        if not cands:
            continue
        f = max(cands, key=lambda c: c.stat().st_mtime)
        m = f.stat().st_mtime
        if m <= status.get(name, 0):
            continue
        try:
            if name == "news.json":
                # Morgen/Abend nach dem Zeitpunkt, an dem die Aufgabe die Datei geschrieben hat
                args = ["news_to_cockpit.py", "push", "morgen" if datetime.fromtimestamp(m).hour < 12 else "abend", str(f)]
            else:
                if f != TMP / name:  # mail_to_cockpit.py melden liest immer tools/tmp/mail_ergebnis.json
                    (TMP / name).write_text(f.read_text(encoding="utf-8-sig"), encoding="utf-8")
            run(args)
            # auch die Kopie in tools/tmp gilt als erledigt (sonst würde sie beim nächsten Lauf erneut gesendet)
            status[name] = max(m, (TMP / name).stat().st_mtime if (TMP / name).exists() else 0)
            log(f"{name} übernommen aus {f}")
        except Exception:
            log(f"{name} FEHLER " + traceback.format_exc()[-400:])
    # 3) Sport aus Formstark (nur lesend) alle 15 Minuten ins Cockpit
    if time.time() - status.get("sport_lauf", 0) > 15 * 60:
        try:
            run(["sport_to_cockpit.py"])
        except Exception:
            log("sport FEHLER " + traceback.format_exc()[-400:])
        status["sport_lauf"] = time.time()
    STATUS.write_text(json.dumps(status), encoding="utf-8")


if __name__ == "__main__":
    main()
