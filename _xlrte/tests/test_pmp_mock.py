"""PMP mock exams (M1 = 3 parts x 60 unseen questions, blueprint 33/41/26, ECO 2026).

The sets are separate from the drill bank (items_pmp.json): they stay hidden until the first run so that the
result is an unseen-question measurement (LEARNINGS_ITIL_TO_PMP.md rule 1). Source: scripts/bank_pmp_mock1.py.
"""
import collections, json, os
import pytest
from conftest import X

PARTS = ("M1A", "M1B", "M1C")
# exact task quota per 60-question part: People 20 / Process 25 / Business Environment 15
QUOTA = {"P.1": 2, "P.2": 3, "P.3": 3, "P.4": 3, "P.5": 2, "P.6": 2, "P.7": 2, "P.8": 3,
         "PR.1": 3, "PR.2": 3, "PR.3": 2, "PR.4": 3, "PR.5": 2, "PR.6": 3, "PR.7": 2, "PR.8": 3, "PR.9": 2, "PR.10": 2,
         "BE.1": 2, "BE.2": 2, "BE.3": 2, "BE.4": 2, "BE.5": 2, "BE.6": 1, "BE.7": 2, "BE.8": 2}


def load(name):
    return json.load(open(os.path.join(X, "data", name), encoding="utf-8"))


@pytest.fixture(scope="module")
def mock():
    return load("items_pmp_mock1.json")


@pytest.fixture(scope="module")
def bank():
    return load("items_pmp.json")


def part(mock, p):
    return [i for i in mock if i["set"] == p]


def test_three_parts_of_sixty(mock):
    assert len(mock) == 180
    assert {p: len(part(mock, p)) for p in PARTS} == {p: 60 for p in PARTS}
    assert len({i["id"] for i in mock}) == 180 and len({i["q"] for i in mock}) == 180


@pytest.mark.parametrize("p", PARTS)
def test_part_follows_task_blueprint(mock, p):
    c = collections.Counter(i["lo"] for i in part(mock, p))
    assert dict(c) == QUOTA
    cat = collections.Counter(i["lo"].split(".")[0] for i in part(mock, p))
    assert (cat["P"], cat["PR"], cat["BE"]) == (20, 25, 15)


@pytest.mark.parametrize("p", PARTS)
def test_part_mix_approach_types_bloom(mock, p):
    s = part(mock, p)
    appr = collections.Counter(i["appr"] for i in s)
    assert 22 <= appr["predictive"] <= 26, appr                      # ECO: 40 % predictive / 60 % agile+hybrid
    assert appr["agile"] >= 8 and appr["hybrid"] >= 8, appr
    assert 6 <= sum(i["type"] == "multi" for i in s) <= 8            # Multiple Response ~ 10-13 %
    assert sum(i["bl"] == 2 for i in s) >= 50                        # scenario questions dominate


def test_item_format_and_isolation(mock, bank):
    ids = {i["id"] for i in bank}
    qs = {i["q"] for i in bank}
    for i in mock:
        assert i["exam"] == "pmp" and i["status"] == "shadow" and i["set"] in PARTS and i["mock"] == "M1"
        assert i["id"].startswith("pm_m1") and i["id"] not in ids and i["q"] not in qs
        assert len(i["why"]) >= 40 and i["bl"] in (1, 2) and i["src"].startswith("xlrte-mock")
        if i["type"] == "multi":
            assert len(i["options"]) == 5 and len(i["answer"]) == 2 and i["answer"] == sorted(i["answer"])
            assert "(Choose two.)" in i["q"]
        else:
            assert len(i["options"]) == 4 and isinstance(i["answer"], int) and 0 <= i["answer"] < 4
        assert len(set(i["options"])) == len(i["options"])


def test_keys_are_balanced_and_not_a_length_tell(mock):
    std = [i for i in mock if i["type"] == "std"]
    pos = collections.Counter(i["answer"] for i in std)
    assert min(pos.values()) >= len(std) * .2 and max(pos.values()) <= len(std) * .3, pos

    def longest(i):
        L = [len(o) for o in i["options"]]
        return all(L[i["answer"]] > l for k, l in enumerate(L) if k != i["answer"])
    assert sum(map(longest, std)) / len(std) <= .35


def test_mock_config_and_loader():
    import xlrte
    _, _, items, _ = xlrte.load_content()
    assert sum(1 for i in items if i.get("mock") == "M1") == 180


def test_key_is_not_a_shortest_option_tell_either(mock):
    std = [i for i in mock if i["type"] == "std"]
    def shortest(i):
        L = [len(o) for o in i["options"]]
        return all(L[i["answer"]] < l for k, l in enumerate(L) if k != i["answer"])
    assert sum(map(shortest, std)) / len(std) <= .35


def test_eco_task_ids_exist(mock):
    tasks = {t["id"] for t in load("eco_pmp2026.json")["los"]}
    assert {i["lo"] for i in mock} <= tasks


def test_no_near_duplicates_of_drill_bank(mock, bank):
    """Mock items must be unseen: no question may be (nearly) the same as one in the drill bank."""
    import re
    w = lambda s: set(re.findall(r"[a-z]+", s.lower()))
    bw = [w(b["q"]) for b in bank]
    for i in mock:
        a = w(i["q"])
        worst = max(len(a & b) / len(a | b) for b in bw)
        assert worst < .75, (i["id"], round(worst, 2), i["q"])


def test_stems_have_exam_caliber(mock):
    """13.10.: the trainer describes real stems as ~55 words; first drafts had 12-25. Parts listed in
    scripts/stems_caliber_m1.py must have 45-60 word medians and no stem below 38 or above 70 words."""
    import stems_caliber_m1 as S
    assert set(S.STEMS) >= {"M1A", "M1B", "M1C"}
    for p, repl in S.STEMS.items():
        items = part(mock, p)
        assert sorted(repl) == list(range(1, len(items) + 1)), (p, "stems must cover every question once")
        w = sorted(len(i["q"].split()) for i in items)
        assert w[0] >= 38 and w[-1] <= 70 and 45 <= w[len(w) // 2] <= 60, (p, w[0], w[len(w) // 2], w[-1])
        multi = [i for i in items if i["type"] == "multi"]
        assert all("(Choose two.)" in i["q"] for i in multi), (p, "multi questions keep '(Choose two.)'")
