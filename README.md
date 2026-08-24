# SkyGuard AI

SkyGuard AI currently provides a deterministic weather-normalization pipeline and
seeded synthetic anomaly injection for training and evaluation data.

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

## Inject labelled anomalies

```powershell
python scripts/inject_anomalies.py --seed 42
```

Outputs:

- `data/processed/labelled_train.csv`
- `data/processed/labelled_test.csv`
- `reports/anomaly_injection_report.json`

The split is chronological (80% train, 20% test) and occurs before injection.
Supported faults are isolated spikes, frozen sensor blocks, gradual drift, missing
sensor blocks, sustained pressure jumps, and impossible humidity patterns. Every
labelled row retains the original temperature, pressure, and humidity values plus
the injected values, injection method, seed, severity, sensor, and event identifier.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The tests cover Phase 1 schema and normalization plus every Phase 2 fault type,
original-value retention, chronological splitting, severity bounds, and byte-for-byte
determinism.

GitHub Actions runs the same suite on Python 3.11 for every push and pull request.
