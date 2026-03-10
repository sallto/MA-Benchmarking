#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


TOOL_COLUMNS = ["clangO1", "tpde", "tpde-old"]
BASELINE_COLUMN = "clangO0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read runtime benchmark CSV and plot speedup relative to clangO1 for each benchmark."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="charts/res-test-suite-rt-text-x86_64",
        help="Input CSV file (default: charts/res-test-suite-rt-text-x86_64)",
    )
    parser.add_argument(
        "--output",
        default="charts/rt_speedup_vs_clangO1.png",
        help="Output plot path (default: charts/rt_speedup_vs_clangO1.png)",
    )
    return parser.parse_args()


def normalize_input_path(path_text: str) -> Path:
    # Allow CLI-style @file shorthand.
    normalized = path_text[1:] if path_text.startswith("@") else path_text
    return Path(normalized)


def parse_rows(path: Path) -> tuple[list[str], dict[str, list[float]]]:
    benchmarks: list[str] = []
    normalized: dict[str, list[float]] = {name: [] for name in TOOL_COLUMNS}

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
                baseline = float(row[BASELINE_COLUMN])
            except (TypeError, ValueError):
                continue

            if baseline <= 0:
                continue

            ratios: dict[str, float] = {}
            valid = True
            for tool in TOOL_COLUMNS:
                try:
                    value = float(row[tool])
                except (TypeError, ValueError):
                    valid = False
                    break
                if value <= 0:
                    valid = False
                    break
                ratios[tool] = baseline / value

            if not valid:
                continue

            benchmarks.append(bench)
            for tool in TOOL_COLUMNS:
                normalized[tool].append(ratios[tool])

    return benchmarks, normalized


def main() -> None:
    args = parse_args()
    input_path = normalize_input_path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    benchmarks, normalized = parse_rows(input_path)
    if not benchmarks:
        raise RuntimeError(f"No valid rows found in {input_path}")

    x = np.arange(len(benchmarks))
    n_tools = len(TOOL_COLUMNS)
    width = min(0.8 / n_tools, 0.3)

    plt.figure(figsize=(max(12, len(benchmarks) * 0.45), 6))

    for idx, tool in enumerate(TOOL_COLUMNS):
        offset = (idx - (n_tools - 1) / 2.0) * width
        plt.bar(x + offset, normalized[tool], width=width, label=tool)

    plt.axhline(1.0, color="black", linestyle="--", linewidth=1, label="clangO0 = 1")
    plt.yscale("log")
    plt.ylabel("Speedup vs clangO0 (higher is better)")
    plt.xlabel("Benchmark")
    plt.title("Runtime speedup per benchmark (relative to clangO0)")
    plt.xticks(x, benchmarks, rotation=75, ha="right")
    plt.legend()
    plt.tight_layout()

    if output_path.parent and output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close()

    print(f"Wrote {output_path} for {len(benchmarks)} benchmarks")


if __name__ == "__main__":
    main()
