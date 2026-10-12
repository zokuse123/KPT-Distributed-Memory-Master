"""Benchmark orchestration for the two-PC distributed prime finder."""

from __future__ import annotations

import csv
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from prime_utils import count_primes
from protocol import make_task, receive_message, send_message, validate_result


@dataclass
class RunResult:
    size: int
    data_count: int
    repetition: int
    task_id: str
    pc1_start: int
    pc1_end: int
    pc2_start: int
    pc2_end: int
    pc1_prime_count: int
    pc2_prime_count: int
    total_prime_count: int
    sequential_prime_count: int
    sequential_seconds: float
    distributed_seconds: float
    worker_compute_seconds: float
    speedup: float
    efficiency_percent: float
    verified: bool


def format_run_result(result: RunResult) -> str:
    """Format all required per-run information without changing measurement data."""
    pc1_data_count = result.pc1_end - result.pc1_start + 1
    pc2_data_count = result.pc2_end - result.pc2_start + 1
    verification = "SESUAI" if result.verified else "TIDAK SESUAI"
    return "\n".join(
        (
            f"--- Hasil {result.task_id} | N={result.size:,} | "
            f"Repetisi {result.repetition} ---",
            f"Jumlah data total : {result.data_count:,} bilangan "
            f"(rentang 2..{result.size:,}, inklusif)",
            f"PC 1 (Master)     : rentang {result.pc1_start:,}..{result.pc1_end:,} "
            f"| beban {pc1_data_count:,} data | hasil {result.pc1_prime_count:,} prima",
            f"PC 2 (Worker)     : rentang {result.pc2_start:,}..{result.pc2_end:,} "
            f"| beban {pc2_data_count:,} data | hasil {result.pc2_prime_count:,} prima",
            f"Hasil gabungan    : {result.total_prime_count:,} prima",
            f"Hasil sequential  : {result.sequential_prime_count:,} prima "
            f"| verifikasi {verification}",
            f"Waktu sequential  : {result.sequential_seconds:.6f} detik",
            f"Waktu distributed : {result.distributed_seconds:.6f} detik "
            f"(compute Worker {result.worker_compute_seconds:.6f} detik)",
            f"Speedup            : {result.speedup:.3f}x",
            f"Efficiency (2 PC)  : {result.efficiency_percent:.2f}%",
        )
    )


def split_range(n: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Split inclusive [2, n] at its numeric midpoint, without gaps."""
    if n < 3:
        raise ValueError("N must be at least 3 so both PCs receive a non-empty range")
    midpoint = (2 + n) // 2
    return (2, midpoint), (midpoint + 1, n)


def run_one(
    sock: socket.socket, *, size: int, repetition: int, task_id: str
) -> RunResult:
    """Run one sequential baseline and one real distributed measurement."""
    pc1_range, pc2_range = split_range(size)

    sequential_started = time.perf_counter()
    sequential_count = count_primes(2, size)
    sequential_seconds = time.perf_counter() - sequential_started

    # The timer intentionally includes TASK/RESULT network I/O, both computations,
    # and result validation/combination. The already-established TCP handshake is
    # outside each per-run measurement so one connection can serve many TASKs.
    distributed_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="master-prime") as pool:
        local_future = pool.submit(count_primes, *pc1_range)
        send_message(sock, make_task(task_id, *pc2_range))
        response = receive_message(sock)
        remote_count, worker_seconds = validate_result(
            response, task_id=task_id, start=pc2_range[0], end=pc2_range[1]
        )
        local_count = local_future.result()
    total_count = local_count + remote_count
    distributed_seconds = time.perf_counter() - distributed_started

    if total_count != sequential_count:
        raise RuntimeError(
            f"verification failed for N={size}: sequential={sequential_count}, "
            f"distributed={total_count}"
        )
    speedup = sequential_seconds / distributed_seconds
    return RunResult(
        size=size,
        data_count=size - 1,
        repetition=repetition,
        task_id=task_id,
        pc1_start=pc1_range[0],
        pc1_end=pc1_range[1],
        pc2_start=pc2_range[0],
        pc2_end=pc2_range[1],
        pc1_prime_count=local_count,
        pc2_prime_count=remote_count,
        total_prime_count=total_count,
        sequential_prime_count=sequential_count,
        sequential_seconds=sequential_seconds,
        distributed_seconds=distributed_seconds,
        worker_compute_seconds=worker_seconds,
        speedup=speedup,
        efficiency_percent=(speedup / 2.0) * 100.0,
        verified=True,
    )


def _write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_results(results: list[RunResult], output_dir: Path) -> tuple[Path, Path]:
    """Write detailed runs and per-size mean summaries to timestamped CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    runs_path = output_dir / f"runs-{stamp}.csv"
    summary_path = output_dir / f"summary-{stamp}.csv"
    run_rows = [asdict(result) for result in results]
    _write_csv(runs_path, run_rows, list(RunResult.__dataclass_fields__))

    summary_rows: list[dict[str, object]] = []
    for size in sorted({result.size for result in results}):
        group = [result for result in results if result.size == size]
        summary_rows.append(
            {
                "size": size,
                "data_count": size - 1,
                "runs": len(group),
                "prime_count": group[0].total_prime_count,
                "mean_sequential_seconds": statistics.fmean(
                    result.sequential_seconds for result in group
                ),
                "mean_distributed_seconds": statistics.fmean(
                    result.distributed_seconds for result in group
                ),
                "mean_worker_compute_seconds": statistics.fmean(
                    result.worker_compute_seconds for result in group
                ),
                "mean_speedup": statistics.fmean(result.speedup for result in group),
                "mean_efficiency_percent": statistics.fmean(
                    result.efficiency_percent for result in group
                ),
                "all_verified": all(result.verified for result in group),
            }
        )
    summary_fields = list(summary_rows[0]) if summary_rows else []
    if summary_fields:
        _write_csv(summary_path, summary_rows, summary_fields)
    return runs_path, summary_path


def run_benchmarks(
    *, host: str, port: int, sizes: list[int], repeats: int, timeout: float,
    output_dir: Path
) -> tuple[list[RunResult], Path, Path]:
    """Connect once to the Worker and execute all configured TASK messages."""
    results: list[RunResult] = []
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            print(f"Terhubung ke Worker {host}:{port}")
            sequence = 0
            for size in sizes:
                for repetition in range(1, repeats + 1):
                    sequence += 1
                    task_id = f"run-{sequence:03d}"
                    print(f"Menjalankan {task_id}: N={size}, repetisi={repetition}")
                    result = run_one(
                        sock, size=size, repetition=repetition, task_id=task_id
                    )
                    results.append(result)
                    print(format_run_result(result))
    except (ConnectionError, TimeoutError, socket.timeout, OSError) as exc:
        raise RuntimeError(
            f"gagal berkomunikasi dengan Worker {host}:{port}: {exc}. "
            "Tidak ada fallback komputasi lokal."
        ) from exc

    runs_path, summary_path = save_results(results, output_dir)
    return results, runs_path, summary_path

