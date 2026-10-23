import json, os, datetime as dt
import pytest
import xlrte
from conftest import X


def eco():
    return json.load(open(os.path.join(X, "data", "eco_pmp2026.json"), encoding="utf-8"))


@pytest.fixture
def frozen(monkeypatch):
    """Engine reads the frozen event copy instead of the live log (the learner keeps studying in parallel)."""
    orig = xlrte.P
    monkeypatch.setattr(xlrte, "P", lambda *a: os.path.join(X, "tests", "events_frozen.csv") if a == ("state", "events.csv") else orig(*a))


# ----------------------------------------------------------------------------- Task 1: ECO
def test_eco_has_26_tasks_and_138_enablers():
    e = eco()
    assert len(e["los"]) == 26
    assert sum(len(t["enablers"]) for t in e["los"]) == 138


def test_enabler_ids_are_task_scoped():
    for t in eco()["los"]:
        for n, en in enumerate(t["enablers"], 1):
            assert en["id"] == f"{t['id']}.{n}" and len(en["text"]) > 10


def test_eco_keeps_focus_and_has_refs():
    for t in eco()["los"]:
        assert t["focus"] and t["refs"]["rita"] and t["refs"]["pmbok8"] and t["keywords"]
        assert t["refs"]["pmbok8_ed"] and all(isinstance(x, str) and "S. " in x for x in t["refs"]["pmbok8_ed"])  # Welle 3: Buchverweise


def test_eco_weights_and_structure():
    e = eco()
    assert [c["weight"] for c in e["categories"]] == [33.0, 41.0, 26.0]
    assert len(e["pmbok8_structure"]) == 7 and len(e["rita_chapters"]) == 18


# ----------------------------------------------------------------------------- Task 2: engine
def test_itil_unchanged_against_baseline(frozen):
    base = json.load(open(os.path.join(X, "tests", "baseline_itil5.json")))
    c = xlrte.compute(dt.date(2026, 9, 26))
    assert json.loads(json.dumps({"itil5": c["itil5"], "streak": c["streak"]}, sort_keys=True)) == base


def test_legacy_glossary_defaults_to_itil5():
    _, _, _, gloss = xlrte.load_content()
    assert all(g.get("exam") in ("itil5", "pmp") for g in gloss)
    assert any(g["exam"] == "itil5" for g in gloss)


def test_keyword_index_uses_enablers_and_keywords():
    syl, e, _, gloss = xlrte.load_content()
    idx = xlrte.keyword_index(syl, e, gloss)
    assert "wbs" in idx[("pmp", "PR.2")] and "impediment" in idx[("pmp", "BE.4")]
    assert "ground" in idx[("pmp", "P.2")]                      # from enabler text only


LONGQ = " ".join(f"w{k}" for k in range(50)) + "?"      # Fragetext im Prüfungskaliber (45–60 Wörter)


def _item(**kw):
    base = {"id": "t1", "exam": "pmp", "lo": "PR.6", "q": "q?", "options": ["a", "b", "c", "d"], "answer": 1, "why": "w" * 25}
    base.update(kw)
    return base


def test_check_item_rules():
    e = xlrte.load_content()[1]
    cases = {"case_01"}
    assert xlrte.check_item(_item(type="multi", options=list("abcde"), answer=[0, 3]), e, cases) == []
    assert xlrte.check_item(_item(type="multi", answer=[0, 3]), e, cases)            # only 4 options
    assert xlrte.check_item(_item(case="nope"), e, cases)
    assert xlrte.check_item(_item(case="case_01"), e, cases) == []
    assert xlrte.check_item(_item(en="P.1.1"), e, cases)                             # enabler of other task
    assert xlrte.check_item(_item(en="PR.6.2"), e, cases) == []
    assert xlrte.check_item(_item(answer=True), e, cases)                            # bool is not an index


def test_add_candidates_rejects_list_answer_without_multi(tmp_path, monkeypatch):
    f = tmp_path / "c.json"
    f.write_text(json.dumps([_item(answer=[0, 1])]))
    monkeypatch.setattr(xlrte, "jsave", lambda *a, **k: None)
    r = xlrte.add_candidates(str(f), dt.date(2026, 10, 6))
    assert r["added"] == 0 and r["rejected"]


