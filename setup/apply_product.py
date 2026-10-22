"""Mastery: turn the setup answers into an exam plan, build or create the learning pack, then the first cockpit.
Never overwrites learning data (events, journal). Messages follow the language chosen in setup."""
import datetime
import json
import os
import subprocess
import sys

BUILD = {
    "pmp": ["build_pack_pmp.py", "bank_pmp.py", "bank_pmp_mock1.py", "bank_pmp_mock2.py", "glossary_pmp.py", "build_traps.py"],
    "itil5": ["build_pack_itil5.py", "bank_itil5.py", "bank_itil5_s3_src.py", "bank_itil5_s4_src.py"],
}
NAMES = {"pmp": ("PMP", "PMP"), "itil5": ("ITIL 5 Foundation (Muster)", "ITIL 5")}


def apply(root, settings):
    a = settings.get("answers") or {}
    en = (settings.get("language") or "de") == "en"
    M = lambda de, eng: eng if en else de
    x = os.path.join(root, "_xlrte")
    scripts = os.path.join(x, "scripts")
    today = datetime.date.today()
    msgs = []
    os.makedirs(os.path.join(x, "data"), exist_ok=True)

    exam = a.get("exam") or "pmp"
    name, short = NAMES.get(exam, (exam, exam))
    if exam == "new":
        sys.path.insert(0, scripts)
        import new_pack
        cats = [new_pack.parse_category(c) for c in (a.get("new_categories") or [])]
        name = a.get("new_name") or M("Meine Prüfung", "My exam")
        short = a.get("new_short") or name
        res = new_pack.create(name, short, a.get("new_lang") or "de", cats, a.get("new_questions") or 40, a.get("new_minutes") or 60, a.get("new_pass") or 65)
        exam = res["id"]
        msgs.append(M("Lernpaket angelegt: _xlrte/packs/%s (Anleitung: README.md darin)", "Learning pack created: _xlrte/packs/%s (guide: README.md inside)") % exam)
    elif exam not in BUILD:
        try:
            with open(os.path.join(x, "packs", exam, "pack.json"), encoding="utf-8") as f:
                p = json.load(f)
            name, short = p.get("name", exam), p.get("short", exam)
        except (OSError, ValueError):
            pass
    for s in BUILD.get(exam, []):
        r = subprocess.run([sys.executable, os.path.join(scripts, s)], cwd=x, capture_output=True, text=True)
        if r.returncode != 0:
            msgs.append(M("Paket-Schritt %s fehlgeschlagen", "Pack step %s failed") % s)
    if exam in BUILD:
        msgs.append(M("Lernpaket gebaut: %s", "Learning pack built: %s") % name)

    cfg_path = os.path.join(x, "config.json")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        with open(os.path.join(x, "config.template.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    ex = cfg.setdefault("exams", {}).setdefault(exam, {})
    ex.update({"name": name, "short": short, "booked": bool(a.get("booked")), "target_pct": int(a.get("target_pct") or 75)})
    if a.get("target_date"):
        ex["target_date"] = a["target_date"]
    ex.setdefault("plan_start", today.isoformat())
    ex.setdefault("pass_pct", int(a.get("new_pass") or 65) if a.get("exam") == "new" else 65)
    cfg["phases"] = [{"name": M("Prüfungsvorbereitung", "Exam preparation"), "exam": exam, "from": today.isoformat(), "to": ex.get("target_date") or "2099-12-31",
                      "attendance_course": name if a.get("course") else "", "mode": "course" if a.get("course") else "self"}]
    cfg["learner"] = a.get("name") or ""
    cfg["language"] = settings.get("language") or "de"
    cfg["course"] = {"attendance": bool(a.get("course"))}
    cfg.setdefault("sla", {}).update({"recap_by": a.get("recap_by") or "21:00", "focus_minutes": int(a.get("daily_minutes") or 60)})
    cfg["streak_min"] = {"retrievals": int(a.get("streak_retrievals") or 25), "focus_minutes": int(a.get("daily_minutes") or 60)}
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    msgs.append(M("Prüfungsplan geschrieben: _xlrte/config.json", "Exam plan written: _xlrte/config.json"))

    if a.get("demo"):
        r = subprocess.run([sys.executable, os.path.join(root, "demo", "load_demo.py")], cwd=root, capture_output=True, text=True)
        msgs.append((r.stdout.strip().splitlines() or [M("Beispiel-Lernverlauf geladen", "Sample learning history loaded")])[-1])
    r = subprocess.run([sys.executable, os.path.join(scripts, "xlrte.py"), "run"], cwd=x, capture_output=True, text=True)
    msgs.append(M("Cockpit gebaut: XLRTE_Cockpit.html", "Cockpit built: XLRTE_Cockpit.html") if r.returncode == 0 else M("Tageslauf fehlgeschlagen: ./mastery prüfen", "Daily run failed: check ./mastery"))
    return msgs
