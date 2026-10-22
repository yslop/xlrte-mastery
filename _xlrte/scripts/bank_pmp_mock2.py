#!/usr/bin/env python3
"""XLRTE PMP Mock 2 (Fallen-Mock) — 60 unseen, self-written questions (set M2A), same ECO blueprint as Mock 1
(People 20 / Process 25 / Business Environment 15, exact quota per task, see tests/test_pmp_mock2.py).
Unlike Mock 1, every question carries its trap tags and every wrong option the trap it lures with
(item fields "traps" and "lures"), which scripts/build_traps.py takes over into data/traps_pmp.json.
Hidden from all other modes until the first run (cockpit mockSeen). No text from books or official exams.
Build: python3 scripts/bank_pmp_mock2.py -> data/items_pmp_mock2.json
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank_pmp_mock2_a

import stems_caliber_m2a
PARTS = (("M2A", bank_pmp_mock2_a),)


def compile_items():
    items = []
    for pn, (setname, mod) in enumerate(PARTS):
        rnd = random.Random(2026100400 + pn)
        std_n = sum(1 for t in mod.QA if t[3] == "std")
        pos = [k % 4 for k in range(std_n)]
        rnd.shuffle(pos)
        pi = 0
        for n, (lo, bl, appr, typ, q, opts, why, traps, lures) in enumerate(mod.QA, 1):
            q = stems_caliber_m2a.STEMS[n]
            it = {"id": f"pm_{setname.lower()}{n:03d}", "exam": "pmp", "lo": lo, "bl": bl, "type": typ, "q": q,
                  "why": why, "src": "xlrte-mock2:own", "status": "shadow", "appr": appr, "set": setname, "mock": "M2",
                  "traps": traps.split()}
            if typ == "std":
                key, ds = opts[0], list(zip(opts[1:], lures))
                assert len(ds) == 3, it["id"]
                rnd.shuffle(ds)
                k = pos[pi]; pi += 1
                seq = ds[:k] + [(key, None)] + ds[k:]
                it["options"] = [o for o, _ in seq]
                it["answer"] = k
                it["lures"] = {str(i): t for i, (_, t) in enumerate(seq) if t}
            else:
                order = list(range(5))
                rnd.shuffle(order)
                it["options"] = [opts[j] for j in order]
                it["answer"] = sorted(order.index(j) for j in (0, 1))
                it["lures"] = {}
            items.append(it)
    return items


if __name__ == "__main__":
    items = compile_items()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "items_pmp_mock2.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(len(items), "questions ->", os.path.normpath(out))
