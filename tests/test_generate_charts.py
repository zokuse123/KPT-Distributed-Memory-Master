import csv
import tempfile
import unittest
from pathlib import Path

from generate_charts import ChartError, create_charts, load_summary


class GenerateChartsTests(unittest.TestCase):
    def write_summary(self, directory: Path) -> Path:
        path = directory / "summary.csv"
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "size", "mean_sequential_seconds",
                    "mean_distributed_seconds", "mean_speedup",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "size": 100,
                    "mean_sequential_seconds": 2.0,
                    "mean_distributed_seconds": 1.25,
                    # Deliberately different: parser must derive from mean times.
                    "mean_speedup": 999,
                }
            )
        return path

    def test_derives_speedup_and_efficiency_from_mean_times(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            point = load_summary(self.write_summary(Path(temp_dir)))[0]
            self.assertAlmostEqual(point.speedup, 1.6)
            self.assertAlmostEqual(point.efficiency_percent, 80.0)

    def test_rejects_missing_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text("size,mean_sequential_seconds\n100,2\n", encoding="utf-8")
            with self.assertRaises(ChartError):
                load_summary(path)

    def test_creates_three_png_files_without_gui(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            paths = create_charts(
                self.write_summary(directory),
                output_dir=directory / "charts",
                show=False,
            )
            self.assertEqual(len(paths), 3)
            for path in paths:
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