def test_add_candidates_keeps_pmp_fields(tmp_path, monkeypatch):
    f = tmp_path / "c.json"
    f.write_text(json.dumps([_item(q=LONGQ, type="multi", options=list("abcde"), answer=[1, 2], en="PR.6.1", appr="hybrid")]))
    saved = {}
    monkeypatch.setattr(xlrte, "jsave", lambda p, obj: saved.setdefault("obj", obj))
    r = xlrte.add_candidates(str(f), dt.date(2026, 10, 6))
    new = saved["obj"][-1]
    assert r["added"] == 1 and new["type"] == "multi" and new["en"] == "PR.6.1" and new["appr"] == "hybrid" and new["answer"] == [1, 2]


def test_briefing_pmp_uses_pmp_thresholds(tmp_path, monkeypatch, frozen):
    orig = xlrte.P
    monkeypatch.setattr(xlrte, "P", lambda *a: str(tmp_path.joinpath(*a)) if a and a[0] == "notebooklm" else orig(*a))
    b = xlrte.briefing(dt.date(2026, 10, 13))["markdown"]
    assert "/ 180" in b and "Bestehensschwelle 26" not in b and "PMI" in b and "Rita" in b
    assert list(tmp_path.joinpath("notebooklm").iterdir())                          # wrote to tmp, not live


def test_recap_day_tolerates_multi():
    items = [_item(id="m1", type="multi", options=list("abcde"), answer=[0, 2])]
    ev = [{"id": "e1", "kind": "attempt", "date": "2026-10-06", "exam": "pmp", "ref": "m1", "value": 0, "minutes": 0, "meta": {}}]
    xlrte.recap_day(dt.date(2026, 10, 6), ev, items, xlrte.load_content()[0])     # must not raise


def test_check_flags_case_without_items(monkeypatch):
    monkeypatch.setattr(xlrte, "load_cases", lambda: [{"id": "case_zz", "title": "t", "text": "x"}])
    assert any("case_zz" in e for e in xlrte.check())


# ----------------------------------------------------------------------------- Task 3: glossary
def test_pmp_glossary():
    g = json.load(open(os.path.join(X, "data", "glossary_pmp.json"), encoding="utf-8"))
    tasks = {t["id"] for t in eco()["los"]}
    assert len(g) >= 140
    assert len({x["term"].lower() for x in g}) == len(g)
    assert len({x["id"] for x in g}) == len(g)
    assert all(x["exam"] == "pmp" and x["los"] and set(x["los"]) <= tasks and len(x["definition"]) >= 25 for x in g)
    assert {lo for x in g for lo in x["los"]} == tasks            # every task has at least one card


# ----------------------------------------------------------------------------- Task 4: item bank + cases
def pmp_items():
    return json.load(open(os.path.join(X, "data", "items_pmp.json"), encoding="utf-8"))


def pmp_cases():
    return json.load(open(os.path.join(X, "data", "cases_pmp.json"), encoding="utf-8"))


def test_bank_size_distribution_and_mix():
    it = pmp_items()
    cat = {t["id"]: t["cat"] for t in eco()["los"]}
    assert len(it) >= 260
    per = {}
    for i in it:
        per[i["lo"]] = per.get(i["lo"], 0) + 1
    assert min(per.get(t, 0) for t in cat) >= 6
    share = {c: sum(1 for i in it if cat[i["lo"]] == c) / len(it) for c in ("P", "PR", "BE")}
    for c, w in (("P", .33), ("PR", .41), ("BE", .26)):
        assert abs(share[c] - w) <= .03, share
    appr = [i.get("appr") for i in it]
    assert all(a in ("predictive", "agile", "hybrid") for a in appr)
    assert .33 <= appr.count("predictive") / len(it) <= .47
    assert sum(1 for i in it if i.get("type") == "multi") >= 20
    assert all(i.get("en") for i in it[34:])


def test_answer_positions_balanced():
    std = [i["answer"] for i in pmp_items() if i.get("type") != "multi"]
    for k in range(4):
        assert std.count(k) / len(std) <= .35, [std.count(j) for j in range(4)]


def test_legacy_ids_unchanged():
    old = json.load(open(os.path.join(X, "_backup", "2026-09-26b", "items_pmp.json"), encoding="utf-8"))
    new = {i["id"]: i for i in pmp_items()}
    for o in old:
        n = new[o["id"]]
        assert (n["lo"], n["q"], n["options"], n["answer"]) == (o["lo"], o["q"], o["options"], o["answer"])


