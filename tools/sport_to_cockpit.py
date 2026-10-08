"""Sport-Bereich im Cockpit: fasst Martins Trainingstage aus Formstark zusammen (Supabase-Tabelle sport_tage).

NUR LESEND gegenüber Formstark (nutzt formstark.lesen()). Je Tag eine Liste kurzer Texte, z. B.
  "Park-Calisthenics (60 Min.): Kniebeugen 10×20, Dips 10×12"  ·  "Laufen 32 Min. · 6 km"
Als Trainingstag zählt jeder Tag mit erledigtem Plan-Training, nachgetragenem Workout, einzelnen Übungen
oder einer Aktivität (wie in Formstark). Pausentage ("rest") zählen nicht.
Fenster: letzte 120 Tage; dort in Formstark gelöschte Tage werden auch im Cockpit entfernt.

Aufruf:  python tools/sport_to_cockpit.py [--dry]     (läuft automatisch über cockpit_inbox.py)
Schema + RLS: D:\\Vault\\Projects\\Cockpit\\SQL\\015_sport.sql. Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import formstark
from mail_to_cockpit import login, req

HERE = Path(__file__).resolve().parent
SESS = json.loads((HERE / "formstark_sessions.json").read_text(encoding="utf-8"))
EX = formstark.UEBUNGEN
FENSTER_TAGE = 120


def zahl(x) -> str:
    x = float(x)
    return str(int(x)) if x == int(x) else f"{x:.1f}".replace(".", ",")


def item_text(i: dict) -> str:
    n = EX.get(i.get("e"), {}).get("n", i.get("e", "?"))
    r = f"{i.get('r')}{' s' if i.get('u') == 's' else ''}"
    kg = f" +{zahl(i['kg'])} kg" if i.get("kg") else ""
    return f"{n} {i.get('s')}×{r}{kg}"


def tag_texte(L: dict, st: dict) -> list[str]:
    out = []
    wk = L.get("wk") or []
    wk_src = {w.get("src") for w in wk if w.get("src")}
    eigene = {m.get("id"): m.get("n") for m in (st.get("myw") or [])}
    for w in wk:
        kopf = w.get("n") or "Workout"
        if w.get("min"):
            kopf += f" ({w['min']} Min.)"
        teile = ", ".join(item_text(i) for i in w.get("items") or [])
        out.append(f"{kopf}: {teile}" if teile else kopf)
    for sid in L.get("done") or []:
        if sid == "rest" or sid in wk_src:
            continue
        name = SESS.get(sid) or eigene.get(sid) or "Training"
        saetze = []
        for k, arr in (L.get("sets") or {}).items():
            s, _, e = k.partition(":")
            n = len([x for x in (arr or []) if x])
            if s == sid and n:
                saetze.append(f"{EX.get(e, {}).get('n', e)} {n} Sätze")
        out.append(f"{name}: {', '.join(saetze)}" if saetze else name)
    man = L.get("man") or []
    if man:
        out.append("Übungen: " + ", ".join(item_text(i) for i in man))
    for a in L.get("acts") or []:
        t = f"{a.get('t') or 'Aktivität'} {a.get('min')} Min."
        if a.get("km"):
            t += f" · {zahl(a['km'])} km"
        if a.get("note"):
            t += f" ({a['note']})"
        out.append(t)
    return out


def main() -> None:
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    st, _ = formstark.lesen()
    ab = (date.today() - timedelta(days=FENSTER_TAGE)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for k, L in sorted((st.get("log") or {}).items()):
        if k < ab:
            continue
        texte = tag_texte(L or {}, st)
        if texte:
            rows.append({"tag": k, "eintraege": texte, "aktualisiert": now})
    for r in rows[-10:]:
        print(r["tag"], " | ".join(r["eintraege"]))
    if "--dry" in sys.argv:
        return
    token = login()
    if rows:
        req("POST", "/rest/v1/sport_tage?on_conflict=tag", rows, token, "resolution=merge-duplicates,return=minimal")
    tage = ",".join(r["tag"] for r in rows) or "1900-01-01"
    req("DELETE", f"/rest/v1/sport_tage?tag=gte.{ab}&tag=not.in.({tage})", None, token, "return=minimal")
    print(f"{len(rows)} Trainingstage gemeldet")


if __name__ == "__main__":
    main()
