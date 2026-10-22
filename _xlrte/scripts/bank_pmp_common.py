"""Shared helpers for the PMP bank modules (EN, own wording, ECO 2026).

S(en, appr, q, [correct, d1, d2, d3], why, case=None)          single answer — correct option written FIRST
M(en, appr, q, [correct...], [wrong...], why, case=None)       multiple response, 5 options — 'Choose N.' is added
The build shuffles options deterministically per item id, so answer positions are balanced.
appr: predictive | agile | hybrid.   Task (lo) is derived from the enabler id (e.g. PR.6.3 -> PR.6).
"""


def S(en, appr, q, opts, why, case=None):
    assert len(opts) == 4, q
    return {"en": en, "appr": appr, "type": "std", "q": q, "opts": opts, "k": 1, "why": why, "case": case}


def M(en, appr, q, right, wrong, why, case=None):
    assert len(right) + len(wrong) == 5 and len(right) >= 2, q
    words = {2: "two", 3: "three"}
    return {"en": en, "appr": appr, "type": "multi", "q": f"{q} (Choose {words[len(right)]}.)", "opts": right + wrong,
            "k": len(right), "why": why, "case": case}