def test_cases_and_items_valid():
    cases = pmp_cases()
    ids = {c["id"] for c in cases}
    e = eco()
    assert len(cases) >= 10
    items = pmp_items()
    assert len({i["id"] for i in items}) == len(items)
    assert len({i["q"] for i in items}) == len(items)
    for i in items:
        assert xlrte.check_item(i, e, ids) == [], i["id"]
    for c in ids:
        assert sum(1 for i in items if i.get("case") == c) >= 3


# ----------------------------------------------------------------------------- Task 6: day plan + config
def test_pmp_day_plan_complete():
    c = json.load(open(os.path.join(X, "config.json"), encoding="utf-8"))
    tasks = {t["id"] for t in eco()["los"]}
    d = dt.date(2026, 10, 5)
    while d <= dt.date(2026, 11, 13):                                      # Prüfung 12.11. (Plan seit 08.10. verdichtet)
        if d.weekday() < 5:
            p = c["day_plan"][d.isoformat()]
            assert p["title"] and p["tasks"] and set(p.get("focus_los", [])) <= tasks, d
        d += dt.timedelta(days=1)
    assert "2026-09-24" in c["day_plan"]                                   # ITIL untouched
    ex = c["exams"]["pmp"]
    assert (ex["target_date"], ex["sim_minutes"], ex["mini_questions"], ex["mini_minutes"]) == ("2026-11-26", 240, 60, 80)
    txt = json.dumps(c["day_plan"], ensure_ascii=False)
    for kw in ("35 Contact Hours", "PMI-Antrag", "Pearson VUE", "Mock 1 · Teil A", "Mock 1 · Teil B", "Mock 1 · Teil C", "Vollmock 2", "Study Hall"):
        assert kw in txt, kw
    covered = {lo for k, p in c["day_plan"].items() if k >= "2026-10-05" for lo in p.get("focus_los", [])}
    assert covered == tasks                                                # every ECO task gets focus days


def test_plan_pmp_is_idempotent(tmp_path, monkeypatch):
    """Runs against a copy — the test must never write the live config.json."""
    import shutil, plan_pmp
    cfg = tmp_path / "config.json"
    shutil.copy(os.path.join(X, "config.json"), cfg)
    monkeypatch.setattr(plan_pmp, "CFG", str(cfg))
    plan_pmp.build()
    once = cfg.read_text(encoding="utf-8")
    plan_pmp.build()
    assert cfg.read_text(encoding="utf-8") == once
    live = json.load(open(os.path.join(X, "config.json"), encoding="utf-8"))
    assert json.loads(once)["day_plan"] == live["day_plan"]


# ----------------------------------------------------------------------------- Task 7: inbox mapping (EN course material)
def test_rita_excerpts_map_to_tasks():
    """Spec §1.6: ≥ 80 % of English course pages map deterministically to a fitting task.
    30 samples = 3 pages in each of Rita ch. 6–15; 'fitting' = a task whose refs.rita cite that chapter."""
    import subprocess, glob
    rita = glob.glob(os.path.join(X, "..", "PMP", "*Rita-Mulcahy*.pdf"))[0]
    e = eco()
    syl, _, _, gloss = xlrte.load_content()
    idx = {k: v for k, v in xlrte.keyword_index(syl, e, gloss).items() if k[0] == "pmp"}
    chap = {c["ch"]: c for c in e["rita_chapters"]}
    hits, miss = 0, []
    for ch in range(6, 16):
        want = {t["id"] for t in e["los"] if any(r["ch"] == ch for r in t["refs"]["rita"])}
        for off in (3, 9, 12):
            pg = chap[ch]["pdf_page"] + off
            txt = subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg + 1), rita, "-"], capture_output=True, text=True).stdout
            top = xlrte.score_chunk(txt, idx)[0][1][1]
            hits += top in want
            if top not in want:
                miss.append((ch, off, top))
    assert hits >= 24, (hits, miss)


# ----------------------------------------------------------------------------- final review fixes
def test_keyword_index_keeps_pmp_glossary_terms():
    syl, e, _, gloss = xlrte.load_content()
    idx = xlrte.keyword_index(syl, e, gloss)
    assert "resource smoothing" in idx[("pmp", "PR.4")]
    assert "privity of contract" in idx[("pmp", "PR.5")]


