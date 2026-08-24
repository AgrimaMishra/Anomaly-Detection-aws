"""Create canonical Phase 1 observations from a Jena Excel workbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from skyguard import normalize_workbook


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Source Jena .xlsx workbook")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "data/processed/observations.parquet",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPOSITORY_ROOT / "reports/data_quality_report.json",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=REPOSITORY_ROOT / "data/station_metadata.csv",
    )
    arguments = parser.parse_args()
    report = normalize_workbook(arguments.input, arguments.output, arguments.report, arguments.metadata)
    print(f"Normalized {report['row_counts']['normalized']:,} rows to {arguments.output}")
    print(f"Quality report: {arguments.report}")


if __name__ == "__main__":
    main()
