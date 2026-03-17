#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_ARCHITECTURES = ("x86_64", "aarch64")
BASELINE_VARIANT = "o1-clang"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot SPEC runtime comparisons per architecture: relative to o1-clang "
            "(100%% baseline) and absolute times."
        )
    )
    parser.add_argument(
        "--input-dir",
        default="bench-res",
        help="Directory containing res-spec-raw-rt-* files (default: %(default)s)",
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


def parse_variant_name(path: Path, arch: str) -> str | None:
    prefix = "res-spec-raw-rt-"
    name = path.name
    if not name.startswith(prefix):
        return None
    body = name[len(prefix) :]
    marker = f"-{arch}-"
    if marker not in body:
        return None
    opt, backend = body.split(marker, 1)
    return f"{opt}-{backend}"


def parse_times(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        bench, raw_value = line.split(":", 1)
        bench = bench.strip()
        raw_value = raw_value.strip()
        if not bench or not raw_value:
            continue
        try:
            value = float(raw_value)
        except ValueError:
            continue
        if value <= 0:
            continue
        values[bench] = value
    return values


def geomean(values: list[float]) -> float:
    if not values:
        return float("nan")
    return math.exp(sum(math.log(v) for v in values) / len(values))


def variant_sort_key(name: str) -> tuple[int, str]:
    order = {
        "o1-clang": 0,
        "o1ir-clang": 1,
        "o1ir-tpde": 2,
        "o1ir-tpde-old": 3,
    }
    return (order.get(name, 99), name)


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
    variants = sorted(series.keys(), key=variant_sort_key)
    n_variants = len(variants)
    x = np.arange(len(labels))
    width = min(0.8 / max(n_variants, 1), 0.24)

    plt.figure(figsize=(max(12, len(labels) * 0.55), 6.5))
    for idx, variant in enumerate(variants):
        offset = (idx - (n_variants - 1) / 2.0) * width
        plt.bar(x + offset, series[variant], width=width, label=variant)

    if hline is not None:
        plt.axhline(hline, color="black", linestyle="--", linewidth=1)

    plt.yscale(yscale)
    plt.ylabel(ylabel)
    plt.xlabel("SPEC benchmark")
    plt.title(title)
    plt.xticks(x, labels, rotation=75, ha="right")
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close()


def build_plots_for_arch(
    input_dir: Path, output_dir: Path, arch: str
) -> tuple[Path, Path] | None:
    paths = sorted(input_dir.glob(f"res-spec-raw-rt-*-{arch}-*"))
    if not paths:
        print(f"[warn] no input files for {arch} in {input_dir}; skipping")
        return None

    times_by_variant: dict[str, dict[str, float]] = {}
    for path in paths:
        variant = parse_variant_name(path, arch)
        if not variant:
            continue
        parsed = parse_times(path)
        if parsed:
            times_by_variant[variant] = parsed
    variants = sorted(times_by_variant.keys(), key=variant_sort_key)
    common_benches: set[str] = set(times_by_variant[variants[0]].keys())
    for variant in variants[1:]:
        common_benches &= set(times_by_variant[variant].keys())


    bench_labels = sorted(common_benches, key=int)
    if BASELINE_VARIANT not in times_by_variant:
        print(f"[warn] missing baseline '{BASELINE_VARIANT}' for {arch}; skipping")


    if not common_benches:
        print(f"[warn] no common benchmarks across variants for {arch}; skipping")
        return None
    all_labels = ["geomean"] + bench_labels

    abs_series: dict[str, list[float]] = {}
    rel_series: dict[str, list[float]] = {}
    if BASELINE_VARIANT not in times_by_variant:
        baseline_values = None 
        baseline_geomean = None
    else:
        baseline_values = [times_by_variant[BASELINE_VARIANT][b] for b in bench_labels]
        baseline_geomean = geomean(baseline_values)

    for variant in variants:
        absolute_vals = [times_by_variant[variant][b] for b in bench_labels]
        abs_gm = geomean(absolute_vals)
        abs_series[variant] = [abs_gm] + absolute_vals
        if BASELINE_VARIANT not in times_by_variant:
            continue
        if variant == BASELINE_VARIANT:
            rel_vals = [100.0 for _ in bench_labels]
            rel_gm = 100.0
        else:
            rel_vals = [
                (times_by_variant[variant][b] / times_by_variant[BASELINE_VARIANT][b])
                * 100.0
                for b in bench_labels
            ]
            rel_gm = (abs_gm / baseline_geomean) * 100.0
        rel_series[variant] = [rel_gm] + rel_vals

    rel_out = output_dir / f"spec_rt_relative_to_o1_clang_{arch}.png"
    abs_out = output_dir / f"spec_rt_absolute_{arch}.png"
    if BASELINE_VARIANT in times_by_variant:
        plot_grouped_bars(
            labels=all_labels,
            series=rel_series,
            ylabel="Runtime (% of o1-clang, lower is better)",
            title=f"SPEC RT relative to o1-clang (o1-clang = 100%) ({arch})",
            output_path=rel_out,
            yscale="linear",
            hline=100.0,
        )
    plot_grouped_bars(
        labels=all_labels,
        series=abs_series,
        ylabel="Runtime (seconds, lower is better)",
        title=f"SPEC RT absolute runtimes ({arch})",
        output_path=abs_out,
        yscale="log",
    )

    print(
        f"[ok] {arch}: {len(bench_labels)} benchmarks, "
        f"{len(variants)} variants -> {rel_out.name}, {abs_out.name}"
    )
    return rel_out, abs_out


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    outputs: list[Path] = []
    for arch in args.architectures:
        result = build_plots_for_arch(input_dir, output_dir, arch)
        if result is None:
            continue
        outputs.extend(result)

    if not outputs:
        raise RuntimeError("No plots were generated.")
    print(f"Done. Wrote {len(outputs)} plot(s).")


if __name__ == "__main__":
    main()