def test_item_ids_are_module_scoped_and_frozen():
    """Appending to one bank module must never renumber another module (events reference ids)."""
    import re, hashlib
    it = pmp_items()
    assert all(re.fullmatch(r"pm_(\d{3}|[prbc]\d{3})", i["id"]) for i in it)
    assert all(re.fullmatch(r"pm_[prbc]\d{3}", i["id"]) for i in it[34:])
    snap = json.load(open(os.path.join(X, "tests", "bank_ids.json"), encoding="utf-8"))
    cur = {i["id"]: hashlib.sha1(i["q"].encode()).hexdigest()[:12] for i in it}
    changed = [k for k, h in snap.items() if cur.get(k) != h]
    assert not changed, changed


def test_correct_option_is_not_a_length_tell():
    """Review finding: the key must not be recognisable as 'the longest option'."""
    std = [i for i in pmp_items() if i.get("type") != "multi"]
    def longest(i):
        L = [len(o) for o in i["options"]]
        return all(L[i["answer"]] > l for k, l in enumerate(L) if k != i["answer"])
    share = sum(map(longest, std)) / len(std)
    assert share <= .35, round(share, 2)


# ----------------------------------------------------------------------------- review minors before course start
def test_add_candidates_derives_exam_and_requires_pmp_fields(tmp_path, monkeypatch):
    saved = {}
    monkeypatch.setattr(xlrte, "jsave", lambda p, obj: saved.setdefault("obj", obj))
    base = {"lo": "PR.6", "q": LONGQ, "options": ["a", "b", "c", "d"], "answer": 1, "why": "w" * 25}
    f = tmp_path / "c.json"
    f.write_text(json.dumps([dict(base), dict(base, q=LONGQ + " two", en="PR.6.1", appr="hybrid")]))
    r = xlrte.add_candidates(str(f), dt.date(2026, 10, 6))
    assert r["added"] == 1 and r["rejected"][0]["i"] == 0                      # missing en/appr rejected
    assert saved["obj"][-1]["exam"] == "pmp"                                   # derived from lo


def test_recap_day_names_pmp_tasks():
    items = [{"id": "m1", "exam": "pmp", "lo": "PR.6", "options": ["a"] * 4, "answer": 0}]
    ev = [{"id": "e1", "kind": "attempt", "date": "2026-10-06", "exam": "pmp", "ref": "m1", "value": 0, "minutes": 0, "meta": {}}]
    txt = xlrte.recap_day(dt.date(2026, 10, 6), ev, items, xlrte.load_content()[0])
    assert "Plan and manage finance" in txt and "Rita Kap. 9" in txt and "Buch §)" not in txt


# ----------------------------------------------------------------------------- learning engine profile (Gemini Notebook)
def test_learner_profile_is_evidence_based(frozen):
    comp = xlrte.compute(dt.date(2026, 9, 26))
    md = xlrte.learner_profile(dt.date(2026, 9, 26), comp)
    rd = comp["itil5"]["readiness"]
    assert "XLRTE Lernprofil" in md and "ITIL 5 Foundation" in md
    assert f"SVH (Service Value Health): {round(rd['pct'])} %" in md            # = forecast share, not invented
    for key in ("Kalibrierung", "Cognitive Velocity", "Cognitive Debt", "Bloom", "Next Incident", "Bereits behandelt"):
        assert key in md, key
    assert any(w["id"] in md for w in comp["itil5"]["weak"])


def test_learner_profile_switches_to_pmp(frozen):
    d = dt.date(2026, 10, 13)
    md = xlrte.learner_profile(d, xlrte.compute(d))
    assert "PMP" in md and "Rita" in md and "englisch" in md.lower()


def test_lernjournal_starts_with_profile(tmp_path, monkeypatch, frozen):
    orig = xlrte.P
    monkeypatch.setattr(xlrte, "P", lambda *a: str(tmp_path.joinpath(*a)) if a and a[0] == "notebooklm" else orig(*a))
    (tmp_path / "notebooklm").mkdir()
    xlrte.update_lernjournal(dt.date(2026, 9, 26))
    txt = (tmp_path / "notebooklm" / "XLRTE_Lernjournal.md").read_text(encoding="utf-8")
    first_day = txt.find("\n## 2026-")
    assert 0 <= txt.index("XLRTE Lernprofil") < (first_day if first_day > 0 else len(txt))   # profile before the day entries
    assert (tmp_path / "notebooklm" / "XLRTE_Lernprofil.md").exists()


