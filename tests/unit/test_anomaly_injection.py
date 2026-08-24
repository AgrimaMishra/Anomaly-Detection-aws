from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from skyguard.anomaly_injection import chronological_split, inject_anomalies, write_labelled_csv


def observations(count: int = 1000) -> pd.DataFrame:
    index = np.arange(count)
    return pd.DataFrame({
        "timestamp_utc": pd.date_range("2025-01-01", periods=count, freq="10min", tz="UTC"),
        "station_id": "TEST",
        "latitude": 28.56,
        "longitude": 77.10,
        "temp_c": 20 + np.sin(index / 20),
        "pressure_hpa": 1000 + np.sin(index / 40),
        "humidity_pct": 60 + np.sin(index / 25) * 5,
        "source": "fixture",
    })


class AnomalyInjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = observations()
        cls.labelled, cls.summary = inject_anomalies(cls.original, seed=123)

    def method_rows(self, method: str) -> pd.DataFrame:
        rows = self.labelled[self.labelled.injection_method.eq(method)]
        self.assertGreater(len(rows), 0, f"No rows generated for {method}")
        return rows

    def test_spikes_change_the_labelled_sensor(self) -> None:
        rows = self.method_rows("spike")
        for _, row in rows.iterrows():
            self.assertNotEqual(row[row.injected_sensor], row[f"original_{row.injected_sensor}"])
            self.assertEqual(row.anomaly_type, "spike")

    def test_frozen_blocks_repeat_a_sensor_value(self) -> None:
        rows = self.method_rows("frozen")
        for _, group in rows.groupby("injection_id"):
            sensor = group.injected_sensor.iloc[0]
            self.assertEqual(group[sensor].nunique(dropna=False), 1)
            self.assertEqual(set(group.anomaly_type), {"frozen"})

    def test_drift_offsets_increase_over_the_block(self) -> None:
        rows = self.method_rows("drift")
        for _, group in rows.groupby("injection_id"):
            sensor = group.injected_sensor.iloc[0]
            offset = (group[sensor] - group[f"original_{sensor}"]).abs().to_numpy()
            self.assertTrue(np.all(np.diff(offset) >= -1e-12))
            self.assertEqual(set(group.anomaly_type), {"drift"})

    def test_missing_blocks_preserve_original_values(self) -> None:
        rows = self.method_rows("missing_block")
        for _, row in rows.iterrows():
            self.assertTrue(pd.isna(row[row.injected_sensor]))
            self.assertFalse(pd.isna(row[f"original_{row.injected_sensor}"]))
            self.assertEqual(row.anomaly_type, "missing")

    def test_pressure_jumps_only_change_pressure(self) -> None:
        rows = self.method_rows("pressure_jump")
        self.assertTrue((rows.pressure_hpa.sub(rows.original_pressure_hpa).abs() >= 12).all())
        self.assertTrue(rows.temp_c.equals(rows.original_temp_c))
        self.assertTrue(rows.humidity_pct.equals(rows.original_humidity_pct))

    def test_impossible_humidity_is_outside_physical_range(self) -> None:
        rows = self.method_rows("impossible_humidity_pattern")
        self.assertTrue(((rows.humidity_pct < 0) | (rows.humidity_pct > 100)).all())
        self.assertEqual(set(rows.anomaly_type), {"out_of_range"})

    def test_original_values_and_required_labels_are_retained(self) -> None:
        for sensor in ("temp_c", "pressure_hpa", "humidity_pct"):
            self.assertIn(f"original_{sensor}", self.labelled)
            self.assertIn(f"injected_{sensor}", self.labelled)
        self.assertTrue(set(self.labelled.is_anomaly.unique()).issubset({0, 1}))
        self.assertTrue(self.labelled.severity.between(0, 100).all())

    def test_fixed_seed_is_byte_deterministic(self) -> None:
        first, _ = inject_anomalies(self.original, seed=123)
        second, _ = inject_anomalies(self.original, seed=123)
        with tempfile.TemporaryDirectory() as directory:
            first_path, second_path = Path(directory) / "first.csv", Path(directory) / "second.csv"
            write_labelled_csv(first, first_path)
            write_labelled_csv(second, second_path)
            self.assertEqual(hashlib.sha256(first_path.read_bytes()).digest(), hashlib.sha256(second_path.read_bytes()).digest())

    def test_split_is_chronological_and_non_overlapping(self) -> None:
        train, test = chronological_split(self.original, train_fraction=0.8)
        self.assertEqual((len(train), len(test)), (800, 200))
        self.assertLess(train.timestamp_utc.max(), test.timestamp_utc.min())


if __name__ == "__main__":
    unittest.main()
