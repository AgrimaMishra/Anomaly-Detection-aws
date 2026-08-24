from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import openpyxl
import pyarrow.parquet as pq

from skyguard.data_pipeline import CANONICAL_COLUMNS, SOURCE_COLUMNS, normalize_workbook


class DataPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.metadata_path = self.root / "station_metadata.csv"
        self.metadata_path.write_text(
            "station_id,latitude,longitude,timezone\nJENA,50.9271,11.5892,Europe/Berlin\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def observation(timestamp: str, temperature: float = 10, pressure: float = 1000,
                    humidity: float = 70) -> list[object]:
        return [timestamp, pressure, temperature, 280, 5, humidity, 12, 8, 4, 5, 8, 1200, 1, 2, 180]

    def create_workbook(self, observations: list[list[object]]) -> Path:
        path = self.root / "raw.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Jena Climate"
        sheet.append(SOURCE_COLUMNS)
        for observation in observations:
            sheet.append(observation)
        workbook.save(path)
        return path

    def run_pipeline(self, source: Path, suffix: str = ""):
        output_path = self.root / f"observations{suffix}.parquet"
        report = normalize_workbook(
            source,
            output_path,
            self.root / f"report{suffix}.json",
            self.metadata_path,
        )
        return output_path, report

    def test_schema_timestamps_sorting_uniqueness_and_units(self) -> None:
        source = self.create_workbook([
            self.observation("01.01.2009 00:20:00"),
            self.observation("01.01.2009 00:10:00"),
            self.observation("01.01.2009 00:10:00"),
        ])
        output, report = self.run_pipeline(source)
        table = pq.read_table(output)
        frame = table.to_pandas()
        self.assertEqual(table.column_names, CANONICAL_COLUMNS)
        self.assertEqual(str(table.schema.field("timestamp_utc").type), "timestamp[us, tz=UTC]")
        self.assertTrue(frame.timestamp_utc.is_monotonic_increasing)
        self.assertFalse(frame.duplicated(["station_id", "timestamp_utc"]).any())
        self.assertEqual(frame.iloc[0].pressure_hpa, 1000)
        self.assertEqual(report["duplicates"]["remaining"], 0)

    def test_raw_workbook_and_quality_report(self) -> None:
        source = self.create_workbook([self.observation("01.01.2009 00:10:00", humidity=101)])
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        _, report = self.run_pipeline(source)
        self.assertEqual(original_hash, hashlib.sha256(source.read_bytes()).hexdigest())
        for field in ("row_counts", "missing_values", "duplicates", "timestamp_gaps", "suspect_values"):
            self.assertIn(field, report)
        self.assertEqual(report["suspect_values"]["humidity_pct"], 1)

    def test_output_is_byte_for_byte_deterministic(self) -> None:
        source = self.create_workbook([
            self.observation("01.01.2009 00:10:00"),
            self.observation("01.01.2009 00:20:00"),
        ])
        first, _ = self.run_pipeline(source, "1")
        second, _ = self.run_pipeline(source, "2")
        self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())


if __name__ == "__main__":
    unittest.main()