def test_learner_profile_maps_topic_ids_and_thin_evidence(frozen):
    md = xlrte.learner_profile(dt.date(2026, 9, 27))
    covered = md.split("Bereits behandelt")[1].split("\n")[0]
    assert "1.1" in covered and "3.2" in covered and "44 Lernziele" in covered and "1.1.1" not in covered   # topics, compact
    assert "vs. davor 0" not in md
    assert "Begriffe festigen (BL1)" not in md.split("6 ITIL und KI")[1].split("\n")[0]


def test_engine_prompt_is_parsed_for_the_cockpit():
    ep = xlrte.engine_prompt()
    assert "SERVICE VALUE LEDGER" in ep["full"] and "/bridge" in ep["full"] and "wörtlich aus dem neuesten Lernprofil" in ep["full"]
    assert 0 < len(ep["short"]) < 800 and "Einmalig einrichten" not in ep["full"]


def test_candidate_keys_accepts_score_chunk_triples():
    sc = [(3.0, ("pmp", "PR.1"), 4), (2.0, ("itil5", "1.1"), 2), (1.0, ("pmp", "P.2"), 1)]
    assert xlrte.candidate_keys(sc, 2) == [("pmp", "PR.1"), ("itil5", "1.1")]


def test_render_always_embeds_the_briefing(tmp_path, monkeypatch):
    """Regression 08.10.: `xlrte.py render` allein hat das Briefing leer ins Cockpit geschrieben (Gemini-Notebook-Ansicht: 'Briefing nicht verfügbar')."""
    import xlrte
    if not os.path.exists(os.path.join(X, "templates", "cockpit.html")):
        pytest.skip("Templates nicht vorhanden")
    monkeypatch.setattr(xlrte, "OUTDIR", str(tmp_path))
    monkeypatch.setattr(xlrte, "briefing", lambda today, comp=None: {"markdown": "# Briefing Test", "date": today.isoformat()})
    out, _ = xlrte.render(dt.date(2026, 10, 8))
    html = open(out, encoding="utf-8").read()
    assert "# Briefing Test" in html


@pytest.mark.skipif(not hasattr(__import__("time"), "tzset"), reason="time.tzset fehlt unter Windows")
def test_engine_time_is_learner_time_not_process_time(monkeypatch):
    """Regression 08.10.: die Routine lief mit UTC, Zeitstempel und Datum wichen von Berlin ab."""
    import time
    monkeypatch.setenv("TZ", "UTC"); time.tzset()
    try:
        n = xlrte.now_local()
        import datetime
        utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        off = (n - utc).total_seconds() / 3600
        assert round(off) in (1, 2), off                                   # MEZ oder MESZ
        assert xlrte._berlin_offset_hours(datetime.datetime(2026, 10, 8, 12)) == 2
        assert xlrte._berlin_offset_hours(datetime.datetime(2026, 12, 1, 12)) == 1
        assert xlrte._berlin_offset_hours(datetime.datetime(2026, 3, 29, 0, 59)) == 1 and xlrte._berlin_offset_hours(datetime.datetime(2026, 3, 29, 1, 0)) == 2
    finally:
        monkeypatch.delenv("TZ"); time.tzset()


def test_stem_length_guard_rejects_short_and_overlong_daily_questions(tmp_path, monkeypatch):
    monkeypatch.setattr(xlrte, "jsave", lambda p, obj: None)
    f = tmp_path / "c.json"
    ok = _item(q=LONGQ, en="PR.6.1", appr="hybrid")
    del ok["id"], ok["exam"]
    f.write_text(json.dumps([dict(ok), dict(ok, q="What now?"), dict(ok, q=LONGQ + " " + " ".join(["x"] * 80))]))
    r = xlrte.add_candidates(str(f), dt.date(2026, 10, 9))
    assert r["added"] == 1 and [x["i"] for x in r["rejected"]] == [1, 2]
    assert all("Prüfungskaliber" in " ".join(x["errors"]) for x in r["rejected"])


def test_gen_targets_carry_stem_length():
    import gen_pmp
    eco = xlrte.load_content()[1]
    t = gen_pmp.targets([{"id": "PR.6", "m": .3, "gap_points": 3}], [], eco, [], limit=2)
    assert t and all(x["stem_words"] == [45, 60] for x in t)
