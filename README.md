# SkyGuard AI

Phase 1 provides a deterministic weather-normalization pipeline for the supplied
Jena climate workbook. It produces UTC-aware, station-sorted canonical observations
and a machine-readable data-quality report. Phase 2 has not started.

## Requirements

- Python 3.11

## Setup

```powershell
python -m pip install -r requirements.txt
```

## Normalize the Jena workbook

```powershell
python scripts/normalize_weather.py --input "C:\Users\ADEEP MISHRA\Downloads\jena_climate_2009_2016.xlsx"
```

Outputs:

- `data/processed/observations.parquet`
- `reports/data_quality_report.json`

Full generated datasets and reports are intentionally ignored by Git. A small,
redistributable 24-hour example is tracked at `data/sample_observations.csv`.

The pipeline interprets source timestamps in `Europe/Berlin`, resolves repeated
daylight-saving wall times deterministically, converts to UTC, performs a stable
station/timestamp sort, and retains the first duplicate. Raw model-input values,
source row numbers, and quality flags remain available in the Parquet output.
Pressure is renamed from mbar to hPa without numeric scaling because 1 mbar equals
1 hPa.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The tests cover schema, timezone, ordering, uniqueness, units, source immutability,
quality-report fields, suspect-value detection, and byte-for-byte determinism.

GitHub Actions runs the same suite on Python 3.11 for every push and pull request.

