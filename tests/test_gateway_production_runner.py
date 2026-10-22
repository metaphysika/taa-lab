"""Same runner/observer, actual native mutations, explicit partial coverage."""
import unittest
from unittest.mock import patch

from tests.trace_support import production_backend as backend
from tests.trace_support import reference_runner as runner
from tests.trace_support import regressions
from tests.trace_support.bundle import cases


class ProductionRunnerTests(unittest.TestCase):
    def test_real_rollback_trace_runs_through_common_observer(self):
        case = next(c for c in cases() if c["id"] == "T23[during_revision_advance]")
        rows = runner.run(case, backend=backend)
        self.assertFalse([row for row in rows if row["status"] == "discrepancy"])
        incomplete = [row for row in rows if row["status"] == "incomplete"]
        self.assertEqual(incomplete, [])
        self.assertTrue(any(row["origin"] == "state-audit" and row["assertion"].endswith("state_delta") for row in rows))

    def test_all_three_hidden_native_mutations_trigger_state_audit_discrepancies(self):
        import json
        controls = json.loads((regressions.ROOT / "mutations.json").read_text())
        for case in regressions.cases():
            if case["id"] not in controls:
                continue
            spec = controls[case["id"]]
            with self.subTest(trace=case["id"]):
                with patch.object(backend, spec["method"], regressions.mutated(getattr(backend, spec["method"]), spec["mutation"], backend)):
                    rows = runner.run(case, backend=backend)
                self.assertTrue([row for row in rows if row["origin"] == "state-audit" and row["status"] == "discrepancy"])
                self.assertFalse([row for row in rows if row["origin"] == "state-audit" and row["status"] == "incomplete"])

    def test_independent_duty_engine_finishes_the_no_proposal_trace(self):
        case = next(c for c in cases() if c["id"] == "T27")
        rows = runner.run(case, backend=backend)
        source = [row for row in rows if row["origin"] == "source"]
        self.assertTrue(source)
        self.assertTrue(all(row["status"] == "pass" for row in rows))

    def test_reviewer_rejection_reason_comes_from_actual_audit_entry(self):
        case = next(c for c in cases() if c["id"] == "T33")
        rows = runner.run(case, backend=backend)
        reason = next(row for row in rows if row["assertion"] == "steps[1]@3.reason")
        self.assertEqual(reason["status"], "pass")
        self.assertEqual(reason["observed"], "no substantive basis or bound evidence")


if __name__ == "__main__":
    unittest.main()
