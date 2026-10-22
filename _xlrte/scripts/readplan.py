"""XLRTE — Lese-Richtwert pro Lerntag (PMP): Rita-Kapitel und PMBOK-8-Seiten (EN) je Fokus-Task, mit Zeitschätzung.

Reine Funktionen, keine Buchtexte. Eingabe sind die Verweise aus data/eco_pmp2026.json (refs.rita, refs.pmbok8_ed).
Schätzung: Rita 1,5 Min/Seite (aktives Lesen von Prüfungsstoff), PMBOK 8 Guide/Standard 2,5 Min/Seite;
"ab S. n" und Key Concepts zählen als feste Leseblöcke.
"""
import re

RATE = {"rita": 1.5, "pmbok": 2.5}
BLOCK_PAGES = {"key": 4, "process": 3}      # Seiten für "Key Concepts (S. n)" und "(ab S. n)"
RITA_CAP_MIN = 25
REF = re.compile(r"^(Guide|Standard)\s+(.*?)\s*\((ab )?S\. (\d+)(?:[–-](\d+))?\)$")


def _span(a, b, rate, cap=None):
    pages = (b - a + 1) if b else 1
    m = pages * rate
    return pages, (min(m, cap) if cap else m)


def parse_ref(s):
    """'Guide 6.4 Lead the Team (ab S. 84)' -> dict(src, label, a, b, minutes) oder None."""
    m = REF.match(s.strip())
    if not m:
        return None
    src, label, ab, a, b = m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)
    key = "Key Concepts" in label
    if b:
        b = int(b)
    elif ab or key:
        b = a + (BLOCK_PAGES["key"] if key else BLOCK_PAGES["process"]) - 1
    pages, minutes = _span(a, b, RATE["pmbok"])
    return {"src": f"PMBOK 8 {src}", "label": label, "a": a, "b": b or a, "pages": pages, "minutes": round(minutes), "kind": "key" if key else "process" if ab else "std"}


def rita_items(refs):
    out = []
    for r in refs or []:
        a, _, b = str(r["pages"]).replace("-", "–").partition("–")
        a, b = int(a), int(b or a)
        pages, minutes = _span(a, b, RATE["rita"], RITA_CAP_MIN)
        out.append({"src": "Rita", "label": f"Kap. {r['ch']} {r['title']}", "a": a, "b": b, "pages": pages, "minutes": round(minutes), "kind": "rita"})
    return out


def items_for_lo(lo):
    """Reihenfolge: erstes Rita-Kapitel, Guide-Prozess, Key Concepts, Standard, zweites Rita-Kapitel."""
    rita = rita_items(lo.get("refs", {}).get("rita"))
    book = [x for x in (parse_ref(s) for s in lo.get("refs", {}).get("pmbok8_ed", [])) if x]
    by = lambda k: [x for x in book if x["kind"] == k]
    return rita[:1] + by("process")[:1] + by("key")[:1] + by("std")[:1] + rita[1:2]


def plan(lo_ids, los_by_id, budget=75):
    """-> (pflicht, optional, minuten). Gleiche Quelle (Kapitel/Abschnitt) einmal pro Tag, mit allen Tasks, die sie bedient.
    Pflicht = Reihenfolge der Tasks, solange die Summe <= budget (mindestens ein Block); der Rest ist optional."""
    ids = [i for i in dict.fromkeys(lo_ids) if i in los_by_id]
    seen, uniq = {}, []
    for rank in range(5):                               # erst die ersten Blöcke aller Tasks, dann die zweiten usw.
        for i in ids:
            its = items_for_lo(los_by_id[i])
            if rank < len(its):
                it = its[rank]
                k = (it["src"], it["label"], it["a"])
                if k in seen:
                    seen[k]["los"].append(i)
                else:
                    seen[k] = dict(it, los=[i])
                    uniq.append(seen[k])
    rita = [x for x in uniq if x["kind"] == "rita"]; book = [x for x in uniq if x["kind"] != "rita"]
    uniq = book + rita                                  # PMBOK 8 (ECO-2026-Stand) zuerst, Rita (11. Aufl., ECO 2021) als Ergänzung für Prüfungsdenken
    must, opt, total = [], [], 0
    for it in uniq:
        if total + it["minutes"] <= budget or not must:
            must.append(it)
            total += it["minutes"]
        else:
            opt.append(it)
    return must, opt, total


def fmt_item(it):
    pg = f"S. {it['a']}" if it["a"] == it["b"] else f"S. {it['a']}–{it['b']}"
    los = "/".join(dict.fromkeys(it.get("los", [])))
    return f"{it['src']} {it['label']} {pg} (ca. {it['minutes']} Min{', ' + los if los else ''})"
