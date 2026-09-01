"""
Trains the disease-prediction model used by the AI symptom-checker.

Run once (or whenever the dataset changes):
    python ai_module/train_model.py

It fits a Random Forest classifier on the binary symptom matrix in
dataset/symptoms_dataset.csv and pickles the model + label encoder +
feature/specialist lookup tables into ai_module/model/.
"""
import os
import json
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "symptoms_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "model")


def train():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = pd.read_csv(DATASET_PATH)

    symptom_columns = [c for c in df.columns if c not in ("disease", "specialist")]
    X = df[symptom_columns]
    y_disease = df["disease"]

    # Map each disease -> recommended specialist (used at prediction time)
    disease_to_specialist = (
        df.drop_duplicates("disease").set_index("disease")["specialist"].to_dict()
    )

    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y_disease)

    # Small dataset -> keep a modest test split just to report a sanity-check accuracy
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=None
    )

    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    if len(X_test) > 0:
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"Validation accuracy on hold-out split: {acc:.2f}")

    # Refit on the full dataset before shipping, since the dataset is intentionally small
    model.fit(X, y_encoded)

    joblib.dump(model, os.path.join(MODEL_DIR, "disease_model.pkl"))
    joblib.dump(encoder, os.path.join(MODEL_DIR, "label_encoder.pkl"))

    with open(os.path.join(MODEL_DIR, "symptom_columns.json"), "w") as f:
        json.dump(symptom_columns, f, indent=2)

    with open(os.path.join(MODEL_DIR, "disease_specialist_map.json"), "w") as f:
        json.dump(disease_to_specialist, f, indent=2)

    print(f"Model trained on {len(df)} records covering {df['disease'].nunique()} diseases.")
    print(f"Artifacts saved to: {MODEL_DIR}")


if __name__ == "__main__":
    train()
