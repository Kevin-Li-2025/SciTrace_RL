from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scitrace_rl.chemistry import formula_stats
from scitrace_rl.eval_suite import run_eval_suite
from scitrace_rl.utils import read_json
from scitrace_rl.runner import run_task


ROOT = Path(__file__).resolve().parents[1]


class ChemistryTests(unittest.TestCase):
    def test_formula_stats_handles_fluorinated_additive(self) -> None:
        stats = formula_stats("C3H3FO3")
        self.assertEqual(stats.atoms["F"], 1)
        self.assertAlmostEqual(stats.molecular_weight, 106.052, places=3)


class RunnerTests(unittest.TestCase):
    def test_demo_run_produces_passed_validations_and_reward_sample(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            trace = run_task(
                ROOT / "data/tasks/electrolyte_additive_screen.json",
                ROOT / "data/corpus/scientific_sources.json",
                out,
            )
            self.assertEqual(trace["metrics"]["total_tool_calls"], 3)
            self.assertGreaterEqual(trace["reward"]["reward"], 0.9)
            self.assertTrue((out / "demo_trace.json").exists())
            self.assertTrue((out / "trace_to_reward_sample.json").exists())
            self.assertTrue((out / "provenance_bundle.json").exists())
            self.assertTrue((out / "post_training_bundle.json").exists())
            provenance = read_json(out / "provenance_bundle.json")
            self.assertEqual(provenance["trace_id"], trace["trace_id"])
            self.assertIn("ro_crate", provenance)
            self.assertIn("prov", provenance)
            self.assertIn("otel", provenance)
            self.assertGreaterEqual(len(provenance["otel"]["spans"]), 1 + trace["metrics"]["total_tool_calls"])
            post_training = read_json(out / "post_training_bundle.json")
            self.assertIn("sft_chat_record", post_training["formats"])
            self.assertIn("dpo_preference_pair", post_training["formats"])
            self.assertEqual(len(post_training["process_reward_steps"]), trace["metrics"]["total_tool_calls"])
            self.assertEqual(len(post_training["tool_router_records"]), trace["metrics"]["total_tool_calls"])
            required = {
                "citation_integrity",
                "artifact_replay",
                "constraint_satisfaction",
                "claim_evidence_alignment",
                "claim_metadata_completeness",
            }
            validation_by_name = {item["name"]: item for item in trace["validations"]}
            self.assertTrue(all(validation_by_name[name]["status"] == "pass" for name in required))
            self.assertEqual(validation_by_name["ai_claim_review"]["status"], "skip")

    def test_eval_suite_exercises_negative_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_eval_suite(
                ROOT / "data/tasks/electrolyte_additive_screen.json",
                ROOT / "data/corpus/scientific_sources.json",
                Path(temp_dir),
            )
            self.assertEqual(summary["num_cases"], 15)
            by_case = {item["case_id"]: item for item in summary["results"]}
            fabricated = by_case["fabricated_citation"]["validations"][0]
            self.assertEqual(fabricated["name"], "citation_integrity")
            self.assertEqual(fabricated["status"], "fail")
            self.assertEqual(summary["metrics"]["deterministic_detection_rate"], 1.0)
            self.assertLess(summary["metrics"]["auto_resolvable_coverage"], 1.0)
            self.assertGreater(summary["metrics"]["expert_required_case_share"], 0.0)


if __name__ == "__main__":
    unittest.main()
