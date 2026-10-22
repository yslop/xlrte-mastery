import json, os
import pytest
from conftest import X
import traps_pmp_rules as R
import build_traps as B


def it(id_, q, options, answer=0, typ="std", **kw):
    return dict(id=id_, exam="pmp", q=q, options=options, answer=answer, type=typ, **kw)


def test_taxonomy_has_nine_traps_with_rules():
    assert R.IDS == ["kw", "act", "esc", "appr", "term", "calc", "multi", "role", "eth"]
    assert all(t["name"] and len(t["rule"]) > 20 for t in R.TAXONOMY)


def test_auto_rules():
    assert R.auto_traps(it("a", "What should the project manager do FIRST?", ["a", "b", "c", "d"])) == ["kw"]
    assert R.auto_traps(it("b", "Which TWO ...? (Choose two.)", list("abcde"), [0, 1], "multi")) == ["multi"]
    assert "calc" in R.auto_traps(it("c", "What is the schedule performance index?", ["0.80", "1.25", "0.89", "1.13"]))
    assert "calc" in R.auto_traps(it("d", "PV is 100, EV is 80. What is the SPI?", ["a", "b", "c", "d"]))
    assert R.auto_traps(it("e", "A team is formed. What happens?", ["a", "b", "c", "d"])) == []


def test_build_prefers_curated_and_resolves_lures():
    items = [it("x1", "Q?", ["Escalate to the PMO director", "Talk to both leads", "Wait", "Replace one"], 1)]
    out = B.build(items, {"x1": "act esc"}, {"x1": {"Escalate to": "esc", "Replace": "act"}})
    assert out["items"] == {"x1": ["act", "esc"]}
    assert out["lures"] == {"x1": {"0": "esc", "3": "act"}}
    assert [t["id"] for t in out["taxonomy"]] == R.IDS


@pytest.mark.parametrize("curated,lures,msg", [
    ({"x1": "act foo"}, {}, "unbekannte Falle"),
    ({"x1": ""}, {}, "1-2 Fallen"),
    ({"x1": "act esc role"}, {}, "1-2 Fallen"),
    ({"x1": "act", "zzz": "act"}, {}, "unbekannte Frage"),
    ({"x1": "act"}, {"x1": {"Talk to": "act"}}, "richtige Option"),
    ({"x1": "act"}, {"x1": {"nope": "act"}}, "nicht eindeutig"),
])
def test_build_rejects_bad_input(curated, lures, msg):
    items = [it("x1", "Q?", ["Escalate to the PMO director", "Talk to both leads", "Wait", "Replace one"], 1)]
    with pytest.raises(ValueError, match=msg):
        B.build(items, curated, lures)


def test_build_rejects_lure_trap_that_is_not_a_tag_of_the_question():
    items = [it("x1", "Q?", ["Escalate to the PMO director", "Talk to both leads", "Wait", "Replace one"], 1)]
    with pytest.raises(ValueError, match="nicht zu den Fallen der Frage"):
        B.build(items, {"x1": "act"}, {"x1": {"Escalate to": "esc"}})


def test_build_without_any_traps_fails():
    with pytest.raises(ValueError, match="1-2 Fallen"):
        B.build([it("x2", "Plain question?", ["a", "b", "c", "d"])], {}, {})


import trapstats as TS

FX = os.path.join(X, "tests", "trap_stats_fixture.json")


def fixture():
    return json.load(open(FX, encoding="utf-8"))


def test_trap_stats_matches_fixture():
    fx = fixture()
    got = TS.trap_stats(fx["events"], fx["items"], fx["traps"], fx["today"], fx["exam"])
    assert set(got) == set(fx["expected"])
    for tid, exp in fx["expected"].items():
        for k, v in exp.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert got[tid][k] == pytest.approx(v, abs=1e-4), (tid, k)
            else:
                assert got[tid][k] == v, (tid, k)


def test_trap_stats_empty_log_is_safe():
    fx = fixture()
    got = TS.trap_stats([], fx["items"], fx["traps"], fx["today"])
    assert all(s["n"] == 0 and s["quote"] is None and s["status"] == "zu wenig Daten" and s["gap"] == 0.0 for s in got.values())


def test_old_events_without_pick_still_count():
    fx = fixture()
    ev = [dict(e, meta={k: v for k, v in e["meta"].items() if k != "pick"}) for e in fx["events"]]
    got = TS.trap_stats(ev, fx["items"], fx["traps"], fx["today"])
    exp = fx["expected"]
    assert got["act"]["n"] == exp["act"]["n"] and got["act"]["lure_share"] is None


