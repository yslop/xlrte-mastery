#!/usr/bin/env python3
"""ITIL 5 Foundation as a MUSTER pack (pattern): learning-objective IDs, Bloom level, category weights and own short topic
labels. No syllabus text is reproduced: each objective is shown as "<topic> . LO <id>". The questions come from the own
banks (bank_itil5.py, bank_itil5_s3_src.py, bank_itil5_s4_src.py). Use it as the model for any exam with a published
blueprint: copy, rename, replace the IDs and weights.

    python3 scripts/build_pack_itil5.py [--force]
"""
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "data", "syllabus_itil5.json")
CATS = [["1", "Wichtige ITIL Begriffe und Definitionen", 30.0], ["2", "Die vier Dimensionen des Produkt- und Servicemanagements", 10.0], ["3", "Der ITIL Produkt- und Servicelebenszyklus", 10.0], ["4", "Das ITIL Value System", 40.0], ["5", "Wertstromidentifizierung, -abbildung und -management", 5.0], ["6", "ITIL und KI", 2.5], ["7", "ITIL und andere Rahmenwerke", 2.5]]
TOPICS = {
 "1.1": "Produkt- und Servicemanagement",
 "1.2": "Serviceangebot",
 "1.3": "Gemeinsame Wertschöpfung",
 "1.4": "Servicebeziehungen",
 "2.1": "Einführung in die vier Dimensionen",
 "2.2": "Interne und externe Faktoren",
 "3.1": "Einführung in den Lebenszyklus",
 "3.2": "Zweck der Lebenszyklus-Aktivitäten",
 "4.1": "Komponenten des ITIL Value Systems",
 "4.2": "Die ITIL Grundprinzipien",
 "4.3": "Governance",
 "4.4": "Wertschöpfungskette",
 "4.5": "Management-Practices",
 "4.6": "Continual Improvement Model",
 "5.1": "Schlüsselkonzepte Wertstrom",
 "5.2": "Anwendung von Wertströmen",
 "5.3": "Zweck von Wertstromabbildung/-management",
 "6.1": "Einführung in KI",
 "6.2": "ITIL KI-Governance",
 "7.1": "ITIL und DevOps",
 "7.2": "ITIL und PRINCE2"
}
LOS = [["1.1.1", 1], ["1.1.2", 1], ["1.1.3", 1], ["1.1.4", 1], ["1.1.5", 1], ["1.1.6", 1], ["1.1.7", 1], ["1.2.1", 1], ["1.2.2", 1], ["1.2.3", 2], ["1.2.4", 2], ["1.3.1", 1], ["1.3.2", 1], ["1.3.3", 1], ["1.3.4", 2], ["1.3.5", 2], ["1.3.6", 2], ["1.4.1", 1], ["1.4.2", 1], ["1.4.3", 1], ["1.4.4", 1], ["1.4.5", 1], ["1.4.6", 1], ["1.4.7", 1], ["1.4.8", 2], ["1.4.9", 2], ["1.4.10", 2], ["1.4.11", 2], ["2.1.1", 1], ["2.1.2", 2], ["2.1.3", 2], ["2.2.1", 1], ["2.2.2", 2], ["3.1.1", 1], ["3.1.2", 2], ["3.1.3", 2], ["3.2.1", 1], ["3.2.2", 1], ["3.2.3", 1], ["3.2.4", 1], ["3.2.5", 1], ["3.2.6", 1], ["3.2.7", 1], ["3.2.8", 1], ["4.1.1", 1], ["4.1.2", 2], ["4.2.1", 1], ["4.2.2", 2], ["4.2.3", 2], ["4.2.4", 2], ["4.2.5", 2], ["4.2.6", 2], ["4.2.7", 2], ["4.2.8", 2], ["4.2.9", 2], ["4.3.1", 1], ["4.3.2", 2], ["4.4.1", 1], ["4.4.2", 1], ["4.4.3", 1], ["4.4.4", 1], ["4.4.5", 1], ["4.4.6", 1], ["4.4.7", 1], ["4.4.8", 1], ["4.4.9", 1], ["4.4.10", 2], ["4.4.11", 2], ["4.4.12", 2], ["4.5.1", 1], ["4.5.2", 1], ["4.5.3", 2], ["4.5.4", 2], ["4.5.5", 2], ["4.5.6", 1], ["4.6.1", 1], ["4.6.2", 2], ["4.6.3", 2], ["5.1.1", 1], ["5.1.2", 1], ["5.1.3", 1], ["5.1.4", 2], ["5.2.1", 2], ["5.3.1", 1], ["5.3.2", 2], ["5.3.3", 2], ["6.1.1", 1], ["6.1.2", 2], ["6.1.3", 2], ["6.2.1", 1], ["6.2.2", 2], ["7.1.1", 2], ["7.1.2", 2], ["7.2.1", 2], ["7.2.2", 2]]


def main(argv=None):
    force = "--force" in (argv or sys.argv[1:])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT) and not force:
        try:
            if (json.load(open(OUT, encoding="utf-8")) or {}).get("source") != "xlrte-pack-skeleton" and json.load(open(OUT, encoding="utf-8")).get("los"):
                print("syllabus_itil5.json exists and is not the skeleton: kept")
                return 0
        except ValueError:
            pass
    cats = [{"id": c, "name": n, "weight": w, "questions": round(40 * w / 100, 1)} for c, n, w in CATS]
    los = [{"id": i, "cat": i.split(".")[0], "topic": ".".join(i.split(".")[:2]), "topic_name": TOPICS[".".join(i.split(".")[:2])],
            "bl": bl, "text": "%s \u00b7 LO %s" % (TOPICS[".".join(i.split(".")[:2])], i), "book": ""} for i, bl in LOS]
    doc = {"source": "xlrte-pack-skeleton", "name": "ITIL 5 Foundation (Muster)", "lang": "de", "questions": 40, "pass": 26, "minutes": 60,
           "bl_mix": {"1": 40, "2": 60}, "categories": cats, "topics": TOPICS, "los": los}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("ITIL Muster: %d objectives, %d categories" % (len(los), len(cats)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
