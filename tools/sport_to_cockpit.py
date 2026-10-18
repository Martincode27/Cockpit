"""Sport-Bereich im Cockpit: fasst Martins Trainingstage aus Formstark zusammen (Supabase-Tabelle sport_tage).

NUR LESEND gegenüber Formstark (nutzt formstark.lesen()). Je Tag eine Liste von Blöcken (seit 2026-10-18), z. B.
  {"t": "Calisthenics Park", "i": "700 Wdh. · 60 Min.", "d": ["Liegestütze: 10×20 = 200 Wdh.", …]}
  {"t": "Laufen", "i": "32 Min. · 6 km", "d": ["Locker nach der Arbeit"]}
Wdh. = Sätze × Wiederholungen ohne Halte-Übungen (Plank, Dead Hang, L-Sit … zählen als Sekunden).
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


# Halte-Übungen: Zahl = Sekunden, auch wenn ein Eintrag u="r" hat (z. B. Plank 1×120)
HALTE = {e for e, v in EX.items() if v.get("u") == "s"} | {"plank", "deadhang", "lsit", "sideplank", "hollow", "wallsit"}


def ist_sek(e: str, u: str | None) -> bool:
    return u == "s" or e in HALTE


def name(e: str) -> str:
    return EX.get(e, {}).get("n", e or "?")


def uebungen(items: list[dict]) -> tuple[list[str], int]:
    """Gleiche Übungen hintereinander zusammenfassen: "Australian Pull-ups: 5×15 + 5×5 = 100 Wdh."
    Liefert (Zeilen, Summe Wiederholungen ohne Halte-Übungen)."""
    gruppen: list[list[dict]] = []
    for i in items:
        if gruppen and gruppen[-1][0].get("e") == i.get("e"):
            gruppen[-1].append(i)
        else:
            gruppen.append([i])
    zeilen, reps = [], 0
    for g in gruppen:
        e = g[0].get("e")
        sek = ist_sek(e, g[0].get("u"))
        teile, summe = [], 0
        for i in g:
            s_, r_ = int(i.get("s") or 0), int(i.get("r") or 0)
            kg = f" +{zahl(i['kg'])} kg" if i.get("kg") else ""
            teile.append(f"{s_}×{r_}{' s' if sek else ''}{kg}")
            summe += s_ * r_
        if not sek:
            reps += summe
        einheit = f"{summe} s" if sek else f"{summe} Wdh."
        zeilen.append(f"{name(e)}: {' + '.join(teile)}" + (f" = {einheit}" if len(g) > 1 or g[0].get("s", 1) != 1 else ""))
    return zeilen, reps


def kopf_info(reps: int, minuten=None) -> str:
    teile = []
    if reps:
        teile.append(f"{reps} Wdh.")
    if minuten:
        teile.append(f"{minuten} Min.")
    return " · ".join(teile)


def tag_bloecke(L: dict, st: dict) -> list[dict]:
    """Je Training ein Block {t: Überbegriff, i: Kurzinfo (Wdh./Min./km), r: Wdh. als Zahl, d: [Übungszeilen], n: Notiz}."""
    out = []
    wk = L.get("wk") or []
    wk_src = {w.get("src") for w in wk if w.get("src")}
    eigene = {m.get("id"): m for m in (st.get("myw") or [])}
    for w in wk:
        d, reps = uebungen(w.get("items") or [])
        out.append({"t": w.get("n") or "Workout", "i": kopf_info(reps, w.get("min")), "r": reps, "d": d, "n": w.get("note") or ""})
    for sid in L.get("done") or []:
        if sid == "rest" or sid in wk_src:
            continue
        plan = {it[0]: it[1] for it in (eigene.get(sid) or {}).get("items") or [] if isinstance(it, list) and len(it) == 2}
        items, nur_saetze = [], []
        for k, arr in (L.get("sets") or {}).items():
            s, _, e = k.partition(":")
            n = len([x for x in (arr or []) if x])
            if s != sid or not n:
                continue
            ziel = plan.get(e) or {}
            if ziel.get("hi"):
                items.append({"e": e, "s": n, "r": ziel["hi"], "u": ziel.get("u")})
            else:
                nur_saetze.append(f"{name(e)}: {n} Sätze")
        d, reps = uebungen(items)
        titel = SESS.get(sid) or (eigene.get(sid) or {}).get("n") or "Training"
        out.append({"t": titel, "i": kopf_info(reps), "r": reps, "d": d + nur_saetze})
    man = L.get("man") or []
    if man:
        d, reps = uebungen(man)
        out.append({"t": "Einzelne Übungen", "i": kopf_info(reps), "r": reps, "d": d})
    for a in L.get("acts") or []:
        info = f"{a.get('min')} Min." if a.get("min") else ""
        if a.get("km"):
            info += f" · {zahl(a['km'])} km"
        out.append({"t": a.get("t") or "Aktivität", "i": info.strip(" ·"), "r": 0, "d": [], "n": a.get("note") or ""})
    return out


def tag_texte(L: dict, st: dict) -> list[str]:
    """Kurzform als Text (für Ausgaben/Tests)."""
    return [f"{b['t']}{' (' + b['i'] + ')' if b['i'] else ''}: {', '.join(b['d'] + ([b['n']] if b.get('n') else []))}" if b["d"] or b.get("n") else
            f"{b['t']}{' ' + b['i'] if b['i'] else ''}" for b in tag_bloecke(L, st)]


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
        bloecke = tag_bloecke(L or {}, st)
        if bloecke:
            rows.append({"tag": k, "eintraege": bloecke, "aktualisiert": now})
    for r in rows[-10:]:
        print(r["tag"], json.dumps(r["eintraege"], ensure_ascii=False))
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
