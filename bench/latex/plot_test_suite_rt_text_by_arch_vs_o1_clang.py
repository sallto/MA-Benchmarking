#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_ARCHITECTURES = ("x86_64", "aarch64")
BASELINE_VARIANT = "o1-clang"
VARIANTS = (
    ("o0-clang", 0),
    ("o1-clang", 1),
    ("tpde", 2),
    ("tpde-old", 3),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot test-suite runtime and text-size comparisons per architecture: "
            "relative to o1-clang (100% baseline) and absolute values."
        )
    )
    parser.add_argument(
        "--input-dir",
        default="bench-res",
        help="Directory containing res-test-suite-rt-text-* files (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default="charts",
        help="Directory to write plots (default: %(default)s)",
    )
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=list(DEFAULT_ARCHITECTURES),
        help="Architectures to process (default: x86_64 aarch64)",
    )
    return parser.parse_args()


def geomean(values: list[float]) -> float:
    if not values:
        return float("nan")
    return math.exp(sum(math.log(v) for v in values) / len(values))


def plot_grouped_bars(
    labels: list[str],
    series: dict[str, list[float]],
    ylabel: str,
    title: str,
    output_path: Path,
    *,
    yscale: str = "linear",
    hline: float | None = None,
) -> None:
    variants = [name for name, _ in VARIANTS if name in series]
    n_variants = len(variants)
    x = np.arange(len(labels))
    width = min(0.8 / max(n_variants, 1), 0.24)

    plt.figure(figsize=(max(12, len(labels) * 0.5), 6.5))
    for idx, variant in enumerate(variants):
        offset = (idx - (n_variants - 1) / 2.0) * width
        plt.bar(x + offset, series[variant], width=width, label=variant)

    if hline is not None:
        plt.axhline(hline, color="black", linestyle="--", linewidth=1)

    plt.yscale(yscale)
    plt.ylabel(ylabel)
    plt.xlabel("Test-suite benchmark")
    plt.title(title)
    plt.xticks(x, labels, rotation=75, ha="right")
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close()


def parse_input_file(
    path: Path,
) -> list[tuple[str, dict[str, float], dict[str, float]]]:
    rows: list[tuple[str, dict[str, float], dict[str, float]]] = []

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue

            cells = [cell.strip() for cell in row]
            if len(cells) < 9:
                continue

            name = ",".join(cells[:-8]).strip()
            if not name:
                continue

            numeric_cells = cells[-8:]
            try:
                numeric_values = [float(cell) for cell in numeric_cells]
            except ValueError:
                continue

            rt_values: dict[str, float] = {}
            text_values: dict[str, float] = {}
            for variant, idx in VARIANTS:
                rt_values[variant] = numeric_values[idx]
                text_values[variant] = numeric_values[idx + 4]

            rows.append((name, rt_values, text_values))

    return rows


def build_metric_series(
    bench_names: list[str],
    values_by_variant: dict[str, list[float]],
) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    baseline_values = values_by_variant[BASELINE_VARIANT]
    baseline_gm = geomean(baseline_values)

    abs_series: dict[str, list[float]] = {}
    rel_series: dict[str, list[float]] = {}

    for variant, _ in VARIANTS:
        vals = values_by_variant[variant]
        abs_gm = geomean(vals)
        abs_series[variant] = [abs_gm] + vals

        if variant == BASELINE_VARIANT:
            rel = [100.0 for _ in bench_names]
            rel_gm = 100.0
        else:
            rel = [(val / base) * 100.0 for val, base in zip(vals, baseline_values)]
            rel_gm = (abs_gm / baseline_gm) * 100.0

        rel_series[variant] = [rel_gm] + rel

    return abs_series, rel_series


def build_plots_for_arch(input_dir: Path, output_dir: Path, arch: str) -> list[Path]:
    input_path = input_dir / f"res-test-suite-rt-text-{arch}"
    if not input_path.exists():
        print(f"[warn] missing input for {arch}: {input_path}; skipping")
        return []

    parsed_rows = parse_input_file(input_path)
    if not parsed_rows:
        print(f"[warn] no valid rows in {input_path}; skipping")
        return []

    filtered_rows: list[tuple[str, dict[str, float], dict[str, float]]] = []
    for name, rt_values, text_values in parsed_rows:
        rt_ok = all(rt_values[variant] > 0 for variant, _ in VARIANTS)
        text_ok = all(text_values[variant] > 0 for variant, _ in VARIANTS)
        if rt_ok and text_ok:
            filtered_rows.append((name, rt_values, text_values))

    if not filtered_rows:
        print(f"[warn] no fully-positive rows for {arch}; skipping")
        return []

    bench_names = [name for name, _, _ in filtered_rows]
    rt_values_by_variant = {
        variant: [rt_values[variant] for _, rt_values, _ in filtered_rows]
        for variant, _ in VARIANTS
    }
    text_values_by_variant = {
        variant: [text_values[variant] for _, _, text_values in filtered_rows]
        for variant, _ in VARIANTS
    }

    rt_abs, rt_rel = build_metric_series(bench_names, rt_values_by_variant)
    text_abs, text_rel = build_metric_series(bench_names, text_values_by_variant)

    labels = ["geomean"] + bench_names
    outputs = [
        output_dir / f"testsuite_rt_relative_to_o1_clang_{arch}.png",
        output_dir / f"testsuite_rt_absolute_{arch}.png",
        output_dir / f"testsuite_text_relative_to_o1_clang_{arch}.png",
        output_dir / f"testsuite_text_absolute_{arch}.png",
    ]

    plot_grouped_bars(
        labels=labels,
        series=rt_rel,
        ylabel="Runtime (% of o1-clang, lower is better)",
        title=f"Test-suite runtime relative to o1-clang (o1-clang = 100%) ({arch})",
        output_path=outputs[0],
        yscale="linear",
        hline=100.0,
    )
    plot_grouped_bars(
        labels=labels,
        series=rt_abs,
        ylabel="Runtime (seconds, lower is better)",
        title=f"Test-suite runtime absolute values ({arch})",
        output_path=outputs[1],
        yscale="log",
    )
    plot_grouped_bars(
        labels=labels,
        series=text_rel,
        ylabel="Text size (% of o1-clang, lower is better)",
        title=f"Test-suite text size relative to o1-clang (o1-clang = 100%) ({arch})",
        output_path=outputs[2],
        yscale="linear",
        hline=100.0,
    )
    plot_grouped_bars(
        labels=labels,
        series=text_abs,
        ylabel="Text size (bytes, lower is better)",
        title=f"Test-suite text size absolute values ({arch})",
        output_path=outputs[3],
        yscale="log",
    )

    print(
        f"[ok] {arch}: {len(bench_names)} benchmarks, {len(VARIANTS)} variants "
        f"-> {', '.join(path.name for path in outputs)}"
    )
    return outputs


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    output_paths: list[Path] = []
    for arch in args.architectures:
        output_paths.extend(build_plots_for_arch(input_dir, output_dir, arch))

    if not output_paths:
        raise RuntimeError("No plots were generated.")
    print(f"Done. Wrote {len(output_paths)} plot(s).")


if __name__ == "__main__":
    main()
