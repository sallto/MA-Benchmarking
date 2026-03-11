#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ARCHITECTURES = ("x86_64", "aarch64")
STAGES = ["clangO0", "tpde-old", "tpde", "clangO1"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot runtime speedup progression as steps: clangO0 -> tpde-old -> tpde -> clangO1."
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
        default="charts/rt_speedup_steps_clangO0_tpdeold_tpde_clangO1_{arch}.png",
        help=(
            "Output plot path "
            "(default: charts/rt_speedup_steps_clangO0_tpdeold_tpde_clangO1_{arch}.png)"
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


def parse_rows(path: Path) -> tuple[list[str], np.ndarray]:
    benchmarks: list[str] = []
    rows: list[list[float]] = []

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
                stage_runtimes = [float(row[s]) for s in STAGES]
            except (TypeError, ValueError):
                continue

            if any(v <= 0 for v in stage_runtimes):
                continue

            baseline = stage_runtimes[0]
            stage_speedups = [baseline / runtime for runtime in stage_runtimes]

            benchmarks.append(bench)
            rows.append(stage_speedups)

    if not rows:
        return benchmarks, np.empty((0, len(STAGES)))

    return benchmarks, np.array(rows, dtype=float)


def main() -> None:
    args = parse_args()
    outputs: list[Path] = []
    for arch in args.architectures:
        input_path = path_for_arch(args.input, arch)
        output_path = output_path_for_arch(args.output, arch)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found for {arch}: {input_path}")

        benchmarks, speedups = parse_rows(input_path)
        if speedups.size == 0:
            raise RuntimeError(f"No valid rows found in {input_path}")

        x = np.arange(len(STAGES))

        plt.figure(figsize=(10, 6))

        for i, _bench in enumerate(benchmarks):
            plt.step(x, speedups[i], where="mid", alpha=0.25, linewidth=1)

        geomean = np.exp(np.mean(np.log(speedups), axis=0))
        plt.step(
            x,
            geomean,
            where="mid",
            color="black",
            linewidth=2.5,
            label="geomean",
        )
        plt.plot(x, geomean, "o", color="black", markersize=5)

        plt.axhline(1.0, color="gray", linestyle="--", linewidth=1)
        plt.xticks(x, STAGES)
        plt.yscale("log")
        plt.ylabel("Speedup vs clangO0 (higher is better)")
        plt.xlabel("Compilation variant step")
        plt.title(
            f"Runtime speedup steps: clangO0 -> tpde-old -> tpde -> clangO1 ({arch})"
        )
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
