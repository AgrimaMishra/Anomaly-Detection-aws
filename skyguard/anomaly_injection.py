"""Reproducible synthetic fault injection for canonical weather observations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

SENSOR_COLUMNS = ("temp_c", "pressure_hpa", "humidity_pct")
LABEL_COLUMNS = (
    "is_anomaly", "anomaly_type", "severity", "injected_sensor",
    "injection_method", "injection_id", "injection_seed",
)


@dataclass(frozen=True)
class InjectionSummary:
    seed: int
    rows: int
    anomalous_rows: int
    counts_by_method: dict[str, int]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _prepare_frame(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    missing = [name for name in ("timestamp_utc", "station_id", *SENSOR_COLUMNS) if name not in frame]
    if missing:
        raise ValueError(f"Canonical observations are missing: {', '.join(missing)}")
    prepared = frame.copy(deep=True)
    prepared["timestamp_utc"] = pd.to_datetime(prepared["timestamp_utc"], utc=True)
    prepared.sort_values(["station_id", "timestamp_utc"], kind="mergesort", inplace=True)
    prepared.reset_index(drop=True, inplace=True)
    for sensor in SENSOR_COLUMNS:
        prepared[f"original_{sensor}"] = prepared[sensor]
    prepared["is_anomaly"] = 0
    prepared["anomaly_type"] = "normal"
    prepared["severity"] = 0
    prepared["injected_sensor"] = ""
    prepared["injection_method"] = "none"
    prepared["injection_id"] = ""
    prepared["injection_seed"] = seed
    return prepared


def _label(frame: pd.DataFrame, indices: np.ndarray, *, anomaly_type: str, severity: Iterable[int] | int,
           sensor: str, method: str, injection_id: str) -> None:
    frame.loc[indices, "is_anomaly"] = 1
    frame.loc[indices, "anomaly_type"] = anomaly_type
    frame.loc[indices, "severity"] = severity
    frame.loc[indices, "injected_sensor"] = sensor
    frame.loc[indices, "injection_method"] = method
    frame.loc[indices, "injection_id"] = injection_id


def _take_isolated(available: np.ndarray, rng: np.random.Generator, count: int) -> np.ndarray:
    candidates = np.flatnonzero(available)
    count = min(count, len(candidates))
    selected = np.sort(rng.choice(candidates, size=count, replace=False))
    available[selected] = False
    return selected


def _take_blocks(available: np.ndarray, rng: np.random.Generator, count: int,
                 minimum: int, maximum: int) -> list[np.ndarray]:
    blocks: list[np.ndarray] = []
    if len(available) < minimum:
        return blocks
    for _ in range(count * 30):
        if len(blocks) >= count:
            break
        length = int(rng.integers(minimum, maximum + 1))
        start = int(rng.integers(1, max(2, len(available) - length)))
        indices = np.arange(start, min(start + length, len(available)))
        if len(indices) >= minimum and available[indices].all():
            available[indices] = False
            blocks.append(indices)
    return blocks


def _inject_spikes(frame: pd.DataFrame, available: np.ndarray, rng: np.random.Generator,
                   seed: int, count: int) -> None:
    scales = {"temp_c": (8.0, 16.0), "pressure_hpa": (12.0, 30.0), "humidity_pct": (18.0, 40.0)}
    indices = _take_isolated(available, rng, count)
    sensors = rng.choice(SENSOR_COLUMNS, size=len(indices))
    deltas = np.array([
        rng.uniform(*scales[str(sensor)]) * rng.choice((-1, 1)) for sensor in sensors
    ])
    for sensor in SENSOR_COLUMNS:
        mask = sensors == sensor
        selected = indices[mask]
        frame.loc[selected, sensor] = frame.loc[selected, sensor].to_numpy() + deltas[mask]
    frame.loc[indices, "is_anomaly"] = 1
    frame.loc[indices, "anomaly_type"] = "spike"
    frame.loc[indices, "severity"] = np.minimum(100, 45 + 2 * np.abs(deltas)).astype(int)
    frame.loc[indices, "injected_sensor"] = sensors
    frame.loc[indices, "injection_method"] = "spike"
    frame.loc[indices, "injection_id"] = [f"{seed}-spike-{number:05d}" for number in range(len(indices))]


def _inject_frozen(frame: pd.DataFrame, blocks: list[np.ndarray], rng: np.random.Generator, seed: int) -> None:
    for number, indices in enumerate(blocks):
        sensor = str(rng.choice(SENSOR_COLUMNS))
        frame.loc[indices, sensor] = frame.at[indices[0] - 1, sensor]
        _label(frame, indices, anomaly_type="frozen", severity=min(100, 40 + len(indices) * 2), sensor=sensor,
               method="frozen", injection_id=f"{seed}-frozen-{number:05d}")


def _inject_drift(frame: pd.DataFrame, blocks: list[np.ndarray], rng: np.random.Generator, seed: int) -> None:
    for number, indices in enumerate(blocks):
        sensor = str(rng.choice(("temp_c", "pressure_hpa")))
        maximum = float(rng.uniform(6, 14) if sensor == "temp_c" else rng.uniform(8, 20))
        maximum *= int(rng.choice((-1, 1)))
        offsets = np.linspace(maximum / len(indices), maximum, len(indices))
        frame.loc[indices, sensor] = frame.loc[indices, sensor].to_numpy() + offsets
        severity = np.linspace(25, min(100, 50 + abs(maximum) * 2), len(indices)).astype(int)
        _label(frame, indices, anomaly_type="drift", severity=severity, sensor=sensor,
               method="drift", injection_id=f"{seed}-drift-{number:05d}")


def _inject_missing(frame: pd.DataFrame, blocks: list[np.ndarray], rng: np.random.Generator, seed: int) -> None:
    for number, indices in enumerate(blocks):
        sensor = str(rng.choice(SENSOR_COLUMNS))
        frame.loc[indices, sensor] = np.nan
        _label(frame, indices, anomaly_type="missing", severity=min(100, 45 + len(indices) * 2), sensor=sensor,
               method="missing_block", injection_id=f"{seed}-missing-{number:05d}")


def _inject_pressure_jumps(frame: pd.DataFrame, blocks: list[np.ndarray], rng: np.random.Generator,
                           seed: int) -> None:
    for number, indices in enumerate(blocks):
        jump = float(rng.uniform(12, 25) * rng.choice((-1, 1)))
        frame.loc[indices, "pressure_hpa"] = frame.loc[indices, "pressure_hpa"] + jump
        _label(frame, indices, anomaly_type="spike", severity=min(100, int(55 + abs(jump))),
               sensor="pressure_hpa", method="pressure_jump",
               injection_id=f"{seed}-pressure-jump-{number:05d}")


def _inject_impossible_humidity(frame: pd.DataFrame, available: np.ndarray, rng: np.random.Generator,
                                seed: int, count: int) -> None:
    indices = _take_isolated(available, rng, count)
    high = rng.random(len(indices)) >= 0.5
    values = np.where(high, rng.uniform(105, 140, len(indices)), rng.uniform(-30, -5, len(indices)))
    frame.loc[indices, "humidity_pct"] = values
    frame.loc[indices, "is_anomaly"] = 1
    frame.loc[indices, "anomaly_type"] = "out_of_range"
    frame.loc[indices, "severity"] = np.minimum(100, 70 + np.abs(values - 50) / 4).astype(int)
    frame.loc[indices, "injected_sensor"] = "humidity_pct"
    frame.loc[indices, "injection_method"] = "impossible_humidity_pattern"
    frame.loc[indices, "injection_id"] = [f"{seed}-humidity-{number:05d}" for number in range(len(indices))]


def inject_anomalies(frame: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, InjectionSummary]:
    """Inject all supported fault types into a copy of a canonical observation frame."""
    result = _prepare_frame(frame, seed)
    rng = np.random.default_rng(seed)
    available = np.ones(len(result), dtype=bool)
    isolated_count = max(1, len(result) // 500)
    block_count = max(1, len(result) // 20000)

    _inject_spikes(result, available, rng, seed, isolated_count)
    _inject_frozen(result, _take_blocks(available, rng, block_count, 6, 18), rng, seed)
    _inject_drift(result, _take_blocks(available, rng, block_count, 12, 36), rng, seed)
    _inject_missing(result, _take_blocks(available, rng, block_count, 6, 18), rng, seed)
    _inject_pressure_jumps(result, _take_blocks(available, rng, block_count, 3, 12), rng, seed)
    _inject_impossible_humidity(result, available, rng, seed, isolated_count)

    for sensor in SENSOR_COLUMNS:
        result[f"injected_{sensor}"] = result[sensor]
    counts = result.loc[result.is_anomaly.eq(1), "injection_method"].value_counts().sort_index().to_dict()
    summary = InjectionSummary(seed, len(result), int(result.is_anomaly.sum()), counts)
    return result, summary


def chronological_split(frame: pd.DataFrame, train_fraction: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    ordered = frame.copy()
    ordered["timestamp_utc"] = pd.to_datetime(ordered["timestamp_utc"], utc=True)
    ordered.sort_values(["timestamp_utc", "station_id"], kind="mergesort", inplace=True)
    split_index = int(len(ordered) * train_fraction)
    return ordered.iloc[:split_index].copy(), ordered.iloc[split_index:].copy()


def write_labelled_csv(frame: pd.DataFrame, path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", date_format="%Y-%m-%dT%H:%M:%SZ", lineterminator="\n")
    return sha256_file(path)


def write_injection_report(path: str | Path, *, source_path: Path, source_hash: str,
                           train: InjectionSummary, test: InjectionSummary,
                           train_path: Path, test_path: Path) -> None:
    report = {
        "source": {"path": str(source_path.resolve()), "sha256": source_hash},
        "split": {"method": "chronological", "train_fraction": 0.8},
        "train": {**train.__dict__, "path": str(train_path.resolve()), "sha256": sha256_file(train_path)},
        "test": {**test.__dict__, "path": str(test_path.resolve()), "sha256": sha256_file(test_path)},
        "faults": ["spike", "frozen", "drift", "missing_block", "pressure_jump", "impossible_humidity_pattern"],
    }
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
