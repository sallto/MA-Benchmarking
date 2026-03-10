#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PREFERRED_VARIANT_ORDER = ["tpde_old", "tpde", "clang_o0", "clang_o1"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read benchmark compile-time results and plot speedups relative to clang_o1."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="res-test-suite-ct-x86_64",
        help="Input results file (default: res-test-suite-ct-x86_64)",
    )
    parser.add_argument(
        "--metric",
        default="codegen",
        help="Metric/pass to compare (default: codegen)",
    )
    parser.add_argument(
        "--baseline",
        default="clang_o1",
        help="Baseline variant with speedup fixed to 1 (default: clang_o1)",
    )
    parser.add_argument(
        "--output",
        default="compiletime_speedup_vs_clang_o1.png",
        help="Output plot path (default: compiletime_speedup_vs_clang_o1.png)",
    )
    return parser.parse_args()


def parse_results(path: Path, metric: str) -> dict[str, dict[str, float]]:
    per_benchmark: dict[str, dict[str, float]] = defaultdict(dict)

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("WARNING:"):
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            benchmark, pass_name, variant, value_str = parts[:4]
            if pass_name != metric:
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            per_benchmark[benchmark][variant] = value

    return per_benchmark


def order_variants(variants: list[str], baseline: str) -> list[str]:
    preferred = [v for v in PREFERRED_VARIANT_ORDER if v in variants and v != baseline]
    remaining = sorted(v for v in variants if v not in preferred and v != baseline)
    return preferred + remaining


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    per_benchmark = parse_results(input_path, args.metric)
    if not per_benchmark:
        raise RuntimeError(f"No data found for metric '{args.metric}' in {input_path}")

    filtered: dict[str, dict[str, float]] = {}
    for benchmark, variant_times in sorted(per_benchmark.items()):
        baseline_time = variant_times.get(args.baseline, 0.0)
        if baseline_time > 0:
            filtered[benchmark] = variant_times

    if not filtered:
        raise RuntimeError(
            f"No benchmark has a positive baseline '{args.baseline}' time for metric "
            f"'{args.metric}'"
        )

    all_variants = sorted({v for m in filtered.values() for v in m.keys()})
    compare_variants = order_variants(all_variants, args.baseline)
    if not compare_variants:
        raise RuntimeError("No non-baseline variants found to compare")

    benchmarks = list(filtered.keys())
    all_labels = ["geomean"] + benchmarks
    n_bench = len(all_labels)
    n_var = len(compare_variants)

    x = np.arange(n_bench)
    width = min(0.8 / max(1, n_var), 0.25)

    plt.figure(figsize=(max(12, n_bench * 0.45), 6))

    for i, variant in enumerate(compare_variants):
        speedups = []
        valid_speedups = []
        for benchmark in benchmarks:
            baseline_time = filtered[benchmark][args.baseline]
            variant_time = filtered[benchmark].get(variant, np.nan)
            if variant_time and variant_time > 0:
                speedup = baseline_time / variant_time
                speedups.append(speedup)
                valid_speedups.append(speedup)
            else:
                speedups.append(np.nan)

        geomean = np.nan
        if valid_speedups:
            geomean = float(np.exp(np.mean(np.log(valid_speedups))))
        speedups = [geomean] + speedups

        offset = (i - (n_var - 1) / 2.0) * width
        plt.bar(x + offset, speedups, width=width, label=variant)

    plt.axhline(1.0, color="black", linestyle="--", linewidth=1, label=args.baseline)
    plt.ylabel(f"Compile-time speedup vs {args.baseline} (higher is better)")
    plt.xlabel("Benchmark")
    plt.title(f"{args.metric} speedup per benchmark ({args.baseline} = 1)")
    plt.xticks(x, all_labels, rotation=75, ha="right")
    plt.yscale("log")
    plt.legend()
    plt.tight_layout()

    if output_path.parent and output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close()

    print(
        f"Wrote {output_path} for {n_bench} benchmarks and "
        f"{len(compare_variants)} variants (baseline: {args.baseline})"
    )


if __name__ == "__main__":
    main()
