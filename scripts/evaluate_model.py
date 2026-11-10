import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.risk_model import RiskModel


def evaluate(data_path):
    df = pd.read_csv(data_path)
    train_df, test_df = train_test_split(df, test_size=0.3, random_state=42, stratify=df["target"])

    model = RiskModel()
    model.train(train_df)

    y_true = test_df["target"].tolist()
    y_prob = []
    y_pred = []
    for _, row in test_df.iterrows():
        prob, _ = model.assess(row.to_dict())
        y_prob.append(prob)
        y_pred.append(1 if prob >= 0.5 else 0)

    return {
        "samples_train": len(train_df),
        "samples_test": len(test_df),
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_true, y_prob), 4),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate the legacy demo model on sample data.")
    parser.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "patients.csv"),
        help="Demo CSV with features and target; not the production BRFSS evaluation.",
    )
    args = parser.parse_args()

    metrics = evaluate(args.data)
    print("Evaluation metrics")
    for key, value in metrics.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
