#!/usr/bin/env python3
"""Deterministic daily drills: new practice questions every day, without any AI call and without third-party text.

Sources are the pack's own material only:
  1. Glossary cards (term + own definition + learning objectives) -> "which term fits this description?" and the reverse.
     Distractors are other terms of the same exam, preferring the same category, so the choice is a real discrimination.
  2. Formula templates (PMP: earned value, PERT) -> calculation drills with new numbers every day ("num" items, drill only).
The day is the seed: the same day always gives the same set (reproducible, testable), the next day a different one.
Weak learning objectives are preferred when the caller passes them.

    python3 scripts/gen_drills.py [--today YYYY-MM-DD] [--n 30]      # writes data/items_gen.json
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "data", "items_gen.json")

TXT = {
    "de": {"d2t": "Welcher Begriff passt zu dieser Beschreibung?\n\n„{d}“", "t2d": "Was beschreibt „{t}“ am besten?",
           "why": "„{t}“: {d}", "calc": "Rechenübung"},
    "en": {"d2t": "Which term matches this description?\n\n\"{d}\"", "t2d": "What best describes \"{t}\"?",
           "why": "\"{t}\": {d}", "calc": "Calculation drill"},
}


def _rng(*parts):
    return random.Random(int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16))


def _mask(definition, term):
    """Hide the term (and its abbreviation in brackets) inside its own definition, so the question does not give it away."""
    out = definition
    for t in {term, re.sub(r"\s*\(.*?\)", "", term).strip()} | set(re.findall(r"\(([^)]+)\)", term)):
        if len(t) >= 2:
            out = re.sub(r"(?i)(?<![\w])" + re.escape(t) + r"(?![\w])", "…", out)
    return out


def card_items(exam, cards, lo_cat, lang, day, n, weak=()):
    """-> up to n multiple-choice items from glossary cards of one exam."""
    T = TXT.get(lang, TXT["de"])
    cards = [c for c in cards if c.get("term") and c.get("definition") and c.get("los")]
    if len(cards) < 4:
        return []
    rnd = _rng(exam, day)
    weak = set(weak)
    ranked = sorted(cards, key=lambda c: (0 if weak & set(c["los"]) else 1, rnd.random()))
    out = []
    for c in ranked[:n]:
        kind = "d2t" if _rng(exam, day, c["term"]).random() < 0.6 else "t2d"
        cat = lo_cat.get(c["los"][0], "")
        pool = [o for o in cards if o is not c and o["term"] != c["term"]]
        same = [o for o in pool if lo_cat.get(o["los"][0], "") == cat]
        r = _rng(exam, day, c["term"], "opts")
        picks = (r.sample(same, min(3, len(same))) if same else [])
        picks += r.sample([o for o in pool if o not in picks], 3 - len(picks))
        if kind == "d2t":
            q, right, wrong = T["d2t"].format(d=_mask(c["definition"], c["term"])), c["term"], [o["term"] for o in picks]
        else:
            q, right, wrong = T["t2d"].format(t=c["term"]), c["definition"], [o["definition"] for o in picks]
        opts = [right] + wrong
        r.shuffle(opts)
        key = hashlib.sha1(("%s|%s|%s" % (exam, c["term"], kind)).encode()).hexdigest()[:10]
        out.append({"id": "gen_%s_%s" % (exam, key), "exam": exam, "lo": c["los"][0], "bl": 1, "type": "std", "q": q, "options": opts,
                    "answer": opts.index(right), "why": T["why"].format(t=c["term"], d=c["definition"]), "src": "xlrte-gen",
                    "status": "approved", "set": "GEN", "gen": day})
    return out


def pmp_calc(day, n=4):
    """Earned value and PERT with new numbers each day. Drill items (no effect on mastery), answer tolerance 0.01."""
    r = _rng("pmp-calc", day)
    out = []
    for i in range(n):
        if i % 2 == 0:
            bac = r.choice(range(100, 1001, 50)) * 1000
            pv = round(bac * r.uniform(0.3, 0.7), -3)
            ev = round(pv * r.uniform(0.75, 1.15), -3)
            ac = round(ev * r.uniform(0.8, 1.25), -3)
            cpi, spi = ev / ac, ev / pv
            eac = bac / cpi
            q = ("BAC = {bac:,.0f} USD, PV = {pv:,.0f} USD, EV = {ev:,.0f} USD, AC = {ac:,.0f} USD. "
                 "Calculate CPI, SPI and EAC (typical variance, EAC = BAC / CPI).").format(bac=bac, pv=pv, ev=ev, ac=ac)
            fields = [{"label": "CPI", "answer": round(cpi, 2), "tol": 0.01}, {"label": "SPI", "answer": round(spi, 2), "tol": 0.01},
                      {"label": "EAC", "answer": round(eac), "tol": max(1000, round(eac * 0.005)), "unit": "USD"}]
            why = "CPI = EV / AC = {:.2f}; SPI = EV / PV = {:.2f}; EAC = BAC / CPI = {:,.0f} USD.".format(cpi, spi, eac)
            lo = "PR.6"
        else:
            o = r.randint(4, 10)
            m = o + r.randint(2, 8)
            p = m + r.randint(3, 14)
            e = (o + 4 * m + p) / 6
            sd = (p - o) / 6
            q = "An activity has O = {} days, M = {} days, P = {} days. Calculate the PERT estimate and the standard deviation.".format(o, m, p)
            fields = [{"label": "PERT", "answer": round(e, 2), "tol": 0.01, "unit": "days"}, {"label": "SD", "answer": round(sd, 2), "tol": 0.01, "unit": "days"}]
            why = "PERT = (O + 4M + P) / 6 = {:.2f}; SD = (P - O) / 6 = {:.2f}.".format(e, sd)
            lo = "PR.8"
        out.append({"id": "gen_pmp_calc_%d" % i, "exam": "pmp", "lo": lo, "type": "num", "q": q, "fields": fields, "why": why,
                    "src": "xlrte-gen", "status": "approved", "drill": "GEN", "gen": day})
    return out


def generate(today, banks, gloss, weak=None, n=30):
    """banks: {exam: bank with los/categories/lang}; gloss: all glossary cards (with 'exam'); weak: {exam: [lo ids]}."""
    day = today.isoformat()
    items = []
    for exam, bank in banks.items():
        lo_cat = {lo["id"]: lo.get("cat", "") for lo in bank.get("los", [])}
        cards = [g for g in gloss if (g.get("exam") or "itil5") == exam and (g.get("los") or [None])[0] in lo_cat]
        lang = bank.get("lang") or ("en" if exam == "pmp" else "de")
        items += card_items(exam, cards, lo_cat, lang, day, n, (weak or {}).get(exam, ()))
        if exam == "pmp":
            items += pmp_calc(day)
    return items


def write(today=None, n=30):
    sys.path.insert(0, HERE)
    import xlrte
    today = today or xlrte.today_local()
    exams = xlrte.cfg().get("exams") or {}
    banks = {k: b for k, b in xlrte.load_banks().items() if k in exams}
    _, _, _, gloss = xlrte.load_content()
    weak = {}
    try:
        comp = xlrte.compute(today)
        weak = {k: [w["id"] if isinstance(w, dict) and "id" in w else (w.get("lo", {}) or {}).get("id") for w in (comp.get(k) or {}).get("weak", [])] for k in banks}
    except Exception:
        pass
    items = generate(today, banks, gloss, weak, n)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    return {"items": len(items), "exams": sorted({i["exam"] for i in items})}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic daily drills from the packs' own cards and formulas")
    ap.add_argument("--today")
    ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args(argv)
    print(json.dumps(write(dt.date.fromisoformat(a.today) if a.today else None, a.n)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
