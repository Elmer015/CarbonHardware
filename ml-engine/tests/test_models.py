import os
import unittest
from pathlib import Path

import pandas as pd

MODELS = Path(__file__).resolve().parents[1] / "models"
import sys

sys.path.insert(0, str(MODELS))

from predict import load_model, predict_frame


class ModelArtifactTests(unittest.TestCase):
    """Run only when an approved Phase 4 artifact is supplied explicitly."""

    @classmethod
    def setUpClass(cls):
        model_path = os.environ.get("CARBONHARDWARE_MODEL_PATH")
        input_path = os.environ.get("CARBONHARDWARE_PREDICTION_INPUT")
        if not model_path or not input_path:
            raise unittest.SkipTest(
                "Set CARBONHARDWARE_MODEL_PATH and CARBONHARDWARE_PREDICTION_INPUT "
                "after a valid Phase 4 model has been trained"
            )
        cls.artifact = load_model(Path(model_path))
        cls.frame = pd.read_csv(input_path)

    def test_saved_model_loads_with_metadata_contract(self):
        self.assertTrue(self.artifact["feature_columns"])
        self.assertTrue(self.artifact["target"]["unit"])

    def test_saved_model_predicts_from_required_features(self):
        predictions = predict_frame(self.artifact, self.frame)
        self.assertEqual(len(predictions), len(self.frame))
        self.assertTrue((predictions == predictions).all())


if __name__ == "__main__":
    unittest.main()
