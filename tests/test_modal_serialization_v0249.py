"""Pinned-SDK serialization regression; no hydration, app run, network or GPU."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SDK_AVAILABLE = importlib.util.find_spec('modal') is not None


@unittest.skipUnless(SDK_AVAILABLE, 'SDK regression runs in dedicated pinned-Modal CI step')
class ModalSerializationTests(unittest.TestCase):
    def test_controller_worker_and_cleanup_serialize_without_hydration(self):
        from modal._serialization import serialize
        import modal
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
        import study_d_modal_app_v0249 as declarations
        import formation_study_d_modal_delete_v0249 as cleanup
        with patch.object(modal.client._Client, 'from_env', side_effect=AssertionError('no client/hydration allowed')):
            for stage in ('base', 'study'):
                app, _ = declarations.define(stage)
                functions = list(app.registered_functions.values())
                self.assertEqual(len(functions), 2)
                for function in functions:
                    # Actual Modal serializer, not cloudpickle alone. The SDK
                    # rejects captured unhydrated handles via persistent_id.
                    self.assertGreater(len(serialize(function._raw_f_)), 100)
            self.assertGreater(len(serialize(cleanup.delete_after_review._raw_f_)), 100)

    def test_serializer_rejects_original_unhydrated_dict_capture(self):
        import modal
        from modal._serialization import serialize
        ledger = modal.Dict.from_name('taa-study-d-v0249-budget-once')
        def original_failure():
            return ledger.contains('stage-once/base')
        with self.assertRaisesRegex(modal.exception.InvalidError, "hasn't been hydrated"):
            serialize(original_failure)
