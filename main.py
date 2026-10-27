import sys
import time
from collections import deque

try:
    import psutil
except ImportError:  # pragma: no cover - reported when the application starts
    psutil = None


HISTORY_LENGTH = 60


def calculate_rate(current: int, previous: int, interval: float) -> float:
    """Return a counter delta as bytes per second."""
    if interval <= 0 or current < previous:
        return 0.0
    return (current - previous) / interval


def format_rate(bytes_per_second: float) -> str:
    """Format a byte rate for a compact UI label."""
    if bytes_per_second >= 1024 * 1024:
        return f"{bytes_per_second / (1024 * 1024):.2f} MB/s"
    return f"{bytes_per_second / 1024:.1f} KB/s"


def format_bytes(bytes_value: int) -> str:
    """Format a byte count using a readable binary unit."""
    value = float(bytes_value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def _counter_value(counter, name: str) -> int:
    return int(getattr(counter, name, 0) or 0)


class MetricsSampler:
    """Read cumulative system counters and turn them into display metrics."""

    def __init__(self):
        if psutil is None:
            raise RuntimeError(
                "缺少运行依赖，请先执行: pip install -r requirements.txt"
            )
        self._previous_network = psutil.net_io_counters()
        self._previous_disk = psutil.disk_io_counters()
        self._previous_time = time.monotonic()

    def sample_metrics(self) -> dict:
        current_time = time.monotonic()
        interval = current_time - self._previous_time
        network = psutil.net_io_counters()
        disk = psutil.disk_io_counters()
        memory = psutil.virtual_memory()

        metrics = {
            "upload_rate": calculate_rate(
                _counter_value(network, "bytes_sent"),
                _counter_value(self._previous_network, "bytes_sent"),
                interval,
            ),
            "download_rate": calculate_rate(
                _counter_value(network, "bytes_recv"),
                _counter_value(self._previous_network, "bytes_recv"),
                interval,
            ),
            "memory_percent": float(memory.percent),
            "memory_used": int(memory.used),
            "memory_total": int(memory.total),
            "read_rate": calculate_rate(
                _counter_value(disk, "read_bytes"),
                _counter_value(self._previous_disk, "read_bytes"),
                interval,
            ),
            "write_rate": calculate_rate(
                _counter_value(disk, "write_bytes"),
                _counter_value(self._previous_disk, "write_bytes"),
                interval,
            ),
        }

        self._previous_network = network
        self._previous_disk = disk
        self._previous_time = current_time
        return metrics


try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QGridLayout,
        QGroupBox,
        QLabel,
        QMainWindow,
        QVBoxLayout,
        QWidget,
    )
    import pyqtgraph as pg
except ImportError:  # pragma: no cover - exercised only without GUI dependencies
    GUI_AVAILABLE = False

    class SystemMonitorWindow:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "缺少 GUI 依赖，请先执行: pip install -r requirements.txt"
            )
