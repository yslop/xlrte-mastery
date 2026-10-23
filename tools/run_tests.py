#!/usr/bin/env python3
"""Run the same checks as the release export: build the packs (if any), then the test suite. Used by CI and by you.

    python3 tools/run_tests.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
MKDIRS = ["_xlrte/data"]
STEPS = [
 [
  "python3",
  "_xlrte/scripts/build_pack_pmp.py"
 ],
 [
  "python3",
  "_xlrte/scripts/build_pack_itil5.py"
 ],
 [
  "python3",
  "_xlrte/scripts/bank_itil5_s4_src.py"
 ],
 [
  "python3",
  "_xlrte/scripts/bank_itil5_s3_src.py"
 ],
 [
  "python3",
  "_xlrte/scripts/bank_itil5.py"
 ],
 [
  "python3",
  "_xlrte/scripts/bank_pmp.py"
 ],
 [
  "python3",
  "_xlrte/scripts/bank_pmp_mock1.py"
 ],
 [
  "python3",
  "_xlrte/scripts/bank_pmp_mock2.py"
 ],
 [
  "python3",
  "_xlrte/scripts/glossary_pmp.py"
 ],
 [
  "python3",
  "_xlrte/scripts/build_traps.py"
 ],
 [
  "python3",
  "-m",
  "pytest",
  "-q",
  "-p",
  "no:cacheprovider",
  "_xlrte/tests",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_eco_has_26_tasks_and_138_enablers",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_enabler_ids_are_task_scoped",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_eco_keeps_focus_and_has_refs",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_eco_weights_and_structure",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_itil_unchanged_against_baseline",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_legacy_glossary_defaults_to_itil5",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_keyword_index_uses_enablers_and_keywords",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_check_item_rules",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_add_candidates_rejects_list_answer_without_multi",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_add_candidates_keeps_pmp_fields",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_briefing_pmp_uses_pmp_thresholds",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_pmp_glossary",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_bank_size_distribution_and_mix",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_legacy_ids_unchanged",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_cases_and_items_valid",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_pmp_day_plan_complete",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_plan_pmp_is_idempotent",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_rita_excerpts_map_to_tasks",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_add_candidates_derives_exam_and_requires_pmp_fields",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_recap_day_names_pmp_tasks",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_learner_profile_is_evidence_based",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_learner_profile_switches_to_pmp",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_lernjournal_starts_with_profile",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_learner_profile_maps_topic_ids_and_thin_evidence",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_render_always_embeds_the_briefing",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_stem_length_guard_rejects_short_and_overlong_daily_questions",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_gen_targets_carry_stem_length",
  "--deselect",
  "_xlrte/tests/test_pmp_mock.py::test_eco_task_ids_exist",
  "--deselect",
  "_xlrte/tests/test_pmp.py::test_engine_prompt_is_parsed_for_the_cockpit",
  "--deselect",
  "_xlrte/tests/test_traps.py::test_engine_prompt_mentions_trap_numbers"
 ]
]


def main():
    for stream in (sys.stdout, sys.stderr):                         # Windows consoles default to cp1252
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    for d in MKDIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    for argv in STEPS:
        argv = [sys.executable if a == "python3" else a for a in argv]
        print("$", " ".join(argv[:6]) + (" …" if len(argv) > 6 else ""), flush=True)
        proc = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ENV)
        out = proc.stdout.decode("utf-8", "replace")
        print(out, flush=True)
        if proc.returncode != 0:
            if os.environ.get("GITHUB_ACTIONS"):                       # show the failure in the PR, not only in the raw log
                tail = "\n".join(out.strip().splitlines()[-60:])
                tail = tail.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
                print("::error title=%s::%s" % (" ".join(argv[1:4]).replace(":", " "), tail), flush=True)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
