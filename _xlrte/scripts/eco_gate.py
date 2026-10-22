#!/usr/bin/env python3
"""XLRTE PMP: ECO-2026-Konformität des Fragenbestands (Maßgabe für die Prüfungsvorbereitung).
Prüft gegen data/eco_pmp2026.json: Domänengewichte (People 33 / Process 41 / Business Environment 26), Ansatzmix (40 % predictiv / 60 % agil+hybrid),
Abdeckung aller 26 Tasks und aller Enabler, Anteil Mehrfachauswahl. Nur Befunde, kein Eingriff.
Usage: python3 scripts/eco_gate.py [--list-enablers]
"""
import collections, json, os, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TOL_DOMAIN_PP = 8
TOL_APPR_PP = 10
MIN_PER_TASK = 8


def evaluate(items, eco):
    pm = [i for i in items if i.get("exam") == "pmp" and i.get("status") != "candidate"]
    findings, stats = [], {}
    w = {c["id"]: c["weight"] for c in eco["categories"]}
    cat_of = {t["id"]: t["cat"] for t in eco["los"]}
    n = len(pm) or 1
    share = collections.Counter(cat_of.get(i["lo"]) for i in pm)
    stats["domain_pct"] = {c: round(100 * share[c] / n, 1) for c in w}
    for c, wt in w.items():
        if abs(stats["domain_pct"][c] - wt) > TOL_DOMAIN_PP:
            findings.append(f"Domäne {c}: {stats['domain_pct'][c]} % der Fragen, ECO verlangt {wt} %")
    tagged = [i for i in pm if i.get("appr")]
    if tagged:
        pred = 100 * sum(1 for i in tagged if i["appr"] == "predictive") / len(tagged)
        stats["predictive_pct"] = round(pred, 1)
        if abs(pred - 40) > TOL_APPR_PP:
            findings.append(f"Ansatzmix: {pred:.0f} % predictiv, ECO erwartet ca. 40 %")
    per_task = collections.Counter(i["lo"] for i in pm)
    thin = [t["id"] for t in eco["los"] if per_task[t["id"]] < MIN_PER_TASK]
    if thin:
        findings.append("Tasks mit weniger als %d Fragen: %s" % (MIN_PER_TASK, ", ".join(thin)))
    en_all = [e["id"] for t in eco["los"] for e in t["enablers"]]
    cov = collections.Counter(i["en"] for i in pm if i.get("en"))
    zero = [e for e in en_all if cov[e] == 0]
    stats["enablers"] = len(en_all)
    stats["enablers_covered"] = len(en_all) - len(zero)
    stats["enablers_zero"] = zero
    if zero:
        findings.append(f"{len(zero)} von {len(en_all)} Enablern ohne getaggte Frage")
    multi = sum(1 for i in pm if i.get("type") == "multi")
    stats["multi_pct"] = round(100 * multi / n, 1)
    return {"findings": findings, "stats": stats, "n_items": len(pm)}


def load_items(root=ROOT):
    items = []
    for f in sorted(os.listdir(os.path.join(root, "data"))):
        if f.startswith("items_pmp") and f.endswith(".json") and "defects" not in f:
            items += [i for i in json.load(open(os.path.join(root, "data", f), encoding="utf-8")) if not i.get("drill")]   # Drill-Sets zählen nicht für die ECO-Abdeckung
    return items


if __name__ == "__main__":
    eco = json.load(open(os.path.join(ROOT, "data", "eco_pmp2026.json"), encoding="utf-8"))
    r = evaluate(load_items(), eco)
    print(json.dumps({"n_items": r["n_items"], **{k: v for k, v in r["stats"].items() if k != "enablers_zero"}}, ensure_ascii=False))
    for f in r["findings"]:
        print("ECO:", f)
    if "--list-enablers" in sys.argv:
        print("ohne Frage:", ", ".join(r["stats"]["enablers_zero"]))
    sys.exit(1 if r["findings"] else 0)
