import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main as monitor
from main import calculate_rate, format_bytes, format_rate


class MonitorFormattingTests(unittest.TestCase):
    def test_calculate_rate_returns_bytes_per_second(self):
        self.assertEqual(calculate_rate(3072, 1024, 2), 1024.0)

    def test_calculate_rate_ignores_counter_reset(self):
        self.assertEqual(calculate_rate(100, 200, 1), 0.0)

    def test_calculate_rate_handles_non_positive_interval(self):
        self.assertEqual(calculate_rate(100, 0, 0), 0.0)

    def test_format_rate_uses_kilobytes_and_megabytes(self):
        self.assertEqual(format_rate(512 * 1024), "512.0 KB/s")
        self.assertEqual(format_rate(2 * 1024 * 1024), "2.00 MB/s")

    def test_format_bytes_formats_memory_capacity(self):
        self.assertEqual(format_bytes(1024**3), "1.00 GB")

    def test_sampler_converts_counter_deltas_to_rates(self):
        counters = iter(
            [
                SimpleNamespace(bytes_sent=100, bytes_recv=200),
                SimpleNamespace(bytes_sent=1100, bytes_recv=2200),
            ]
        )
        disk_counters = iter(
            [
                SimpleNamespace(read_bytes=300, write_bytes=400),
                SimpleNamespace(read_bytes=1300, write_bytes=2400),
            ]
        )
        fake_psutil = SimpleNamespace(
            net_io_counters=lambda: next(counters),
            disk_io_counters=lambda: next(disk_counters),
            virtual_memory=lambda: SimpleNamespace(
                percent=50.0, used=1024, total=2048
            ),
        )

        with patch.object(monitor, "psutil", fake_psutil), patch.object(
            monitor.time, "monotonic", side_effect=[10.0, 11.0]
        ):
            sampler = monitor.MetricsSampler()
            metrics = sampler.sample_metrics()

        self.assertEqual(metrics["upload_rate"], 1000.0)
        self.assertEqual(metrics["download_rate"], 2000.0)
        self.assertEqual(metrics["read_rate"], 1000.0)
        self.assertEqual(metrics["write_rate"], 2000.0)
        self.assertEqual(metrics["memory_percent"], 50.0)

    def test_main_reports_missing_dependencies(self):
        with patch.object(monitor, "GUI_AVAILABLE", False):
            with self.assertRaisesRegex(RuntimeError, "pip install"):
                monitor.main()


if __name__ == "__main__":
    unittest.main()