def test_ranked_puts_data_rich_traps_by_gap_first():
    fx = fixture()
    st = TS.trap_stats(fx["events"], fx["items"], fx["traps"], fx["today"])
    r = TS.ranked(st, fx["traps"]["taxonomy"])
    oks = [t["id"] for t in r if st[t["id"]]["status"] == "ok"]
    assert oks == sorted(oks, key=lambda i: -st[i]["gap"])
    assert [t["id"] for t in r][:len(oks)] == oks


def test_visible_items_hides_unplayed_mocks():
    items = [dict(id="a", exam="pmp"), dict(id="m", exam="pmp", mock="M1", set="M1A"), dict(id="n", exam="pmp", mock="M1", set="M1B")]
    assert [i["id"] for i in TS.visible_items(items, [])] == ["a"]
    assert [i["id"] for i in TS.visible_items(items, [dict(kind="exam", ref="XLRTE-M1A")])] == ["a", "m"]
    assert [i["id"] for i in TS.visible_items(items, [dict(kind="exam", ref="XLRTE-M1")])] == ["a", "m", "n"]


def test_profile_lines_use_cockpit_numbers():
    fx = fixture()
    st = TS.trap_stats(fx["events"], fx["items"], fx["traps"], fx["today"])
    lines = TS.profile_lines(st, fx["traps"]["taxonomy"])
    txt = "\n".join(lines)
    assert lines[0] == "### Fallen (PMP)"
    assert f"{st['act']['n']} Versuche" in txt and "zu wenig Daten" in txt


def test_profile_has_trap_section_when_pmp_is_active(monkeypatch):
    import xlrte, datetime as dt
    fx = fixture()
    monkeypatch.setattr(xlrte, "jload", lambda p, d=None: fx["traps"] if str(p).endswith("traps_pmp.json") else d)
    lines = xlrte.trap_section([dict(i) for i in fx["items"]], fx["events"], dt.date(2026, 10, 20))
    assert lines[0] == "### Fallen (PMP)" and any("Voreiliges Handeln" in l for l in lines)
    monkeypatch.setattr(xlrte, "jload", lambda p, d=None: d)
    assert xlrte.trap_section([], [], dt.date(2026, 10, 20)) == []


def test_engine_prompt_mentions_trap_numbers():
    import xlrte
    assert "Abschnitt „Fallen“" in xlrte.engine_prompt()["full"]


def _data(name):
    p = os.path.join(X, "data", name)
    if not os.path.exists(p):
        pytest.skip("data/ nicht vorhanden (Test läuft im Drive-Ordner)")
    return json.load(open(p, encoding="utf-8"))


def test_every_bank_item_has_curated_traps():
    import traps_pmp_curated_bank as cb
    ids = [i["id"] for i in _data("items_pmp.json")]
    assert sorted(cb.CURATED) == sorted(ids)
    assert all(1 <= len(v.split()) <= 2 and set(v.split()) <= set(R.IDS) for v in cb.CURATED.values())


def test_multi_and_numeric_items_carry_their_trap():
    import traps_pmp_curated_bank as cb
    for i in _data("items_pmp.json"):
        tags = cb.CURATED[i["id"]].split()
        if i["type"] == "multi":
            assert "multi" in tags, i["id"]
        if len(i["options"]) >= 3 and all(R._NUM_OPT.match(str(o).strip()) for o in i["options"]):
            assert "calc" in tags, i["id"]


def test_every_mock_item_has_curated_traps_and_valid_lures():
    import traps_pmp_curated_mock1 as cm
    items = _data("items_pmp_mock1.json")
    assert sorted(cm.CURATED) == sorted(i["id"] for i in items)
    assert all(1 <= len(v.split()) <= 2 and set(v.split()) <= set(R.IDS) for v in cm.CURATED.values())
    for i in items:
        if i["type"] == "multi":
            assert "multi" in cm.CURATED[i["id"]].split(), i["id"]
    out = B.build(items, cm.CURATED, cm.LURES)
    assert len(out["lures"]) >= 100                        # mindestens die Einzelauswahl-Fragen mit klarer Verlockung


def test_full_build_covers_all_pmp_items():
    p = os.path.join(X, "data", "traps_pmp.json")
    if not os.path.exists(p):
        pytest.skip("nicht gebaut")
    traps = json.load(open(p, encoding="utf-8"))
    ids = [i["id"] for f in ("items_pmp.json", "items_pmp_mock1.json", "items_pmp_mock2.json", "items_pmp_mock3.json", "items_pmp_sz1.json", "items_pmp_sz2.json", "items_pmp_m2b.json", "items_pmp_m2c.json") for i in _data(f)]
    ids += [c["id"] for c in _data("items_candidates.json") if str(c.get("src", "")).endswith("ethik-kodex")]      # Ethik-Fragen aus dem Kodex (Kandidaten, kuratiert)
    assert sorted(traps["items"]) == sorted(ids) and len(ids) == 813
    assert sum(1 for t in traps["items"].values() if "eth" in t) == 12
