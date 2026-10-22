#!/usr/bin/env python3
"""Baut data/traps_pmp.json (Taxonomie, Frage->Fallen, Option->Falle) aus Regeln + kuratierten Einträgen.
Usage: python3 scripts/build_traps.py [--check]   (--check validiert nur und schreibt nichts)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from traps_pmp_rules import TAXONOMY, IDS, auto_traps

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _answers(it):
    a = it["answer"]
    return list(a) if isinstance(a, list) else [a]


def build(items, curated, lures_src):
    errors, out_items, out_lures = [], {}, {}
    by_id = {it["id"]: it for it in items}
    for it in items:
        tags = curated[it["id"]].split() if it["id"] in curated else (it.get("traps") or auto_traps(it))
        bad = [t for t in tags if t not in IDS]
        if bad:
            errors.append(f"{it['id']}: unbekannte Falle {bad}")
        if not 1 <= len(tags) <= 2:
            errors.append(f"{it['id']}: braucht 1-2 Fallen, hat {len(tags)}")
        out_items[it["id"]] = tags
    for iid in curated:
        if iid not in by_id:
            errors.append(f"{iid}: unbekannte Frage in der Korrekturdatei")
    lures_all = {**{i["id"]: i["lures"] for i in items if i.get("lures")}, **lures_src}   # Fragen mit eingebetteten Lures (ab Mock 2)
    for iid, m in lures_all.items():
        it = by_id.get(iid)
        if not it:
            errors.append(f"{iid}: unbekannte Frage bei den Lures")
            continue
        res = {}
        for frag, trap in m.items():
            if frag.isdigit() and it.get("lures") and frag in it["lures"] and m is it["lures"]:   # eingebettet: Index -> Falle
                hits = [int(frag)]
            else:
                hits = [k for k, o in enumerate(it["options"]) if frag in o]
            if len(hits) != 1:
                errors.append(f"{iid}: Option '{frag}' nicht eindeutig ({len(hits)} Treffer)")
            elif hits[0] in _answers(it):
                errors.append(f"{iid}: Lure '{frag}' ist die richtige Option")
            elif trap not in IDS:
                errors.append(f"{iid}: unbekannte Falle {trap} im Lure")
            elif trap not in out_items.get(iid, []):
                errors.append(f"{iid}: Lure '{frag}' ({trap}) gehört nicht zu den Fallen der Frage {out_items.get(iid)}")
            else:
                res[str(hits[0])] = trap
        out_lures[iid] = res
    if errors:
        raise ValueError("\n".join(errors))
    return {"version": 1, "taxonomy": TAXONOMY, "items": out_items, "lures": out_lures}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    import traps_pmp_curated_bank as cb, traps_pmp_curated_mock1 as cm
    items = []
    for f in ("items_pmp.json", "items_pmp_mock1.json", "items_pmp_mock2.json", "items_pmp_mock3.json", "items_pmp_sz1.json", "items_pmp_sz2.json", "items_pmp_m2b.json", "items_pmp_m2c.json"):
        p = os.path.join(ROOT, "data", f)
        if os.path.exists(p):
            items += json.load(open(p, encoding="utf-8"))
    import traps_pmp_curated_ethik as ce
    cp = os.path.join(ROOT, "data", "items_candidates.json")
    eth_items, eth_cur = ce.resolve(json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else [])
    out = build(items + eth_items, {**cb.CURATED, **cm.CURATED, **eth_cur}, cm.LURES)
    if "--check" in argv:
        print("ok", len(out["items"]), "Fragen,", len(out["lures"]), "mit Lures")
        return
    path = os.path.join(ROOT, "data", "traps_pmp.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    print(len(out["items"]), "Fragen ->", path)


if __name__ == "__main__":
    main()
