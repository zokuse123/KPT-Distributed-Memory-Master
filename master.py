"""Command-line entry point for the distributed prime-number Master."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from benchmark import run_benchmarks
from generate_charts import ChartError, create_charts
from protocol import ProtocolError


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("harus lebih besar dari 0")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Master TCP untuk Distributed Prime Number Finder"
    )
    parser.add_argument("--worker-host", default="192.168.1.42")
    parser.add_argument("--worker-port", type=int, default=5000)
    parser.add_argument(
        "--sizes", nargs="+", type=positive_int,
        default=[100_000, 500_000, 1_000_000], metavar="N",
        help="satu atau beberapa batas atas (default: 100000 500000 1000000)",
    )
    parser.add_argument("--repeats", type=positive_int, default=5)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--from-summary", type=Path, metavar="CSV",
        help="buat grafik dari summary CSV lama tanpa menjalankan benchmark",
    )
    parser.add_argument(
        "--no-show", action="store_true",
        help="simpan grafik tanpa membuka jendela Matplotlib",
    )
    args = parser.parse_args()
    if not 1 <= args.worker_port <= 65535:
        parser.error("--worker-port harus dalam rentang 1..65535")
    if args.timeout <= 0:
        parser.error("--timeout harus lebih besar dari 0")
    if any(size < 3 for size in args.sizes):
        parser.error("setiap N pada --sizes harus minimal 3")
    return args


def main() -> int:
    args = parse_args()
    if args.from_summary is not None:
        try:
            create_charts(args.from_summary, show=not args.no_show)
        except ChartError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        return 0
    try:
        results, runs_path, summary_path = run_benchmarks(
            host=args.worker_host,
            port=args.worker_port,
            sizes=args.sizes,
            repeats=args.repeats,
            timeout=args.timeout,
            output_dir=args.output_dir,
        )
    except (RuntimeError, ProtocolError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Selesai: {len(results)} run terverifikasi")
    print(f"Detail: {runs_path}")
    print(f"Ringkasan: {summary_path}")
    try:
        create_charts(summary_path, show=not args.no_show)
    except ChartError as exc:
        # Benchmark remains valid even if an optional visualization dependency or
        # filesystem operation fails after its CSV files have been written.
        print(f"PERINGATAN: grafik tidak dapat dibuat: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

