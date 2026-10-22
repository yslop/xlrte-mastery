"""PMP Mock 2 (Fallen-Mock, set M2A): 60 unseen questions, ECO blueprint, every wrong option carries the trap it lures with."""
import collections, json, os, re
import pytest
from conftest import X
import traps_pmp_rules as R
from test_pmp_mock import QUOTA


def load(name):
    p = os.path.join(X, "data", name)
    if not os.path.exists(p):
        pytest.skip("data/ nicht vorhanden (Test läuft im Drive-Ordner)")
    return json.load(open(p, encoding="utf-8"))


@pytest.fixture(scope="module")
def m2():
    return load("items_pmp_mock2.json")


def test_sixty_questions_follow_the_task_blueprint(m2):
    assert len(m2) == 60 and len({i["id"] for i in m2}) == 60 and len({i["q"] for i in m2}) == 60
    assert dict(collections.Counter(i["lo"] for i in m2)) == QUOTA
    cat = collections.Counter(i["lo"].split(".")[0] for i in m2)
    assert (cat["P"], cat["PR"], cat["BE"]) == (20, 25, 15)


def test_mix_of_approach_types_and_bloom(m2):
    appr = collections.Counter(i["appr"] for i in m2)
    assert 22 <= appr["predictive"] <= 26 and appr["agile"] >= 8 and appr["hybrid"] >= 8, appr
    assert 6 <= sum(i["type"] == "multi" for i in m2) <= 8
    assert sum(i["bl"] == 2 for i in m2) >= 50


def test_format_isolation_and_traps(m2):
    bank = load("items_pmp.json") + load("items_pmp_mock1.json")
    qs = {i["q"] for i in bank}
    w = lambda s: set(re.findall(r"[a-z]+", s.lower()))
    bw = [w(b["q"]) for b in bank]
    for i in m2:
        assert i["exam"] == "pmp" and i["status"] == "shadow" and i["set"] == "M2A" and i["mock"] == "M2"
        assert i["id"].startswith("pm_m2a") and i["q"] not in qs and len(i["why"]) >= 40
        assert 1 <= len(i["traps"]) <= 2 and set(i["traps"]) <= set(R.IDS)
        a = w(i["q"])
        assert max(len(a & b) / len(a | b) for b in bw) < .75, i["id"]
        if i["type"] == "multi":
            assert len(i["options"]) == 5 and len(i["answer"]) == 2 and "(Choose two.)" in i["q"] and "multi" in i["traps"]
            assert i["lures"] == {}
        else:
            assert len(i["options"]) == 4 and isinstance(i["answer"], int)
            wrong = {str(k) for k in range(4) if k != i["answer"]}
            assert set(i["lures"]) == wrong and set(i["lures"].values()) <= set(i["traps"]), i["id"]
        assert len(set(i["options"])) == len(i["options"])


def test_keys_are_balanced_and_no_length_tell(m2):
    std = [i for i in m2 if i["type"] == "std"]
    pos = collections.Counter(i["answer"] for i in std)
    assert min(pos.values()) >= len(std) * .18 and max(pos.values()) <= len(std) * .32, pos
    L = lambda i: [len(o) for o in i["options"]]
    longest = lambda i: all(L(i)[i["answer"]] > l for k, l in enumerate(L(i)) if k != i["answer"])
    shortest = lambda i: all(L(i)[i["answer"]] < l for k, l in enumerate(L(i)) if k != i["answer"])
    assert sum(map(longest, std)) / len(std) <= .35 and sum(map(shortest, std)) / len(std) <= .35


def test_build_takes_over_embedded_traps_and_lures(m2):
    import build_traps as B
    out = B.build(m2, {}, {})
    assert all(out["items"][i["id"]] == i["traps"] for i in m2)
    assert all(out["lures"][i["id"]] == i["lures"] for i in m2 if i["lures"])
