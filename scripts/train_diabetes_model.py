import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.training_pipeline import load_dataset_from_path, train_production_model

DEFAULT_DATA = (
    PROJECT_ROOT / "data" / "training" / "diabetes_binary_health_indicators_BRFSS2015.csv"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts"


def parse_args():
    parser = argparse.ArgumentParser(description="Train the production diabetes risk model.")
    parser.add_argument(
        "--data", default=str(DEFAULT_DATA), help="Local CSV file or dataset directory."
    )
    parser.add_argument(
        "--output-dir", default=str(DEFAULT_OUTPUT), help="Local directory for model outputs."
    )
    parser.add_argument("--explanation-sample-size", type=int, default=2500)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    data_path, X, y = load_dataset_from_path(args.data)
    train_production_model(
        X,
        y,
        data_path=data_path,
        output_dir=args.output_dir,
        explanation_sample_size=args.explanation_sample_size,
    )
