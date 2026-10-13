"""Formstark (Sport-App der Freundin): Martins Workouts lesen und eintragen.

Zwei Wege, Umschalter FORMSTARK_BACKEND in tools/.env: "supabase" (neue App b4hkmh9hfg-svg.github.io/Formstark,
Login FORMSTARK_SB_EMAIL/_PASSWORT) oder sonst der alte Firestore-Weg (formstark.netlify.app, unten beschrieben).

Formstark speichert jedes Profil als EIN Firestore-Dokument `data/users/<Team-Code>/state_<profil>` mit den
Feldern `j` (ganzer App-Zustand als JSON-Text) und `upd` (Zeitstempel ms). Workouts liegen in
`log["YYYY-MM-DD"].wk = [{id, src, n, min, feel, note, items:[{e, s, r, u, kg}]}]` — genau wie beim
Nachtragen in der App ("Workout nachtragen"). Zugang: Einladungslink (enthält Firebase-Config + Team-Code)
in tools/.env als FORMSTARK_INVITE (nie in Git, nie ausgeben).

Schutz: Es wird NUR das Profil "martin" gelesen/geschrieben; vor jedem Schreiben wird der bisherige Stand
nach tools/tmp/formstark_backup/ gesichert und geprüft, dass der Profilname "Martin" ist.

Aufruf:
  python tools/formstark.py info                 Überblick über Martins Profil (nur lesen)
  python tools/formstark.py uebungen [suchwort]  Übungs-IDs aus Martins bisherigen Einträgen
Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFIL = "martin"


def env() -> dict:
    out = {}
    for line in (HERE / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def zugang() -> tuple[dict, str]:
    link = env().get("FORMSTARK_INVITE", "")
    if "#join=" not in link:
        raise SystemExit("FORMSTARK_INVITE fehlt oder ist kein Formstark-Einladungslink (…#join=…)")
    p = link.split("#join=", 1)[1]
    p = urllib.parse.unquote(p)
    raw = base64.b64decode(p + "=" * (-len(p) % 4))
    d = json.loads(raw.decode("utf-8"))
    return d["c"], d["t"]


def doc_url(cfg: dict, code: str, profil: str = PROFIL) -> str:
    name = "state" if profil == "me" else "state_" + profil
    path = f"data/users/{urllib.parse.quote(code)}/{name}"
    return (f"https://firestore.googleapis.com/v1/projects/{cfg['projectId']}/databases/(default)/documents/"
            f"{path}?key={urllib.parse.quote(cfg['apiKey'])}")


def http(method: str, url: str, body=None) -> dict:
    req = urllib.request.Request(url, method=method, headers={"Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Firestore {method}: HTTP {e.code} {e.read().decode()[:300]}") from None


# ---------- Neuer Weg: Formstark auf Supabase (seit 2026-10, github.io/Formstark) ----------
# Ein Eintrag = eine Zeile (profile, workouts, eintraege, tageswerte; Umwandlung wie daten.js der App).
# Login mit Martins eigenem Formstark-Zugang (FORMSTARK_SB_EMAIL/_PASSWORT in .env). Umschalter:
# FORMSTARK_BACKEND=supabase (sonst alter Firestore-Weg). URL + publishable key sind öffentlich (stehen in der App).
SB_URL = "https://uxiyjsbhtijrhptwlibs.supabase.co"
SB_KEY = "sb_publishable_sF0G1BqSIXTjOnWAjtYvjg_pZXxBYkZ"
LISTEN = ["prs", "recipes", "shop", "goals", "myw", "cex", "duels", "prog", "tests"]
TAGLISTEN = ["acts", "food"]


def backend() -> str:
    return env().get("FORMSTARK_BACKEND", "firestore").strip().lower()


def sb_http(method: str, path: str, body=None, token: str | None = None, prefer: str | None = None):
    h = {"apikey": SB_KEY, "Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    if prefer:
        h["Prefer"] = prefer
    req = urllib.request.Request(SB_URL + path, method=method, headers=h,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Formstark-Supabase {method} {path.split('?')[0]}: HTTP {e.code} {e.read().decode()[:300]}") from None


def sb_login() -> tuple[str, str]:
    e = env()
    mail, pw = e.get("FORMSTARK_SB_EMAIL", ""), e.get("FORMSTARK_SB_PASSWORT", "")
    if not mail or not pw:
        raise SystemExit("FORMSTARK_SB_EMAIL / FORMSTARK_SB_PASSWORT fehlen in tools/.env")
    d = sb_http("POST", "/auth/v1/token?grant_type=password", {"email": mail, "password": pw})
    return d["access_token"], d["user"]["id"]


def sb_zeilen(token: str, uid: str) -> dict:
    out = {}
    for t in ("profile", "workouts", "eintraege", "tageswerte"):
        rows, off = [], 0
        while True:
            part = sb_http("GET", f"/rest/v1/{t}?select=*&user_id=eq.{uid}&limit=1000&offset={off}", None, token) or []
            rows += part
            if len(part) < 1000:
                break
            off += 1000
        out[t] = rows
    out["profile"] = out["profile"][0] if out["profile"] else None
    return out


def _unpack(d, rid):
    if isinstance(d, dict) and "_v" in d:
        return d["_v"]
    x = dict(d or {})
    ohne = x.pop("_ni", None)
    x.pop("_o", None)
    if not ohne and x.get("id") in (None, ""):
        x["id"] = rid
    return x


def _ordnung(d) -> float:
    o = d.get("_o") if isinstance(d, dict) else None
    return o if isinstance(o, (int, float)) and not isinstance(o, bool) else 1e9


def zeilen_zu_s(rows: dict) -> dict:
    """Python-Gegenstück zu zeilenZuS() aus daten.js der App: Zeilen -> App-Zustand S."""
    S: dict = {}
    p = rows.get("profile")
    if p and isinstance(p.get("einstellungen"), dict):
        S.update(p["einstellungen"])
    S["log"], S["photos"] = {}, {}
    tmp: dict = {}
    for r in rows.get("eintraege") or []:
        if r.get("geloescht") or not r.get("daten"):
            continue
        if r["art"] == "photos":
            S["photos"][r["id"]] = r["daten"].get("_v")
            continue
        item = (_ordnung(r["daten"]), _unpack(r["daten"], r["id"]))
        if r["art"] in LISTEN:
            tmp.setdefault(r["art"], []).append(item)
        elif r["art"] in TAGLISTEN and r.get("tag"):
            tmp.setdefault((r["tag"], r["art"]), []).append(item)
    for art in LISTEN:
        S[art] = [v for _, v in sorted(tmp.get(art, []), key=lambda x: x[0])]
    for k, lst in tmp.items():
        if isinstance(k, tuple):
            S["log"].setdefault(k[0], {})[k[1]] = [v for _, v in sorted(lst, key=lambda x: x[0])]
    wk: dict = {}
    for r in rows.get("workouts") or []:
        if r.get("geloescht"):
            continue
        ex = r.get("extra") if isinstance(r.get("extra"), dict) else {}
        had = ex.get("had") if isinstance(ex.get("had"), list) else None
        w = {} if ex.get("noId") else {"id": r["id"]}
        for f, v in ex.items():
            if f not in ("o", "had", "noId", "rawMin", "rawFeel", "rawN", "rawNote"):
                w[f] = v
        fremd = had is None

        def setze(feld, wert, rawkey=None):
            if had is not None and feld not in had:
                return
            w[feld] = ex[rawkey] if rawkey and rawkey in ex else wert
        setze("n", (r.get("name") or "Workout") if fremd else r.get("name"), "rawN")
        setze("min", r.get("minuten"), "rawMin")
        setze("feel", (r.get("gefuehl") or 0) if fremd else r.get("gefuehl"), "rawFeel")
        setze("note", (r.get("notiz") or "") if fremd else r.get("notiz"), "rawNote")
        if fremd and "src" not in w:
            w["src"] = ""
        setze("items", r.get("uebungen") or [])
        wk.setdefault(r["tag"], []).append((ex.get("o") or 0, w))
    for t, lst in wk.items():
        S["log"].setdefault(t, {})["wk"] = [v for _, v in sorted(lst, key=lambda x: x[0])]
    for r in rows.get("tageswerte") or []:
        d = r.get("daten")
        if not d or d.get("_geloescht"):
            continue
        S["log"].setdefault(r["tag"], {})
        if r["bereich"] != "_leer":
            S["log"][r["tag"]][r["bereich"]] = d.get("v")
    return S


def lesen(profil: str = PROFIL) -> tuple[dict, dict]:
    if backend() == "supabase":
        if profil != PROFIL:
            raise SystemExit("Supabase-Weg liest nur Martins eigenes Profil")
        token, uid = sb_login()
        rows = sb_zeilen(token, uid)
        return zeilen_zu_s(rows), {"backend": "supabase", "uid": uid, "token": token, "rows": rows}
    cfg, code = zugang()
    d = http("GET", doc_url(cfg, code, profil))
    j = d.get("fields", {}).get("j", {}).get("stringValue")
    if not j:
        raise SystemExit("Profil-Dokument hat kein Feld j (Format geändert?)")
    return json.loads(j), d


UEBUNGEN = json.loads((HERE / "formstark_uebungen.json").read_text(encoding="utf-8"))  # aus dem App-Code ausgelesen


def eintragen(datum: str, items: list[dict], name: str = "", minuten=None, notiz: str = "") -> str:
    """Workout wie "Workout nachtragen" in der App an Martins Tag `datum` (YYYY-MM-DD) anhängen.
    items: [{"e": "<Übungs-ID>", "s": Sätze, "r": Wiederholungen bzw. Sekunden}]. Gibt eine Bestätigung zurück."""
    import random
    import re
    import string
    import time
    from datetime import date
    date.fromisoformat(datum)  # wirft bei falschem Datum
    clean = []
    for it in items:
        e = it.get("e")
        if e not in UEBUNGEN:
            raise SystemExit(f"Unbekannte Übung {e!r} – siehe formstark_uebungen.json")
        s, r = int(it.get("s") or 0), int(it.get("r") or 0)
        if s < 1 or r < 1:
            raise SystemExit(f"Sätze/Wiederholungen fehlen bei {UEBUNGEN[e]['n']}")
        clean.append({"e": e, "s": s, "r": r, "u": UEBUNGEN[e].get("u", "r"), "kg": it.get("kg")})
    if not clean and not minuten:
        raise SystemExit("Keine Übungen und keine Dauer angegeben")
    if backend() == "supabase":
        st, raw = lesen()
        if str((st.get("profile") or {}).get("name", "")).strip().lower() != "martin":
            raise SystemExit("Sicherheitsstopp: Profil heißt nicht 'Martin' – nichts geschrieben")
        bdir = HERE / "tmp" / "formstark_backup"
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"martin_sb_{time.strftime('%Y%m%d_%H%M%S')}.json").write_text(
            json.dumps(raw["rows"], ensure_ascii=False), encoding="utf-8")
        # Neue Zeile ohne "extra": die App behandelt sie als Eintrag von außen (daten.js, "fremd").
        wid = "a" + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(7))
        sb_http("POST", "/rest/v1/workouts?on_conflict=user_id,id", [{
            "id": wid, "tag": datum, "name": (name or "Workout").strip()[:50],
            "minuten": round(float(minuten)) if minuten else None, "gefuehl": 0,
            "notiz": (notiz or "").strip()[:140], "quelle": "assistent", "uebungen": clean, "geloescht": False}],
            raw["token"], "resolution=merge-duplicates,return=minimal")
        teile = ", ".join(f"{UEBUNGEN[i['e']]['n']} {i['s']}×{i['r']}{' s' if i['u'] == 's' else ''}" for i in clean)
        return f"Formstark: Workout am {datum} eingetragen – {teile or str(minuten) + ' Min.'}"
    cfg, code = zugang()
    for versuch in range(3):
        st, raw = lesen()
        if str((st.get("profile") or {}).get("name", "")).strip().lower() != "martin":
            raise SystemExit("Sicherheitsstopp: Profil heißt nicht 'Martin' – nichts geschrieben")
        # Sicherung des bisherigen Stands
        bdir = HERE / "tmp" / "formstark_backup"
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"martin_{time.strftime('%Y%m%d_%H%M%S')}.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        log = st.setdefault("log", {})
        day = log.setdefault(datum, {})
        day.setdefault("wk", []).append({
            "id": "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(7)),
            "src": "", "n": (name or "Workout").strip()[:50], "min": round(float(minuten)) if minuten else None,
            "feel": 0, "note": (notiz or "").strip()[:140], "items": clean})
        now = int(time.time() * 1000)
        st["upd"] = now
        body = {"fields": {"j": {"stringValue": json.dumps(st, ensure_ascii=False, separators=(",", ":"))},
                           "upd": {"integerValue": str(now)}}}
        url = doc_url(cfg, code) + "&updateMask.fieldPaths=j&updateMask.fieldPaths=upd" \
            + "&currentDocument.updateTime=" + urllib.parse.quote(raw["updateTime"])
        try:
            req = urllib.request.Request(url, method="PATCH", headers={"Content-Type": "application/json"},
                                         data=json.dumps(body).encode())
            with urllib.request.urlopen(req, timeout=30):
                pass
            teile = ", ".join(f"{UEBUNGEN[i['e']]['n']} {i['s']}×{i['r']}{' s' if i['u'] == 's' else ''}" for i in clean)
            return f"Formstark: Workout am {datum} eingetragen – {teile or str(minuten) + ' Min.'}"
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            if e.code in (400, 409, 412) and "precondition" in msg.lower():
                time.sleep(2)  # Profil wurde zwischendurch geändert (z. B. App am Handy) -> neu lesen
                continue
            raise SystemExit(f"Firestore PATCH: HTTP {e.code} {msg[:300]}") from None
    raise SystemExit("Profil wurde mehrfach gleichzeitig geändert – nichts geschrieben, bitte später nochmal")


def letzte(n: int = 5) -> list[str]:
    st, _ = lesen()
    out = []
    for k in sorted((st.get("log") or {}).keys(), reverse=True):
        for w in (st["log"][k] or {}).get("wk", []):
            teile = ", ".join(f"{UEBUNGEN.get(i['e'], {}).get('n', i['e'])} {i['s']}×{i['r']}" for i in w.get("items", []))
            out.append(f"{k} {w.get('n')}: {teile}")
            if len(out) >= n:
                return out
    return out


def main() -> None:
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    st, raw = lesen()
    if cmd == "info":
        prof = st.get("profile") or {}
        log = st.get("log") or {}
        wk_tage = sorted(k for k, v in log.items() if (v or {}).get("wk"))
        print(f"Profil: {prof.get('name')!r} · Art {st.get('kind')} · Version v{st.get('v')} · upd {st.get('upd')}")
        print(f"Tage im Log: {len(log)} · davon mit nachgetragenen Workouts: {len(wk_tage)} · letzte: {wk_tage[-5:]}")
        felder = sorted({f for v in log.values() for f in (v or {}).keys()})
        print("Felder pro Tag:", felder)
        for k in wk_tage[-2:]:
            print(k, json.dumps(log[k]["wk"], ensure_ascii=False)[:600])
        print("Dokument-Felder:", list(raw.get("fields", {}).keys()), "· updateTime", raw.get("updateTime"))
    elif cmd == "uebungen":
        q = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
        seen = {}
        for v in (st.get("log") or {}).values():
            for w in (v or {}).get("wk", []) + [{"items": (v or {}).get("man", [])}]:
                for it in w.get("items", []):
                    seen[it.get("e")] = seen.get(it.get("e"), 0) + 1
        for e, n in sorted(seen.items(), key=lambda x: -x[1]):
            if q in str(e).lower():
                print(f"{e}: {n}×")


if __name__ == "__main__":
    main()
