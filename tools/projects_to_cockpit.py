"""Projektübersicht: überträgt die Projekte aus dem Vault ins Cockpit (Supabase-Tabelle projects).

Quelle ist der Vault (D:\\Vault\\Projects\\<Projekt>\\):
  - Steckbrief im Kopf (Frontmatter) von 00_Start.md: status, ziel, stand, naechster_schritt, fortschritt,
    cockpit_reihenfolge, optional projekt (Anzeigename) und cockpit_details: nein (nur Steckbrief).
    Nur Ordner mit "status:" im Steckbrief werden übertragen.
  - Offene Punkte: "- [ ] …" in 00_Start.md und Backlog.md (abgehakte "- [x]" werden nur gezählt).
  - Ideen: einfache Aufzählungen ("- …") unter Überschriften, die "Idee" enthalten.

Aufruf:  python tools/projects_to_cockpit.py        (meldet)
         python tools/projects_to_cockpit.py --dry  (nur anzeigen)
Anmeldung als Bot-Nutzer über tools/.env (wie mail_to_cockpit.py). Schema + RLS:
D:\\Vault\\Projects\\Cockpit\\SQL\\011_projekte.sql. Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from mail_to_cockpit import login, req

VAULT = Path(r"D:\Vault\Projects")
QUELLEN = ("00_Start.md", "Backlog.md")
MAX_TEXT = 240


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    out = {}
    for line in text[4:text.find("\n---", 4)].splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            v = re.sub(r"\s+#.*$", "", m.group(2)).strip()  # Kommentar am Zeilenende weg
            out[m.group(1)] = v[1:-1] if len(v) >= 2 and v[0] == v[-1] == '"' else v
    return out


def clean(s: str) -> str:
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)       # [[Ziel|Text]] -> Text
    s = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m.group(1).split("/")[-1], s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)              # [Text](url) -> Text
    s = s.replace("**", "").replace("__", "").strip()
    return s if len(s) <= MAX_TEXT else s[:MAX_TEXT - 1].rstrip() + "…"


def scan(folder: Path) -> dict | None:
    start = folder / "00_Start.md"
    if not start.exists():
        return None
    fm = frontmatter(start.read_text(encoding="utf-8-sig"))
    if not fm.get("status"):
        return None
    offen, ideen, erledigt = [], [], 0
    for name in QUELLEN:
        f = folder / name
        if not f.exists():
            continue
        heading = ""
        body = f.read_text(encoding="utf-8-sig")
        if body.startswith("---\n"):
            body = body[body.find("\n---", 4) + 4:]
        for line in body.splitlines():
            if re.match(r"^#{1,6}\s", line):
                heading = line.lower()
                continue
            m = re.match(r"^\s*- \[( |x|X)\]\s+(.+)$", line)
            if m:
                if m.group(1) == " ":
                    offen.append({"text": clean(m.group(2)), "quelle": name})
                else:
                    erledigt += 1
                continue
            m = re.match(r"^- (?!\[)(.+)$", line)   # nur oberste Ebene
            if m and "idee" in heading:
                ideen.append({"text": clean(m.group(1)), "quelle": name})
    fort = fm.get("fortschritt", "")
    geaendert = max(p.stat().st_mtime for p in folder.glob("*.md"))
    details = fm.get("cockpit_details", "").lower() not in ("nein", "false", "no")
    return {
        "id": folder.name, "name": fm.get("projekt") or folder.name, "status": fm.get("status"),
        "ziel": fm.get("ziel") or None, "stand": fm.get("stand") or None,
        "naechster_schritt": fm.get("naechster_schritt") or None,
        "fortschritt": float(fort) if re.fullmatch(r"\d+(\.\d+)?", fort) else None,
        "offen": offen if details else [], "ideen": ideen if details else [],
        "erledigt": erledigt if details else None, "details": details,
        "reihenfolge": int(fm["cockpit_reihenfolge"]) if fm.get("cockpit_reihenfolge", "").isdigit() else 99,
        "vault_geaendert": datetime.fromtimestamp(geaendert, timezone.utc).isoformat(),
        "aktualisiert": datetime.now(timezone.utc).isoformat(),
    }


def apply_done(token: str) -> None:
    """Im Cockpit abgehakte Punkte (Tabelle project_item_done) im Vault abhaken: "- [ ]" -> "- [x]".
    Verglichen wird der bereinigte Text wie im Cockpit angezeigt; erledigte bzw. nicht mehr gefundene
    Einträge werden danach aus der Tabelle gelöscht."""
    done = req("GET", "/rest/v1/project_item_done?select=*&order=id", None, token) or []
    for d in done:
        f = VAULT / d["projekt"] / d["quelle"]
        hit = False
        if f.exists() and f.parent.parent == VAULT and d["quelle"] in QUELLEN:
            lines = f.read_text(encoding="utf-8-sig").split("\n")
            for i, line in enumerate(lines):
                m = re.match(r"^(\s*- )\[ \](\s+)(.+)$", line)
                if m and clean(m.group(3)) == d["text"]:
                    lines[i] = f"{m.group(1)}[x]{m.group(2)}{m.group(3)}"
                    hit = True
                    break
            if hit:
                f.write_text("\n".join(lines), encoding="utf-8")
        print(("abgehakt: " if hit else "nicht gefunden (verworfen): ") + f"{d['projekt']}/{d['quelle']}: {d['text'][:60]}")
        req("DELETE", f"/rest/v1/project_item_done?id=eq.{d['id']}", None, token, "return=minimal")


def main() -> None:
    if sys.stdout:  # unter pythonw (Taskplaner, ohne Fenster) gibt es keine Konsole
        sys.stdout.reconfigure(encoding="utf-8")
    token = None
    if "--dry" not in sys.argv:
        token = login()
        try:
            apply_done(token)
        except SystemExit as e:  # req() meldet HTTP-Fehler so, z. B. SQL 012 noch nicht ausgeführt -> Abgleich trotzdem
            print(f"Abhaken übersprungen: {e}")
    rows = [r for r in (scan(d) for d in sorted(VAULT.iterdir()) if d.is_dir()) if r]
    rows.sort(key=lambda r: r["reihenfolge"])
    for r in rows:
        print(f"{r['name']:16s} {r['status']:9s} {str(r['fortschritt'] or '–'):>5} % | offen {len(r['offen']):2d} | "
              f"Ideen {len(r['ideen']):2d} | erledigt {r['erledigt']}")
    if "--dry" in sys.argv:
        return
    req("POST", "/rest/v1/projects?on_conflict=id", rows, token, "resolution=merge-duplicates,return=minimal")
    ids = ",".join(f'"{r["id"]}"' for r in rows)
    req("DELETE", f"/rest/v1/projects?id=not.in.({ids})", None, token, "return=minimal")  # aus dem Vault entfernt
    print(f"{len(rows)} Projekte gemeldet")


if __name__ == "__main__":
    main()
