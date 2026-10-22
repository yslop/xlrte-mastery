#!/usr/bin/env python3
"""Fictional learning history for "Sam Beispiel": three weeks of practice on the exam chosen in setup, with a realistic
learning curve, so the cockpit, streak, error management, recap and forecast are populated. Every event is marked
(id prefix e_demo_, meta.demo = true).

    python3 demo/load_demo.py            # add (run setup first, it builds the pack)
    python3 demo/load_demo.py --remove   # drop exactly the demo events (a backup of events.csv is kept)
"""
import argparse
import csv
import datetime
import json
import os
import random
import shutil
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X = os.path.join(ROOT, "_xlrte")
EVENTS = os.path.join(X, "state", "events.csv")
COLS = ["id", "ts", "date", "kind", "exam", "ref", "value", "minutes", "meta"]


def _exam_and_items():
    sys.path.insert(0, os.path.join(X, "scripts"))
    import xlrte
    c = xlrte.cfg()
    exam = ((c.get("phases") or [{}])[0] or {}).get("exam") or next(iter(c.get("exams") or {}), "pmp")
    _, _, items, _ = xlrte.load_content()
    return exam, [i for i in items if i.get("exam") == exam and i.get("type", "std") == "std" and i.get("lo") and not i.get("gen")]


def add(today, days=21, seed=7):
    exam, items = _exam_and_items()
    if len(items) < 10:
        en = "Too few questions in the pack for a sample history (at least 10)."
        print("Zu wenige Fragen im Paket für einen Beispielverlauf (mindestens 10). / " + en)
        return 1
    rnd = random.Random(seed)
    skill, rows = {}, []
    for d in range(days, 0, -1):
        day = today - datetime.timedelta(days=d)
        if day.weekday() >= 5 and rnd.random() < 0.6:
            continue
        for it in rnd.sample(items, min(len(items), rnd.randint(18, 40))):
            lo = it.get("lo")
            p = min(0.9, 0.45 + skill.get(lo, 0) * 0.08 + (days - d) * 0.006)
            ok = rnd.random() < p
            conf = "sure" if rnd.random() < (0.7 if ok else 0.35) else "guess"
            skill[lo] = skill.get(lo, 0) + 1
            rows.append(_ev(day, "attempt", exam, it["id"], 1 if ok else 0, "", {"mode": "drill", "conf": conf, "demo": True}))
        rows.append(_ev(day, "focus", exam, "", "", rnd.choice([25, 40, 50, 60]), {"demo": True}))
    os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
    new = not os.path.exists(EVENTS)
    with open(EVENTS, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        w.writerows(rows)
    print("Sam Beispiel (demo): %d events / Ereignisse, %d days / Tage, exam %s." % (len(rows), len({r["date"] for r in rows}), exam))
    return 0


def _ev(day, kind, exam, ref, value, minutes, meta):
    return {"id": "e_demo_" + uuid.uuid4().hex[:10], "ts": "%sT18:00:00" % day.isoformat(), "date": day.isoformat(), "kind": kind,
            "exam": exam, "ref": ref, "value": value, "minutes": minutes, "meta": json.dumps(meta)}


def remove():
    if not os.path.exists(EVENTS):
        print("No learning history / Kein Lernverlauf.")
        return 0
    shutil.copy2(EVENTS, EVENTS + ".before-demo-remove")
    with open(EVENTS, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keep = [r for r in rows if not r["id"].startswith("e_demo_")]
    with open(EVENTS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(keep)
    print("%d demo events removed / entfernt (backup: events.csv.before-demo-remove)." % (len(rows) - len(keep)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args(argv)
    return remove() if a.remove else add(datetime.date.today())


if __name__ == "__main__":
    sys.exit(main())
