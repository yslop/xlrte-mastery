#!/usr/bin/env python3
"""XLRTE: length-tell check for single-answer items (lesson from ITIL/PMP authoring: first drafts had the key as the longest option in 80 %+).
Usage: python3 scripts/lengthtell.py FILE.json [--max 35]   -> share of items whose key is the longest / the shortest option; exit 1 above the limit.
"""
import json, sys


def shares(items):
    std = [i for i in items if i.get("type", "std") == "std" and isinstance(i["answer"], int)]
    if not std:
        return 0.0, 0.0, 0
    lens = [[len(o) for o in i["options"]] for i in std]
    longest = sum(1 for i, l in zip(std, lens) if l[i["answer"]] == max(l) and l.count(max(l)) == 1)
    shortest = sum(1 for i, l in zip(std, lens) if l[i["answer"]] == min(l) and l.count(min(l)) == 1)
    return 100 * longest / len(std), 100 * shortest / len(std), len(std)


if __name__ == "__main__":
    path = sys.argv[1]
    limit = float(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 35.0
    data = json.load(open(path, encoding="utf-8"))
    if "--list" in sys.argv:
        for k, i in enumerate(data):
            l = [len(o) for o in i["options"]]
            if isinstance(i["answer"], int) and l[i["answer"]] == max(l) and l.count(max(l)) == 1:
                print("key longest: #%d %s %s  key=%d vs others %s" % (k + 1, i.get("id", ""), i.get("lo"), l[i["answer"]], sorted(x for j, x in enumerate(l) if j != i["answer"])))
    lo, sh, n = shares(data)
    print("%d single-answer items: key longest %.0f %%, key shortest %.0f %% (limit %.0f %%)" % (n, lo, sh, limit))
    sys.exit(1 if max(lo, sh) > limit else 0)
