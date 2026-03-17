#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ARCHITECTURES = ("x86_64", "aarch64")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate compile-time comparison plots for test-suite and SPEC data, "
            "including geomean bars."
        )
    )
    parser.add_argument(
        "--input-dir",
        default="bench-res",
        help="Directory containing res-*-ct-* files (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default="charts",
        help="Directory to write plots into (default: %(default)s)",
    )
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=list(ARCHITECTURES),
        help="Architectures to process (default: x86_64 aarch64)",
    )
    return parser.parse_args()


def geomean(values: list[float]) -> float:
    valid = [v for v in values if v > 0]
    if not valid:
        return float("nan")
    return math.exp(sum(math.log(v) for v in valid) / len(valid))


def parse_ct_file(
    path: Path,
) -> tuple[list[str], dict[str, dict[tuple[str, str], float]]]:
    bench_order: list[str] = []
    values: dict[str, dict[tuple[str, str], float]] = {}

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("WARNING:") or line.endswith(":"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue

        bench, metric, variant, value_text = parts[:4]
        try:
            value = float(value_text)
        except ValueError:
            continue

        if bench not in values:
            values[bench] = {}
            bench_order.append(bench)
        values[bench][(metric, variant)] = value

    return bench_order, values


def common_benches(
    bench_order: list[str],
    values: dict[str, dict[tuple[str, str], float]],
    required_keys: list[tuple[str, str]],
) -> list[str]:
    return [
        bench
        for bench in bench_order
        if all(key in values.get(bench, {}) for key in required_keys)
    ]


def with_geomean(series: list[float]) -> list[float]:
    return [geomean(series)] + series


def sort_bench_labels(labels: list[str]) -> list[str]:
    if labels and all(label.isdigit() for label in labels):
        return sorted(labels, key=int)
    return labels


def plot_grouped(
    labels: list[str],
    series: dict[str, list[float]],
    title: str,
    ylabel: str,
    output_path: Path,
    *,
    yscale: str = "log",
) -> None:
    names = list(series.keys())
    x = np.arange(len(labels))
    width = min(0.8 / max(len(names), 1), 0.24)

    plt.figure(figsize=(max(12, len(labels) * 0.5), 6.5))
    for idx, name in enumerate(names):
        offset = (idx - (len(names) - 1) / 2.0) * width
        plt.bar(x + offset, series[name], width=width, label=name)

    plt.yscale(yscale)
    plt.ylabel(ylabel)
    plt.xlabel("Benchmark")
    plt.title(title)
    plt.xticks(x, labels, rotation=75, ha="right")
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close()


def plot_analysis_breakdown(
    labels: list[str],
    old_analysis: list[float],
    tpde_pl: list[float],
    tpde_spill: list[float],
    tpde_other: list[float],
    title: str,
    output_path: Path,
) -> None:
    x = np.arange(len(labels))
    width = 0.36

    old_vals = with_geomean(old_analysis)
    pl_vals = with_geomean(tpde_pl)
    spill_vals = with_geomean(tpde_spill)
    other_vals = with_geomean(tpde_other)

    plt.figure(figsize=(max(12, len(labels) * 0.5), 6.5))
    plt.bar(x - width / 2.0, old_vals, width=width, label="tpde_old analysis")

    plt.bar(x + width / 2.0, pl_vals, width=width, label="tpde analysis: tpde_pl")
    plt.bar(
        x + width / 2.0,
        spill_vals,
        width=width,
        bottom=pl_vals,
        label="tpde analysis: tpde_spill",
    )
    plt.bar(
        x + width / 2.0,
        other_vals,
        width=width,
        bottom=(np.array(pl_vals) + np.array(spill_vals)),
        label="tpde analysis: other",
    )

    plt.yscale("log")
    plt.ylabel("Compile time")
    plt.xlabel("Benchmark")
    plt.title(title)
    plt.xticks(x, labels, rotation=75, ha="right")
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close()


def emit_missing(prefix: str, arch: str, message: str) -> None:
    print(f"[warn] {prefix} ({arch}): {message}")


def build_testsuite_plots(input_dir: Path, output_dir: Path, arch: str) -> list[Path]:
    outputs: list[Path] = []
    path = input_dir / f"res-test-suite-ct-{arch}"
    if not path.exists():
        emit_missing("testsuite", arch, f"missing file {path}")
        return outputs

    bench_order, values = parse_ct_file(path)
    benches = sort_bench_labels(bench_order)

    codegen_keys = [
        ("codegen", "tpde_old"),
        ("codegen", "tpde"),
        ("codegen", "clang_o0"),
        ("codegen", "clang_o1"),
    ]
    codegen_benches = common_benches(benches, values, codegen_keys)
    if codegen_benches:
        labels = ["geomean"] + codegen_benches
        series = {
            "tpde_old codegen": with_geomean(
                [values[b][("codegen", "tpde_old")] for b in codegen_benches]
            ),
            "tpde codegen": with_geomean(
                [values[b][("codegen", "tpde")] for b in codegen_benches]
            ),
            "clang_O0 codegen": with_geomean(
                [values[b][("codegen", "clang_o0")] for b in codegen_benches]
            ),
            "clang_O1 codegen": with_geomean(
                [values[b][("codegen", "clang_o1")] for b in codegen_benches]
            ),
        }
        out = output_dir / f"ct_codegen_testsuite_{arch}.png"
        plot_grouped(
            labels,
            series,
            f"Test-suite compile time: codegen comparison ({arch})",
            "Compile time",
            out,
            yscale="log",
        )
        outputs.append(out)
    else:
        emit_missing("testsuite", arch, "no common benchmarks for codegen comparison")

    tpde_cg_keys = [("tpde_cg", "tpde"), ("tpde_cg", "tpde_old")]
    tpde_cg_benches = common_benches(benches, values, tpde_cg_keys)
    if tpde_cg_benches:
        labels = ["geomean"] + tpde_cg_benches
        series = {
            "tpde_cg tpde_old": with_geomean(
                [values[b][("tpde_cg", "tpde_old")] for b in tpde_cg_benches]
            ),
            "tpde_cg tpde": with_geomean(
                [values[b][("tpde_cg", "tpde")] for b in tpde_cg_benches]
            ),
        }
        out = output_dir / f"ct_tpde_cg_testsuite_{arch}.png"
        plot_grouped(
            labels,
            series,
            f"Test-suite compile time: tpde_cg tpde vs tpde_old ({arch})",
            "Compile time",
            out,
            yscale="log",
        )
        outputs.append(out)
    else:
        emit_missing("testsuite", arch, "no common benchmarks for tpde_cg comparison")

    analysis_keys = [
        ("analysis", "tpde_old"),
        ("analysis", "tpde"),
        ("tpde_pl", "tpde"),
        ("tpde_spill", "tpde"),
    ]
    analysis_benches = common_benches(benches, values, analysis_keys)
    if analysis_benches:
        old_analysis = [values[b][("analysis", "tpde_old")] for b in analysis_benches]
        tpde_pl = [values[b][("tpde_pl", "tpde")] for b in analysis_benches]
        tpde_spill = [values[b][("tpde_spill", "tpde")] for b in analysis_benches]
        tpde_analysis = [values[b][("analysis", "tpde")] for b in analysis_benches]
        tpde_other = [
            max(total - pl - spill, 1e-9)
            for total, pl, spill in zip(tpde_analysis, tpde_pl, tpde_spill)
        ]

        labels = ["geomean"] + analysis_benches
        out = output_dir / f"ct_analysis_breakdown_testsuite_{arch}.png"
        plot_analysis_breakdown(
            labels,
            old_analysis,
            tpde_pl,
            tpde_spill,
            tpde_other,
            f"Test-suite compile time: analysis tpde vs tpde_old ({arch})",
            out,
        )
        outputs.append(out)
    else:
        emit_missing(
            "testsuite",
            arch,
            "no common benchmarks for analysis breakdown comparison",
        )

    delta_keys = [
        ("codegen", "tpde"),
        ("codegen", "tpde_old"),
        ("LLVM_RA", "clang_o1"),
    ]
    delta_benches = common_benches(benches, values, delta_keys)
    if delta_benches:
        delta = [
            values[b][("codegen", "tpde")] - values[b][("codegen", "tpde_old")]
            for b in delta_benches
        ]
        llvm_ra = [values[b][("LLVM_RA", "clang_o1")] for b in delta_benches]

        positive_rows = [
            (b, d, r)
            for b, d, r in zip(delta_benches, delta, llvm_ra)
            if d > 0 and r > 0
        ]
        if positive_rows:
            labels = ["geomean"] + [b for b, _, _ in positive_rows]
            series = {
                "tpde codegen - tpde_old codegen": with_geomean(
                    [d for _, d, _ in positive_rows]
                ),
                "clang LLVM_RA (O1)": with_geomean([r for _, _, r in positive_rows]),
            }
            out = output_dir / f"ct_codegen_delta_vs_llvm_ra_testsuite_{arch}.png"
            plot_grouped(
                labels,
                series,
                f"Test-suite: (tpde - tpde_old) codegen vs clang LLVM_RA ({arch})",
                "Compile time",
                out,
                yscale="log",
            )
            outputs.append(out)
        else:
            emit_missing(
                "testsuite",
                arch,
                "codegen delta vs LLVM_RA has no strictly-positive benchmark rows",
            )
    else:
        emit_missing(
            "testsuite",
            arch,
            "no common benchmarks for codegen-delta vs LLVM_RA comparison",
        )

    return outputs


def build_spec_plots(input_dir: Path, output_dir: Path, arch: str) -> list[Path]:
    outputs: list[Path] = []

    o0_path = input_dir / f"res-spec-raw-ct-o1ir-{arch}"
    if not o0_path.exists():
        emit_missing("spec", arch, f"missing file {o0_path}")
        return outputs

    o1_path = input_dir / f"res-spec-raw-ct-o1-{arch}"
    if not o1_path.exists():
        emit_missing(
            "spec",
            arch,
            f"missing file {o1_path}; skipping codegen clang_O0 vs clang_O1 comparison",
        )

    bench_o0, values_o0 = parse_ct_file(o0_path)
    bench_o0 = sort_bench_labels(bench_o0)

    values_o1: dict[str, dict[tuple[str, str], float]] = {}
    if o1_path.exists():
        _, values_o1 = parse_ct_file(o1_path)

    if o1_path.exists():
        required = [
            ("codegen", "clang"),
            ("codegen", "tpde"),
            ("codegen", "tpde_old"),
        ]
        codegen_benches = common_benches(bench_o0, values_o0, required)
        codegen_benches = [
            b for b in codegen_benches if ("codegen", "clang") in values_o1.get(b, {})
        ]
        if codegen_benches:
            labels = ["geomean"] + codegen_benches
            series = {
                "tpde_old codegen": with_geomean(
                    [values_o0[b][("codegen", "tpde_old")] for b in codegen_benches]
                ),
                "tpde codegen": with_geomean(
                    [values_o0[b][("codegen", "tpde")] for b in codegen_benches]
                ),
                "clang_O0 codegen": with_geomean(
                    [values_o0[b][("codegen", "clang")] for b in codegen_benches]
                ),
                "clang_O1 codegen": with_geomean(
                    [values_o1[b][("codegen", "clang")] for b in codegen_benches]
                ),
            }
            out = output_dir / f"ct_codegen_spec_{arch}.png"
            plot_grouped(
                labels,
                series,
                f"SPEC compile time: codegen comparison ({arch})",
                "Compile time",
                out,
                yscale="log",
            )
            outputs.append(out)
        else:
            emit_missing("spec", arch, "no common benchmarks for codegen comparison")

    tpde_cg_keys = [("tpde_cg", "tpde"), ("tpde_cg", "tpde_old")]
    tpde_cg_benches = common_benches(bench_o0, values_o0, tpde_cg_keys)
    if tpde_cg_benches:
        labels = ["geomean"] + tpde_cg_benches
        series = {
            "tpde_cg tpde_old": with_geomean(
                [values_o0[b][("tpde_cg", "tpde_old")] for b in tpde_cg_benches]
            ),
            "tpde_cg tpde": with_geomean(
                [values_o0[b][("tpde_cg", "tpde")] for b in tpde_cg_benches]
            ),
        }
        out = output_dir / f"ct_tpde_cg_spec_{arch}.png"
        plot_grouped(
            labels,
            series,
            f"SPEC compile time: tpde_cg tpde vs tpde_old ({arch})",
            "Compile time",
            out,
            yscale="log",
        )
        outputs.append(out)
    else:
        emit_missing("spec", arch, "no common benchmarks for tpde_cg comparison")

    analysis_keys = [
        ("analysis", "tpde_old"),
        ("analysis", "tpde"),
        ("tpde_pl", "tpde"),
        ("tpde_spill", "tpde"),
    ]
    analysis_benches = common_benches(bench_o0, values_o0, analysis_keys)
    if analysis_benches:
        old_analysis = [
            values_o0[b][("analysis", "tpde_old")] for b in analysis_benches
        ]
        tpde_pl = [values_o0[b][("tpde_pl", "tpde")] for b in analysis_benches]
        tpde_spill = [values_o0[b][("tpde_spill", "tpde")] for b in analysis_benches]
        tpde_analysis = [values_o0[b][("analysis", "tpde")] for b in analysis_benches]
        tpde_other = [
            max(total - pl - spill, 1e-9)
            for total, pl, spill in zip(tpde_analysis, tpde_pl, tpde_spill)
        ]

        labels = ["geomean"] + analysis_benches
        out = output_dir / f"ct_analysis_breakdown_spec_{arch}.png"
        plot_analysis_breakdown(
            labels,
            old_analysis,
            tpde_pl,
            tpde_spill,
            tpde_other,
            f"SPEC compile time: analysis tpde vs tpde_old ({arch})",
            out,
        )
        outputs.append(out)
    else:
        emit_missing("spec", arch, "no common benchmarks for analysis breakdown")

    delta_keys = [
        ("codegen", "tpde"),
        ("codegen", "tpde_old"),
        ("LLVM_RA", "clang"),
    ]
    delta_benches = common_benches(bench_o0, values_o0, delta_keys)
    if delta_benches:
        delta = [
            values_o0[b][("codegen", "tpde")] - values_o0[b][("codegen", "tpde_old")]
            for b in delta_benches
        ]
        llvm_ra = [values_o0[b][("LLVM_RA", "clang")] for b in delta_benches]
        positive_rows = [
            (b, d, r)
            for b, d, r in zip(delta_benches, delta, llvm_ra)
            if d > 0 and r > 0
        ]

        if positive_rows:
            labels = ["geomean"] + [b for b, _, _ in positive_rows]
            series = {
                "tpde codegen - tpde_old codegen": with_geomean(
                    [d for _, d, _ in positive_rows]
                ),
                "clang LLVM_RA (O0)": with_geomean([r for _, _, r in positive_rows]),
            }
            out = output_dir / f"ct_codegen_delta_vs_llvm_ra_spec_{arch}.png"
            plot_grouped(
                labels,
                series,
                f"SPEC: (tpde - tpde_old) codegen vs clang LLVM_RA ({arch})",
                "Compile time",
                out,
                yscale="log",
            )
            outputs.append(out)
        else:
            emit_missing(
                "spec",
                arch,
                "codegen delta vs LLVM_RA has no strictly-positive benchmark rows",
            )
    else:
        emit_missing("spec", arch, "no common benchmarks for codegen-delta vs LLVM_RA")

    return outputs


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    all_outputs: list[Path] = []
    for arch in args.architectures:
        all_outputs.extend(build_testsuite_plots(input_dir, output_dir, arch))
        all_outputs.extend(build_spec_plots(input_dir, output_dir, arch))

    if not all_outputs:
        raise RuntimeError("No plots were generated.")

    print(f"Done. Wrote {len(all_outputs)} plot(s).")
    for path in all_outputs:
        print(f" - {path}")


if __name__ == "__main__":
    main()
