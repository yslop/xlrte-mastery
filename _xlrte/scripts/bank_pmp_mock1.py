#!/usr/bin/env python3
"""XLRTE PMP Mock 1 — 180 unseen, self-written questions in three parts of 60 (M1A, M1B, M1C).
Each part follows the ECO 2026 blueprint (People 20 / Process 25 / Business Environment 15 questions, exact quota per
task, see tests/test_pmp_mock.py), approach mix about 40 % predictive / 60 % agile+hybrid, about 12 % Multiple Response.
Parts are runnable alone (60 Q / 80 Min) or together as a full mock (180 Q / 240 Min, breaks after Q60 and Q120).
The items stay hidden from every other mode until the first run (cockpit), so the result measures UNSEEN questions.
No text from books or official exams. Ids: pm_m1a001 …, set M1A/M1B/M1C, mock M1, status "shadow".
Build: python3 scripts/bank_pmp_mock1.py -> data/items_pmp_mock1.json
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank_pmp_mock1_a, bank_pmp_mock1_b, bank_pmp_mock1_c
from stems_caliber_m1 import STEMS     # exam-caliber stems per question number (13.10.2026)

PARTS = (("M1A", bank_pmp_mock1_a), ("M1B", bank_pmp_mock1_b), ("M1C", bank_pmp_mock1_c))


def compile_items():
    items = []
    for pn, (setname, mod) in enumerate(PARTS):
        rnd = random.Random(2026100300 + pn)
        std_n = sum(1 for t in mod.QA if t[3] == "std")
        pos = [k % 4 for k in range(std_n)]                   # balanced key positions, then shuffled
        rnd.shuffle(pos)
        pi = 0
        for n, (lo, bl, appr, typ, q, opts, why) in enumerate(mod.QA, 1):
            q = STEMS.get(setname, {}).get(n, q)
            it = {"id": f"pm_{setname.lower()}{n:03d}", "exam": "pmp", "lo": lo, "bl": bl, "type": typ, "q": q,
                  "why": why, "src": "xlrte-mock1:own", "status": "shadow", "appr": appr, "set": setname, "mock": "M1"}
            if typ == "std":
                key, ds = opts[0], list(opts[1:])
                rnd.shuffle(ds)
                k = pos[pi]; pi += 1
                it["options"] = ds[:k] + [key] + ds[k:]
                it["answer"] = k
            else:
                order = list(range(5))
                rnd.shuffle(order)
                it["options"] = [opts[j] for j in order]
                it["answer"] = sorted(order.index(j) for j in (0, 1))
            items.append(it)
    return items


if __name__ == "__main__":
    items = compile_items()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "items_pmp_mock1.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(len(items), "questions ->", os.path.normpath(out))
