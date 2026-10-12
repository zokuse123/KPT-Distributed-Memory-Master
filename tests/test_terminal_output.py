import unittest

from benchmark import RunResult, format_run_result


class TerminalOutputTests(unittest.TestCase):
    def test_format_run_result_contains_required_actual_values(self):
        result = RunResult(
            size=100_000,
            data_count=99_999,
            repetition=3,
            task_id="run-003",
            pc1_start=2,
            pc1_end=50_001,
            pc2_start=50_002,
            pc2_end=100_000,
            pc1_prime_count=5_133,
            pc2_prime_count=4_459,
            total_prime_count=9_592,
            sequential_prime_count=9_592,
            sequential_seconds=0.0622481,
            distributed_seconds=0.0594531,
            worker_compute_seconds=0.048239,
            speedup=1.0470118,
            efficiency_percent=52.35059,
            verified=True,
        )

        output = format_run_result(result)

        expected_fragments = (
            "run-003", "N=100,000", "Repetisi 3",
            "Jumlah data total : 99,999",
            "rentang 2..50,001 | beban 50,000 data | hasil 5,133 prima",
            "rentang 50,002..100,000 | beban 49,999 data | hasil 4,459 prima",
            "Hasil gabungan    : 9,592 prima",
            "Hasil sequential  : 9,592 prima | verifikasi SESUAI",
            "Waktu sequential  : 0.062248 detik",
            "Waktu distributed : 0.059453 detik",
            "compute Worker 0.048239 detik",
            "Speedup            : 1.047x",
            "Efficiency (2 PC)  : 52.35%",
        )
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, output)


if __name__ == "__main__":
    unittest.main()
