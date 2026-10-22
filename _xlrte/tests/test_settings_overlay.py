"""Cockpit settings (exam target date, booked) must reach the Python side the same way examCfg() applies them in the cockpit."""
import pytest
import xlrte


def ev(ref, value, i):
    return {"id": f"s{i}", "kind": "setting", "exam": "pmp", "ref": ref, "value": value, "date": "2026-10-04"}


CONFIG = {"exams": {"pmp": {"name": "PMP", "target_date": "2026-11-26", "booked": False},
                    "itil5": {"name": "ITIL", "target_date": "2026-10-03", "booked": True}}}


@pytest.fixture
def base(monkeypatch):
    monkeypatch.setattr(xlrte, "jload", lambda p, d=None: {"exams": {k: dict(v) for k, v in CONFIG["exams"].items()}})
    return monkeypatch


@pytest.mark.parametrize("raw,expected", [("True", True), ("true", True), (1, True), ("1", True), ("False", False), ("false", False), (0, False)])
def test_booked_setting_overrides_config_in_any_spelling(base, raw, expected):
    base.setattr(xlrte, "read_events", lambda include_void=False: [ev("pmp.booked", raw, 1)])
    assert xlrte.cfg()["exams"]["pmp"]["booked"] is expected


def test_target_date_and_last_setting_wins(base):
    base.setattr(xlrte, "read_events", lambda include_void=False: [ev("pmp.target_date", "2026-11-06", 1), ev("pmp.target_date", "2026-11-12", 2), ev("pmp.booked", "True", 3)])
    pm = xlrte.cfg()["exams"]["pmp"]
    assert pm["target_date"] == "2026-11-12" and pm["booked"] is True
    assert xlrte.cfg()["exams"]["itil5"]["booked"] is True          # other exams untouched


def test_no_settings_leaves_config_unchanged(base):
    base.setattr(xlrte, "read_events", lambda include_void=False: [])
    assert xlrte.cfg()["exams"]["pmp"] == CONFIG["exams"]["pmp"]


def test_empty_target_date_setting_is_ignored(base):
    base.setattr(xlrte, "read_events", lambda include_void=False: [ev("pmp.target_date", "", 1)])
    assert xlrte.cfg()["exams"]["pmp"]["target_date"] == "2026-11-26"