else:
    GUI_AVAILABLE = True

    class SystemMonitorWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Windows 系统资源监视器")
            self.resize(1000, 760)
            self.setMinimumSize(800, 600)

            self.sampler = MetricsSampler()
            self.history = {
                "upload": deque(maxlen=HISTORY_LENGTH),
                "download": deque(maxlen=HISTORY_LENGTH),
                "memory": deque(maxlen=HISTORY_LENGTH),
                "read": deque(maxlen=HISTORY_LENGTH),
                "write": deque(maxlen=HISTORY_LENGTH),
            }
            self.labels = {}
            self._build_ui()

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_metrics)
            self.timer.start(1000)

        def _build_ui(self):
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            root_layout = QVBoxLayout(central_widget)

            title = QLabel("Windows 系统资源监视器")
            title.setStyleSheet("font-size: 22px; font-weight: bold; padding: 8px;")
            root_layout.addWidget(title)

            cards_layout = QGridLayout()
            cards_layout.addWidget(
                self._create_card(
                    "网络",
                    [("upload", "上传"), ("download", "下载")],
                ),
                0,
                0,
            )
            cards_layout.addWidget(
                self._create_card(
                    "内存",
                    [("memory_percent", "使用率"), ("memory_capacity", "已用/总量")],
                ),
                0,
                1,
            )
            cards_layout.addWidget(
                self._create_card(
                    "磁盘",
                    [("read", "读取"), ("write", "写入")],
                ),
                0,
                2,
            )
            root_layout.addLayout(cards_layout)

            self.network_plot = self._create_plot(
                "网络速率", [("上传", "#4dabf7"), ("下载", "#51cf66")]
            )
            self.memory_plot = self._create_plot(
                "内存使用率", [("使用率", "#fcc419")]
            )
            self.disk_plot = self._create_plot(
                "磁盘速率", [("读取", "#da77f2"), ("写入", "#ff8787")]
            )
            root_layout.addWidget(self.network_plot)
            root_layout.addWidget(self.memory_plot)
            root_layout.addWidget(self.disk_plot)

        def _create_card(self, title: str, rows: list[tuple[str, str]]) -> QGroupBox:
            card = QGroupBox(title)
            layout = QVBoxLayout(card)
            for key, label_text in rows:
                label = QLabel(f"{label_text}: --")
                label.setStyleSheet("font-size: 14px; padding: 4px;")
                self.labels[key] = label
                layout.addWidget(label)
            return card

        def _create_plot(
            self, title: str, curves: list[tuple[str, str]]
        ) -> pg.PlotWidget:
            plot = pg.PlotWidget(title=title)
            plot.setBackground("#18202f")
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.setLabel("bottom", "最近 60 秒")
            plot.setXRange(0, HISTORY_LENGTH - 1, padding=0)
            plot.addLegend()
            plot.curves = {
                name: plot.plot(pen=pg.mkPen(color=color, width=2), name=name)
                for name, color in curves
            }
            return plot

        def update_metrics(self):
            metrics = self.sampler.sample_metrics()
            self.labels["upload"].setText(
                f"上传: {format_rate(metrics['upload_rate'])}"
            )
            self.labels["download"].setText(
                f"下载: {format_rate(metrics['download_rate'])}"
            )
            self.labels["memory_percent"].setText(
                f"使用率: {metrics['memory_percent']:.1f}%"
            )
            self.labels["memory_capacity"].setText(
                "已用/总量: "
                f"{format_bytes(metrics['memory_used'])} / "
                f"{format_bytes(metrics['memory_total'])}"
            )
            self.labels["read"].setText(
                f"读取: {format_rate(metrics['read_rate'])}"
            )
            self.labels["write"].setText(
                f"写入: {format_rate(metrics['write_rate'])}"
            )

            self.history["upload"].append(metrics["upload_rate"])
            self.history["download"].append(metrics["download_rate"])
            self.history["memory"].append(metrics["memory_percent"])
            self.history["read"].append(metrics["read_rate"])
            self.history["write"].append(metrics["write_rate"])
            self.update_charts()

        def update_charts(self):
            x_values = list(range(len(self.history["memory"])))
            self.network_plot.curves["上传"].setData(
                x_values, list(self.history["upload"])
            )
            self.network_plot.curves["下载"].setData(
                x_values, list(self.history["download"])
            )
            self.memory_plot.curves["使用率"].setData(
                x_values, list(self.history["memory"])
            )
            self.memory_plot.setYRange(0, 100, padding=0)
            self.disk_plot.curves["读取"].setData(
                x_values, list(self.history["read"])
            )
            self.disk_plot.curves["写入"].setData(
                x_values, list(self.history["write"])
            )

        def closeEvent(self, event):
            self.timer.stop()
            event.accept()


def main() -> int:
    if not GUI_AVAILABLE or psutil is None:
        raise RuntimeError(
            "缺少运行依赖，请先执行: pip install -r requirements.txt"
        )
    app = QApplication(sys.argv)
    window = SystemMonitorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
