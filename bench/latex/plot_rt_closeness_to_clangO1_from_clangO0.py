#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ARCHITECTURES = ("x86_64", "aarch64")
BASELINE = "clangO0"
TARGET = "clangO1"
COMPARE_COLUMNS = ["clangO1", "tpde", "tpde-old"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot how close each variant gets to clangO1 runtime, using clangO0 as baseline."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="charts/res-test-suite-rt-text-{arch}",
        help="Input CSV file (default: charts/res-test-suite-rt-text-{arch})",
    )
    parser.add_argument(
        "--output",
        default="charts/rt_closeness_to_clangO1_from_clangO0_{arch}.png",
        help="Output plot path (default: charts/rt_closeness_to_clangO1_from_clangO0_{arch}.png)",
    )
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=list(ARCHITECTURES),
        help="Architectures to plot (default: x86_64 aarch64)",
    )
    return parser.parse_args()


def normalize_input_path(path_text: str) -> Path:
    return Path(path_text[1:] if path_text.startswith("@") else path_text)


def path_for_arch(path_text: str, arch: str) -> Path:
    normalized = path_text[1:] if path_text.startswith("@") else path_text
    if "{arch}" in normalized:
        return Path(normalized.format(arch=arch))
    for token in ARCHITECTURES:
        if token in normalized:
            return Path(normalized.replace(token, arch))
    return Path(normalized)


def output_path_for_arch(path_text: str, arch: str) -> Path:
    base = path_for_arch(path_text, arch)
    if "{arch}" in path_text:
        return base
    return base.with_name(f"{base.stem}_{arch}{base.suffix}")


def geometric_mean(values: list[float]) -> float | None:
    if not values or any(v <= 0 for v in values):
        return None
    return float(np.exp(np.mean(np.log(values))))


def parse_rows(path: Path) -> tuple[list[str], dict[str, list[float]]]:
    benchmarks: list[str] = []
    closeness: dict[str, list[float]] = {name: [] for name in COMPARE_COLUMNS}
    runtimes: dict[str, list[float]] = {
        name: [] for name in [BASELINE, TARGET, *COMPARE_COLUMNS]
    }

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(
            f,
            fieldnames=[
                "benchname",
                "clangO0",
                "clangO1",
                "tpde",
                "tpde-old",
                "size_clangO0",
                "size_clangO1",
                "size_tpde",
                "size_tpde-old",
            ],
        )

        for row in reader:
            bench = (row.get("benchname") or "").strip()
            if not bench:
                continue

            try:
                baseline = float(row[BASELINE])
                target = float(row[TARGET])
            except (TypeError, ValueError):
                continue

            gap = baseline - target
            if gap <= 0:
                continue

            values: dict[str, float] = {}
            row_runtimes: dict[str, float] = {}
            valid = True
            for variant in COMPARE_COLUMNS:
                try:
                    runtime = float(row[variant])
                except (TypeError, ValueError):
                    valid = False
                    break
                # 0% means equal to clangO0, 100% means equal to clangO1.
                values[variant] = ((baseline - runtime) / gap) * 100.0
                row_runtimes[variant] = runtime

            if not valid:
                continue

            benchmarks.append(bench)
            runtimes[BASELINE].append(baseline)
            runtimes[TARGET].append(target)
            for variant in COMPARE_COLUMNS:
                closeness[variant].append(values[variant])
                runtimes[variant].append(row_runtimes[variant])

    baseline_gm = geometric_mean(runtimes[BASELINE])
    target_gm = geometric_mean(runtimes[TARGET])
    if baseline_gm is not None and target_gm is not None:
        gap_gm = baseline_gm - target_gm
        if gap_gm > 0:
            geomean_values: dict[str, float] = {}
            for variant in COMPARE_COLUMNS:
                runtime_gm = geometric_mean(runtimes[variant])
                if runtime_gm is None:
                    geomean_values = {}
                    break
                geomean_values[variant] = ((baseline_gm - runtime_gm) / gap_gm) * 100.0

            if geomean_values:
                benchmarks.insert(0, "geomean")
                for variant in COMPARE_COLUMNS:
                    closeness[variant].insert(0, geomean_values[variant])

    return benchmarks, closeness


def main() -> None:
    args = parse_args()
    outputs: list[Path] = []
    for arch in args.architectures:
        input_path = path_for_arch(args.input, arch)
        output_path = output_path_for_arch(args.output, arch)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found for {arch}: {input_path}")

        benchmarks, closeness = parse_rows(input_path)
        if not benchmarks:
            raise RuntimeError(f"No valid rows found in {input_path}")

        x = np.arange(len(benchmarks))
        n_var = len(COMPARE_COLUMNS)
        width = min(0.8 / n_var, 0.3)

        plt.figure(figsize=(max(12, len(benchmarks) * 0.45), 6))

        for idx, variant in enumerate(COMPARE_COLUMNS):
            offset = (idx - (n_var - 1) / 2.0) * width
            plt.bar(x + offset, closeness[variant], width=width, label=variant)

        plt.axhline(0.0, color="gray", linestyle="--", linewidth=1)
        plt.axhline(
            100.0, color="black", linestyle="--", linewidth=1, label="clangO1 target"
        )
        plt.ylabel("Closeness to clangO1 runtime (%) from clangO0 baseline")
        plt.xlabel("Benchmark")
        plt.title(f"Runtime closeness to clangO1 (clangO0 -> clangO1 scale) ({arch})")
        plt.xticks(x, benchmarks, rotation=75, ha="right")
        plt.legend()
        plt.tight_layout()

        if output_path.parent and output_path.parent != Path("."):
            output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=220)
        plt.close()
        outputs.append(output_path)

        print(f"Wrote {output_path} for {len(benchmarks)} benchmarks")

    print(f"Done. Wrote {len(outputs)} plot(s).")


if __name__ == "__main__":
    main()
