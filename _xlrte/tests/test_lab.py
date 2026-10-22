"""Lab (Prototyp): Sokratischer Tutor + Propositions-Tabelle. Modellfrei und deterministisch."""
import json
import pytest
import lab as b

TABLE = """| X | Beziehung | Y |
|---|---|---|
| AI-Tutor | ist ein Typ von | Einsatzart von KI |
| Halluzination | wird verursacht durch | Wahrscheinlichkeitsvorhersage |
| Coach-Rolle | erklärt | Metakognition |
"""


def test_tutor_prompt_forbids_answer_first_and_contains_topic_and_level():
    p = b.tutor_prompt("Earned Value", level="highschool")
    assert "Earned Value" in p and "Oberstufe" in p
    assert "keine Antwort" in p and "zuerst" in p
    assert "nicht erfunden" in p or "nicht erfinden" in p


def test_tutor_prompt_with_source_restricts_to_source():
    p = b.tutor_prompt("EV", source="EV ist der Wert der geleisteten Arbeit.")
    assert "NUR" in p and "EV ist der Wert der geleisteten Arbeit." in p


def test_tutor_prompt_rejects_unknown_level():
    with pytest.raises(ValueError):
        b.tutor_prompt("EV", level="phd")


def test_multilevel_prompt_has_three_levels_in_order():
    p = b.multilevel_prompt("Risiko")
    assert p.index("Kind") < p.index("Oberstufe") < p.index("akademisch")


def test_propositions_prompt_names_three_forms_and_caps_input():
    p = b.propositions_prompt("a" * 20000)
    for form in ("ist ein Typ von", "wird verursacht durch", "erklärt"):
        assert form in p
    assert len(p) < b.MAX_TEXT + 2000


def test_parse_table_returns_triples_and_skips_header():
    rows, problems = b.parse_table(TABLE)
    assert rows == [("AI-Tutor", "ist ein Typ von", "Einsatzart von KI"),
                    ("Halluzination", "wird verursacht durch", "Wahrscheinlichkeitsvorhersage"),
                    ("Coach-Rolle", "erklärt", "Metakognition")]
    assert problems == []


def test_parse_table_flags_unknown_relation_and_empty_cells():
    rows, problems = b.parse_table("| a | liegt neben | b |\n| c | erklärt |  |\n")
    assert rows == []
    assert len(problems) == 2


def test_parse_table_ignores_duplicates():
    rows, _ = b.parse_table(TABLE + "| AI-Tutor | ist ein Typ von | Einsatzart von KI |\n")
    assert len(rows) == 3


def test_cards_are_cloze_style_and_tagged_lab():
    rows, _ = b.parse_table(TABLE)
    cards = b.to_cards(rows, topic="KI")
    assert len(cards) == 3
    c = cards[0]
    assert c["set"] == "lab" and c["topic"] == "KI"
    assert "ist ein Typ von" in c["front"] and "Einsatzart von KI" not in c["front"]
    assert c["back"] == "Einsatzart von KI"
    assert len({k["id"] for k in cards}) == 3


def test_cards_ids_are_stable():
    rows, _ = b.parse_table(TABLE)
    assert [c["id"] for c in b.to_cards(rows)] == [c["id"] for c in b.to_cards(rows)]


def test_cli_cards_writes_json(tmp_path, capsys):
    f = tmp_path / "t.md"
    f.write_text(TABLE, encoding="utf-8")
    out = tmp_path / "cards.json"
    assert b.main(["cards", str(f), "--topic", "KI", "--out", str(out)]) == 0
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 3


# --- focus: Schwachstellen-Fokus-Paket -------------------------------------------------------
def cand(i, m=0.3, n=3.0, gap=1.0, sw=0, **kw):
    return dict(id=i, text="Thema " + i, m=m, n=n, gap=gap, sure_wrong=sw,
                refs={"rita": [{"ch": 5, "title": "Leadership Skills", "pages": "105–124"}], "pmbok8": ["1.1 Initiate Project or Phase"]}, **kw)


def test_sure_wrong_comes_first_and_uses_tutor():
    es = b.pick([cand("A", gap=5), cand("B", gap=1, sw=2)], n=2)
    assert es[0]["id"] == "B" and es[0]["mode"] == "tutor"
    assert "sicher" in es[0]["why"]


def test_no_evidence_uses_multilevel_and_evidence_uses_props():
    es = {e["id"]: e for e in b.pick([cand("N", n=0.4), cand("E", n=4.0)], n=2)}
    assert es["N"]["mode"] == "multilevel" and "Evidenz" in es["N"]["why"]
    assert es["E"]["mode"] == "tutor" and "trotz Evidenz" in es["E"]["why"]


def test_props_is_never_chosen_automatically():
    es = b.pick([cand(str(k), n=k, sw=k % 2) for k in range(6)], n=6)
    assert "props" not in {e["mode"] for e in es}


def test_tutor_prompt_ends_with_exam_style_scenario_questions():
    p = b.tutor_prompt("EV")
    assert "Szenariofragen" in p and "vier Optionen" in p


def test_strong_los_are_excluded_and_n_is_capped():
    es = b.pick([cand("S", m=0.9)] + [cand(str(k), gap=k) for k in range(8)], n=4)
    assert len(es) == 4 and "S" not in [e["id"] for e in es]
    assert es[0]["id"] == "7"


def test_pick_is_deterministic_on_ties():
    c = [cand("B"), cand("A")]
    assert [e["id"] for e in b.pick(c, 2)] == [e["id"] for e in b.pick(list(reversed(c)), 2)]


def test_render_focus_is_pasteable_and_has_sources_but_no_book_text():
    md = b.render_focus(b.pick([cand("P.1", sw=1)], 1), "2026-10-16")
    assert md.startswith("### Lab-Fokus")
    assert "P.1" in md and "Sokratischen Tutor" in md
    assert "Rita Kap. 5" in md and "PMBOK 8 1.1 Initiate Project or Phase" in md
    assert "Basis-Prompt" in md


def test_render_focus_empty_says_so():
    assert "keine" in b.render_focus([], "2026-10-16").lower()


def test_basis_prompts_have_placeholders():
    t = b.basis_prompts()
    assert t.count("{THEMA}") >= 3 and "Sokratischer Tutor" in t and "Propositionen" in t
