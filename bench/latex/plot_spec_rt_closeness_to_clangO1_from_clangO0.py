#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ARCHITECTURES = ("x86_64", "aarch64")
BASELINE = "o1ir-clang"
TARGET = "o1-clang"
VARIANT_FILES = {
    BASELINE: "res-spec-raw-rt-o1ir-{arch}-clang",
    TARGET: "res-spec-raw-rt-o1-{arch}-clang",
    "tpde": "res-spec-raw-rt-o1ir-{arch}-tpde",
    "tpde-old": "res-spec-raw-rt-o1ir-{arch}-tpde-old",
}
COMPARE_COLUMNS = [TARGET, "tpde", "tpde-old"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot how close each SPEC variant gets to o1-clang runtime, using "
            "o1ir-clang as baseline."
        )
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default="charts",
        help="Directory containing SPEC raw runtime files (default: charts)",
    )
    parser.add_argument(
        "--output",
        default="charts/spec_rt_closeness_to_clangO1_from_clangO0_{arch}.png",
        help=(
            "Output plot path "
            "(default: charts/spec_rt_closeness_to_clangO1_from_clangO0_{arch}.png)"
        ),
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


def output_path_for_arch(path_text: str, arch: str) -> Path:
    normalized = path_text[1:] if path_text.startswith("@") else path_text
    if "{arch}" in normalized:
        return Path(normalized.format(arch=arch))
    for token in ARCHITECTURES:
        if token in normalized:
            return Path(normalized.replace(token, arch))
    base = Path(normalized)
    return base.with_name(f"{base.stem}_{arch}{base.suffix}")


def parse_raw_runtime_file(path: Path) -> dict[str, float]:
    rows: dict[str, float] = {}
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if ":" not in line:
                continue

            bench, value_text = line.split(":", 1)
            bench = bench.strip()
            value_text = value_text.strip()
            if not bench or not value_text:
                continue

            try:
                value = float(value_text)
            except ValueError:
                continue

            if value > 0:
                rows[bench] = value
    return rows


def benchmark_sort_key(name: str) -> tuple[int, str]:
    return (0, f"{int(name):08d}") if name.isdigit() else (1, name)


def geometric_mean(values: list[float]) -> float | None:
    if not values or any(v <= 0 for v in values):
        return None
    return float(np.exp(np.mean(np.log(values))))


def parse_rows(input_dir: Path, arch: str) -> tuple[list[str], dict[str, list[float]]]:
    runtime_tables = {
        name: parse_raw_runtime_file(input_dir / filename.format(arch=arch))
        for name, filename in VARIANT_FILES.items()
    }

    available = set.intersection(*(set(table) for table in runtime_tables.values()))
    benchmarks: list[str] = []
    closeness: dict[str, list[float]] = {name: [] for name in COMPARE_COLUMNS}
    runtimes: dict[str, list[float]] = {
        name: [] for name in [BASELINE, TARGET, *COMPARE_COLUMNS]
    }

    for bench in sorted(available, key=benchmark_sort_key):
        baseline = runtime_tables[BASELINE][bench]
        target = runtime_tables[TARGET][bench]
        gap = baseline - target
        if gap <= 0:
            continue

        row_values: dict[str, float] = {}
        valid = True
        for variant in COMPARE_COLUMNS:
            runtime = runtime_tables[variant][bench]
            value = ((baseline - runtime) / gap) * 100.0
            if not np.isfinite(value):
                valid = False
                break
            row_values[variant] = value

        if not valid:
            continue

        benchmarks.append(bench)
        runtimes[BASELINE].append(baseline)
        runtimes[TARGET].append(target)
        for variant in COMPARE_COLUMNS:
            closeness[variant].append(row_values[variant])
            runtimes[variant].append(runtime_tables[variant][bench])

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
    input_dir = normalize_input_path(args.input_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    outputs: list[Path] = []
    for arch in args.architectures:
        output_path = output_path_for_arch(args.output, arch)
        missing_files = [
            filename.format(arch=arch)
            for filename in VARIANT_FILES.values()
            if not (input_dir / filename.format(arch=arch)).exists()
        ]
        if missing_files:
            missing_text = ", ".join(sorted(missing_files))
            raise FileNotFoundError(
                f"Missing required input files for {arch} in {input_dir}: {missing_text}"
            )

        benchmarks, closeness = parse_rows(input_dir, arch)
        if not benchmarks:
            raise RuntimeError(
                "No valid SPEC rows with complete data for all variants and positive baseline-target gap"
            )

        x = np.arange(len(benchmarks))
        n_var = len(COMPARE_COLUMNS)
        width = min(0.8 / n_var, 0.3)

        plt.figure(figsize=(max(10, len(benchmarks) * 0.75), 6))

        for idx, variant in enumerate(COMPARE_COLUMNS):
            offset = (idx - (n_var - 1) / 2.0) * width
            plt.bar(x + offset, closeness[variant], width=width, label=variant)

        plt.axhline(0.0, color="gray", linestyle="--", linewidth=1)
        plt.axhline(
            100.0, color="black", linestyle="--", linewidth=1, label=f"{TARGET} target"
        )
        plt.ylabel(f"Closeness to {TARGET} runtime (%) from {BASELINE} baseline")
        plt.xlabel("SPEC benchmark")
        plt.title(
            f"SPEC runtime closeness to {TARGET} ({BASELINE} -> {TARGET} scale) ({arch})"
        )
        plt.xticks(x, benchmarks, rotation=45, ha="right")
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
