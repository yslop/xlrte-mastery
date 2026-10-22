"""Public edition: packs for any exam, the deterministic drill generator and pack creation."""
import datetime as dt
import json
import os

import gen_drills
import new_pack
import xlrte

CARDS = [{"term": "Term %d" % i, "definition": "Own definition number %d of a concept." % i, "los": ["K%d.1" % (1 + i % 2)], "exam": "demo"} for i in range(8)]
BANK = {"lang": "en", "los": [{"id": "K1.1", "cat": "K1"}, {"id": "K2.1", "cat": "K2"}], "categories": [{"id": "K1", "weight": 50}, {"id": "K2", "weight": 50}]}


def test_generator_is_deterministic_per_day_and_changes_the_next_day():
    d1, d2 = dt.date(2026, 11, 2), dt.date(2026, 11, 3)
    a = gen_drills.generate(d1, {"demo": BANK}, CARDS, n=6)
    b = gen_drills.generate(d1, {"demo": BANK}, CARDS, n=6)
    c = gen_drills.generate(d2, {"demo": BANK}, CARDS, n=6)
    assert a == b and len(a) == 6
    assert [i["options"] for i in a] != [i["options"] for i in c]
    for it in a:
        assert len(it["options"]) == 4 and it["options"][it["answer"]] and it["exam"] == "demo"


def test_generator_never_reveals_the_term_in_its_own_definition():
    cards = CARDS + [{"term": "Sprint", "definition": "A Sprint is a fixed period.", "los": ["K1.1"], "exam": "demo"}]
    items = gen_drills.card_items("demo", cards, {"K1.1": "K1", "K2.1": "K2"}, "en", "2026-11-02", 20)
    for it in items:
        if it["q"].startswith("Which term") and "fixed period" in it["q"]:
            assert "Sprint" not in it["q"]


def test_pmp_calculations_are_plausible():
    for it in gen_drills.pmp_calc("2026-11-02"):
        f = {x["label"]: x["answer"] for x in it["fields"]}
        if "CPI" in f:
            assert 0.5 < f["CPI"] < 2 and 0.5 < f["SPI"] < 2


def test_packs_are_loaded(tmp_path, monkeypatch):
    d = tmp_path / "packs" / "demo"
    d.mkdir(parents=True)
    (d / "pack.json").write_text(json.dumps({"id": "demo", "name": "Demo", "categories": BANK["categories"], "los": BANK["los"]}), encoding="utf-8")
    (d / "items.json").write_text("[]", encoding="utf-8")
    (d / "glossary.json").write_text(json.dumps(CARDS), encoding="utf-8")
    monkeypatch.setattr(xlrte, "P", lambda *a: os.path.join(str(tmp_path), *a))
    packs = xlrte.load_packs()
    assert "demo" in packs and len(packs["demo"][2]) == 8


def test_new_pack_creates_a_skeleton_and_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(new_pack, "ROOT", str(tmp_path))
    r = new_pack.create("AWS Solutions Architect", "AWS SAA", "en", [("Secure", 30), ("Resilient", 70)])
    assert r["created"] and r["id"] == "aws-saa"
    p = json.load(open(os.path.join(r["path"], "pack.json"), encoding="utf-8"))
    assert [c["weight"] for c in p["categories"]] == [30, 70] and len(p["los"]) == 2
    assert new_pack.create("AWS Solutions Architect", "AWS SAA")["created"] is False
