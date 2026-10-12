"""Create benchmark charts from an existing summary CSV file."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REQUIRED_COLUMNS = {
    "size",
    "mean_sequential_seconds",
    "mean_distributed_seconds",
}


class ChartError(Exception):
    """Raised when chart input is invalid or charts cannot be generated."""


@dataclass(frozen=True)
class SummaryPoint:
    size: int
    sequential_seconds: float
    distributed_seconds: float
    speedup: float
    efficiency_percent: float


def load_summary(csv_path: Path) -> list[SummaryPoint]:
    """Load summary means and derive speedup and efficiency from those means."""
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            columns = set(reader.fieldnames or [])
            missing = REQUIRED_COLUMNS - columns
            if missing:
                raise ChartError(
                    "kolom CSV tidak lengkap; tidak ditemukan: "
                    + ", ".join(sorted(missing))
                )

            points: list[SummaryPoint] = []
            seen_sizes: set[int] = set()
            for line_number, row in enumerate(reader, start=2):
                try:
                    size = int(row["size"])
                    sequential = float(row["mean_sequential_seconds"])
                    distributed = float(row["mean_distributed_seconds"])
                except (TypeError, ValueError) as exc:
                    raise ChartError(
                        f"nilai numerik tidak valid pada baris {line_number}"
                    ) from exc
                if size <= 0 or size in seen_sizes:
                    raise ChartError(
                        f"size harus positif dan unik pada baris {line_number}"
                    )
                if not all(map(math.isfinite, (sequential, distributed))):
                    raise ChartError(f"waktu tidak finite pada baris {line_number}")
                if sequential < 0 or distributed <= 0:
                    raise ChartError(
                        f"waktu sequential harus >= 0 dan distributed harus > 0 "
                        f"pada baris {line_number}"
                    )
                speedup = sequential / distributed
                points.append(
                    SummaryPoint(
                        size=size,
                        sequential_seconds=sequential,
                        distributed_seconds=distributed,
                        speedup=speedup,
                        efficiency_percent=(speedup / 2.0) * 100.0,
                    )
                )
                seen_sizes.add(size)
    except OSError as exc:
        raise ChartError(f"tidak dapat membaca {csv_path}: {exc}") from exc

    if not points:
        raise ChartError("CSV ringkasan tidak memiliki baris data")
    return sorted(points, key=lambda point: point.size)


def print_summary(points: Sequence[SummaryPoint]) -> None:
    """Print the exact derived values used by the charts."""
    print("\nRingkasan visualisasi (dihitung dari mean waktu CSV):")
    print(f"{'N':>12} {'Sequential (s)':>16} {'Distributed (s)':>17} "
          f"{'Speedup':>10} {'Efficiency':>12}")
    for point in points:
        print(
            f"{point.size:>12,d} {point.sequential_seconds:>16.6f} "
            f"{point.distributed_seconds:>17.6f} {point.speedup:>9.3f}x "
            f"{point.efficiency_percent:>11.2f}%"
        )


def create_charts(
    summary_csv: Path, *, output_dir: Path | None = None, show: bool = True
) -> list[Path]:
    """Create three PNG charts; showing them is best-effort and never required."""
    points = load_summary(summary_csv)
    print_summary(points)
    chart_dir = output_dir or summary_csv.parent / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ChartError(
            "Matplotlib belum terpasang. Jalankan: py -3.14 -m pip install matplotlib"
        ) from exc

    sizes = [point.size for point in points]
    labels = [f"{size:,}" for size in sizes]
    sequential = [point.sequential_seconds for point in points]
    distributed = [point.distributed_seconds for point in points]
    speedups = [point.speedup for point in points]
    efficiencies = [point.efficiency_percent for point in points]
    figures = []
    paths: list[Path] = []

    try:
        # Mean execution-time comparison.
        fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
        positions = list(range(len(points)))
        width = 0.36
        bars_seq = ax.bar(
            [position - width / 2 for position in positions], sequential,
            width, label="Sequential", color="#4472C4"
        )
        bars_dist = ax.bar(
            [position + width / 2 for position in positions], distributed,
            width, label="Distributed", color="#ED7D31"
        )
        ax.bar_label(bars_seq, fmt="%.3f s", padding=3, fontsize=9)
        ax.bar_label(bars_dist, fmt="%.3f s", padding=3, fontsize=9)
        ax.set_title("Rata-rata Waktu Sequential vs Distributed")
        ax.set_xlabel("Ukuran Data (N)")
        ax.set_ylabel("Rata-rata Waktu (detik)")
        ax.set_xticks(positions, labels)
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
        figures.append(fig)
        paths.append(chart_dir / "sequential-vs-distributed.png")

        # Speedup derived from the ratio of mean execution times.
        fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
        positions = list(range(len(points)))
        ax.plot(positions, speedups, marker="o", linewidth=2, color="#2F75B5",
                label="Speedup aktual")
        ax.axhline(1.0, color="#C00000", linestyle="--", linewidth=1.5,
                   label="Referensi speedup = 1")
        for position, value in zip(positions, speedups):
            ax.annotate(f"{value:.3f}x", (position, value), xytext=(0, 8),
                        textcoords="offset points", ha="center")
        ax.set_title("Speedup terhadap Ukuran Data")
        ax.set_xlabel("Ukuran Data (N)")
        ax.set_ylabel("Speedup (kali)")
        ax.set_xticks(positions, labels)
        ax.margins(x=0.12, y=0.18)
        ax.legend()
        ax.grid(alpha=0.25)
        figures.append(fig)
        paths.append(chart_dir / "speedup.png")

        # Two-PC efficiency derived from speedup.
        fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
        bars = ax.bar(labels, efficiencies, color="#70AD47", width=0.6,
                      label="Efficiency (2 PC)")
        ax.bar_label(bars, fmt="%.2f%%", padding=3)
        ax.set_title("Efficiency terhadap Ukuran Data")
        ax.set_xlabel("Ukuran Data (N)")
        ax.set_ylabel("Efficiency (%)")
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
        figures.append(fig)
        paths.append(chart_dir / "efficiency.png")

        for figure, path in zip(figures, paths):
            figure.savefig(path, dpi=180, bbox_inches="tight")
            print(f"Grafik tersimpan: {path}")

        if show:
            try:
                plt.show()
            except Exception as exc:  # GUI/backend failure must not lose PNG output.
                print(f"PERINGATAN: GUI grafik tidak tersedia ({exc}); PNG tetap tersimpan.")
    except OSError as exc:
        raise ChartError(f"gagal menyimpan grafik: {exc}") from exc
    finally:
        for figure in figures:
            plt.close(figure)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Buat ulang grafik dari CSV ringkasan tanpa benchmark"
    )
    parser.add_argument("summary_csv", type=Path, help="path summary-*.csv")
    parser.add_argument("--output-dir", type=Path, help="default: results/charts")
    parser.add_argument("--no-show", action="store_true", help="simpan tanpa GUI")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        create_charts(
            args.summary_csv, output_dir=args.output_dir, show=not args.no_show
        )
    except ChartError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

