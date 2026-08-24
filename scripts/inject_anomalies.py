"""Create deterministic labelled Phase 2 training and test datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from skyguard.anomaly_injection import (
    chronological_split,
    inject_anomalies,
    sha256_file,
    write_injection_report,
    write_labelled_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=REPOSITORY_ROOT / "data/processed/observations.parquet")
    parser.add_argument("--train-output", type=Path, default=REPOSITORY_ROOT / "data/processed/labelled_train.csv")
    parser.add_argument("--test-output", type=Path, default=REPOSITORY_ROOT / "data/processed/labelled_test.csv")
    parser.add_argument("--report", type=Path, default=REPOSITORY_ROOT / "reports/anomaly_injection_report.json")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    arguments = parser.parse_args()

    observations = pd.read_parquet(arguments.input)
    train_source, test_source = chronological_split(observations, arguments.train_fraction)
    labelled_train, train_summary = inject_anomalies(train_source, arguments.seed)
    labelled_test, test_summary = inject_anomalies(test_source, arguments.seed + 1)
    write_labelled_csv(labelled_train, arguments.train_output)
    write_labelled_csv(labelled_test, arguments.test_output)
    write_injection_report(
        arguments.report,
        source_path=arguments.input,
        source_hash=sha256_file(arguments.input),
        train=train_summary,
        test=test_summary,
        train_path=arguments.train_output,
        test_path=arguments.test_output,
    )
    print(f"Train: {train_summary.rows:,} rows, {train_summary.anomalous_rows:,} anomalies")
    print(f"Test:  {test_summary.rows:,} rows, {test_summary.anomalous_rows:,} anomalies")
    print(f"Outputs: {arguments.train_output} and {arguments.test_output}")


if __name__ == "__main__":
    main()
