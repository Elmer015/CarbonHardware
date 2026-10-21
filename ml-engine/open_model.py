from __future__ import annotations

import json
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "artifacts" / "embodied_carbon_model.joblib"
METADATA_PATH = ROOT / "artifacts" / "embodied_carbon_model.json"


def load_metadata():
    if not METADATA_PATH.exists():
        print(f"Metadata tidak ditemukan: {METADATA_PATH}")
        return None

    with METADATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def print_metadata():
    data = load_metadata()
    if not data:
        return

    print("=== Metadata model ===")
    print(f"model_type: {data.get('model_type')}")
    print(f"source: {data.get('source')}")
    print(f"group_column: {data.get('group_column')}")
    target = data.get("target", {})
    print(f"target_column: {target.get('column')}")
    print(f"target_unit: {target.get('unit')}")
    print(f"target_definition: {target.get('definition')}")
    print()


def extract_predictable_model(obj):
    if hasattr(obj, "predict"):
        return obj

    if isinstance(obj, dict):
        for key in [
            "model",
            "trained_model",
            "estimator",
            "clf",
            "regressor",
            "random_forest",
            "model_object",
        ]:
            value = obj.get(key)
            if hasattr(value, "predict"):
                return value

    return None


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model tidak ditemukan di: {MODEL_PATH}")

    raw_obj = joblib.load(MODEL_PATH)
    model = extract_predictable_model(raw_obj)

    print("=== Informasi model ===")
    print(f"Tipe objek yang dibaca: {type(raw_obj)}")
    print(f"Kelas objek: {raw_obj.__class__}")

    if model is None:
        print("Status: file joblib ini berisi metadata/dictionary, bukan model sklearn yang siap dipakai.")
        print("Jadi, file ini tidak dapat langsung dipanggil dengan predict().")
        print(f"Lokasi file: {MODEL_PATH}")
        print()
        return None

    print(f"Tipe model: {type(model)}")
    print(f"Kelas model: {model.__class__}")

    if hasattr(model, "get_params"):
        print(f"Parameter: {model.get_params()}")

    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is not None:
        print(f"Feature names: {list(feature_names)}")

    feature_importance = getattr(model, "feature_importances_", None)
    if feature_importance is not None:
        print(f"Feature importance: {feature_importance}")

    print(f"Lokasi file: {MODEL_PATH}")
    print()
    return model


def print_example_prediction():
    model = load_model()
    if model is None:
        print("=== Contoh prediksi ===")
        print("Tidak ada model sklearn yang bisa diprediksi dari file joblib ini.")
        return

    try:
        import pandas as pd
    except ImportError:
        print("Pandas belum terinstall. Untuk prediksi, install dulu: pip install pandas")
        return

    sample = pd.DataFrame([
        {
            "Process Size (nm)": 14,
            "TDP (W)": 180,
            "DieSizeValue": 400,
            "#dies": 1,
            "Avg Die Area": 200,
        }
    ])

    print("=== Contoh prediksi ===")
    print(model.predict(sample))


if __name__ == "__main__":
    print_metadata()
    model = load_model()
    print_example_prediction() if model is not None else None
    if model is not None:
        print("File model berhasil dibuka dan siap dipakai.")
    else:
        print("File joblib saat ini berisi metadata, bukan model yang bisa diprediksi secara langsung.")
