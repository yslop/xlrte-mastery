#!/usr/bin/env python3
"""PMP pack skeleton: the 26 task IDs of the ECO 2026 with OWN short topic labels and the three domain weights.
No outline text is reproduced. Writes data/eco_pmp2026.json. Never overwrites a richer eco file you built yourself from your own copy of the outline.

    python3 scripts/build_pack_pmp.py [--force]
"""
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA = os.path.join(ROOT, "data")
CATS = [("P", "People", 33.0), ("PR", "Process", 41.0), ("BE", "Business Environment", 26.0)]
TOPICS = {
    "P.1": "Shared vision and alignment", "P.2": "Conflict", "P.3": "Team leadership and empowerment", "P.4": "Stakeholder engagement",
    "P.5": "Stakeholder expectations and acceptance", "P.6": "Customer value and feedback", "P.7": "Knowledge transfer",
    "P.8": "Communication", "PR.1": "Integrated planning and approach", "PR.2": "Scope and requirements", "PR.3": "Value delivery",
    "PR.4": "Resources", "PR.5": "Procurement and contracts", "PR.6": "Budget and finances", "PR.7": "Quality",
    "PR.8": "Schedule", "PR.9": "Performance and reporting", "PR.10": "Closure and transition", "BE.1": "Governance",
    "BE.2": "Compliance", "BE.3": "Change control", "BE.4": "Impediments and issues", "BE.5": "Risk",
    "BE.6": "Continuous improvement", "BE.7": "Organizational change", "BE.8": "External environment",
}


def main(argv=None):
    force = "--force" in (argv or sys.argv[1:])
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, "eco_pmp2026.json")
    if os.path.exists(path) and not force:
        with open(path, encoding="utf-8") as f:
            if (json.load(f) or {}).get("source") != "xlrte-pack-skeleton":
                print("eco_pmp2026.json exists and is not the skeleton: kept")
                return 0
    eco = {"source": "xlrte-pack-skeleton", "exam": "pmp", "questions": 180,
           "categories": [{"id": c, "name": n, "weight": w} for c, n, w in CATS],
           "los": [{"id": t, "cat": t.split(".")[0], "text": label, "focus": "", "enablers": [], "refs": {}, "keywords": []}
                   for t, label in TOPICS.items()]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(eco, f, ensure_ascii=False, indent=1)
    print("PMP pack skeleton: %d tasks, %d domains" % (len(TOPICS), len(CATS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
