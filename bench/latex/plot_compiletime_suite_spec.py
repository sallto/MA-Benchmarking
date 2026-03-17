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
    hline: float | None = None,
) -> None:
    names = list(series.keys())
    x = np.arange(len(labels))
    width = min(0.8 / max(len(names), 1), 0.24)

    plt.figure(figsize=(max(12, len(labels) * 0.5), 6.5))
    for idx, name in enumerate(names):
        offset = (idx - (len(names) - 1) / 2.0) * width
        plt.bar(x + offset, series[name], width=width, label=name)

    if hline is not None:
        plt.axhline(hline, color="black", linestyle="--", linewidth=1)

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
    ylabel: str,
    output_path: Path,
    *,
    hline: float | None = None,
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

    if hline is not None:
        plt.axhline(hline, color="black", linestyle="--", linewidth=1)

    plt.yscale("log")
    plt.ylabel(ylabel)
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


def build_relative_series(
    benches: list[str],
    baseline_by_bench: dict[str, float],
    raw_series: dict[str, list[float]],
) -> tuple[list[str], dict[str, list[float]]]:
    positive_benches = [
        b for b in benches if b in baseline_by_bench and baseline_by_bench[b] > 0
    ]
    if not positive_benches:
        return [], {}

    rel_series: dict[str, list[float]] = {}
    for name, values in raw_series.items():
        by_bench = dict(zip(benches, values))
        rel_values = [
            (by_bench[b] / baseline_by_bench[b]) * 100.0 for b in positive_benches
        ]
        rel_series[name] = with_geomean(rel_values)

    rel_series["clang_O1 baseline"] = [100.0 for _ in range(len(positive_benches) + 1)]
    labels = ["geomean"] + positive_benches
    return labels, rel_series


def build_relative_list(
    benches: list[str],
    baseline_by_bench: dict[str, float],
    values: list[float],
) -> tuple[list[str], list[float]]:
    by_bench = dict(zip(benches, values))
    positive_benches = [
        b for b in benches if b in baseline_by_bench and baseline_by_bench[b] > 0
    ]
    rel_values = [
        (by_bench[b] / baseline_by_bench[b]) * 100.0 for b in positive_benches
    ]
    return positive_benches, rel_values


def build_testsuite_plots(input_dir: Path, output_dir: Path, arch: str) -> list[Path]:
    outputs: list[Path] = []
    path = input_dir / f"res-test-suite-ct-{arch}"
    if not path.exists():
        emit_missing("testsuite", arch, f"missing file {path}")
        return outputs

    bench_order, values = parse_ct_file(path)
    benches = sort_bench_labels(bench_order)
    baseline_o1 = {
        b: values[b][("codegen", "clang_o1")]
        for b in benches
        if ("codegen", "clang_o1") in values.get(b, {})
        and values[b][("codegen", "clang_o1")] > 0
    }

    codegen_keys = [
        ("codegen", "tpde_old"),
        ("codegen", "tpde"),
        ("codegen", "clang_o0"),
        ("codegen", "clang_o1"),
    ]
    codegen_benches = common_benches(benches, values, codegen_keys)
    if codegen_benches:
        labels_abs = ["geomean"] + codegen_benches
        raw_series = {
            "tpde_old codegen": [
                values[b][("codegen", "tpde_old")] for b in codegen_benches
            ],
            "tpde codegen": [values[b][("codegen", "tpde")] for b in codegen_benches],
            "clang_O0 codegen": [
                values[b][("codegen", "clang_o0")] for b in codegen_benches
            ],
            "clang_O1 codegen": [
                values[b][("codegen", "clang_o1")] for b in codegen_benches
            ],
        }
        series_abs = {
            "tpde_old codegen": with_geomean(raw_series["tpde_old codegen"]),
            "tpde codegen": with_geomean(raw_series["tpde codegen"]),
            "clang_O0 codegen": with_geomean(raw_series["clang_O0 codegen"]),
            "clang_O1 codegen": with_geomean(raw_series["clang_O1 codegen"]),
        }
        out = output_dir / f"ct_codegen_testsuite_{arch}.png"
        plot_grouped(
            labels_abs,
            series_abs,
            f"Test-suite compile time: codegen comparison ({arch})",
            "Compile time",
            out,
            yscale="log",
        )
        outputs.append(out)

        labels_rel, series_rel = build_relative_series(
            codegen_benches,
            baseline_o1,
            raw_series,
        )
        if labels_rel:
            out_rel = (
                output_dir / f"ct_codegen_testsuite_relative_to_clang_o1_{arch}.png"
            )
            plot_grouped(
                labels_rel,
                series_rel,
                f"Test-suite compile time: codegen relative to clang_O1 ({arch})",
                "Compile time (% of clang_O1, clang_O1 = 100%)",
                out_rel,
                yscale="log",
                hline=100.0,
            )
            outputs.append(out_rel)
        else:
            emit_missing("testsuite", arch, "cannot build relative codegen plot")
    else:
        emit_missing("testsuite", arch, "no common benchmarks for codegen comparison")

    tpde_cg_keys = [("tpde_cg", "tpde"), ("tpde_cg", "tpde_old")]
    tpde_cg_benches = common_benches(benches, values, tpde_cg_keys)
    if tpde_cg_benches:
        labels_abs = ["geomean"] + tpde_cg_benches
        raw_series = {
            "tpde_cg tpde_old": [
                values[b][("tpde_cg", "tpde_old")] for b in tpde_cg_benches
            ],
            "tpde_cg tpde": [values[b][("tpde_cg", "tpde")] for b in tpde_cg_benches],
        }
        series_abs = {
            "tpde_cg tpde_old": with_geomean(raw_series["tpde_cg tpde_old"]),
            "tpde_cg tpde": with_geomean(raw_series["tpde_cg tpde"]),
        }
        out = output_dir / f"ct_tpde_cg_testsuite_{arch}.png"
        plot_grouped(
            labels_abs,
            series_abs,
            f"Test-suite compile time: tpde_cg tpde vs tpde_old ({arch})",
            "Compile time",
            out,
            yscale="log",
        )
        outputs.append(out)

        labels_rel, series_rel = build_relative_series(
            tpde_cg_benches,
            baseline_o1,
            raw_series,
        )
        if labels_rel:
            out_rel = (
                output_dir / f"ct_tpde_cg_testsuite_relative_to_clang_o1_{arch}.png"
            )
            plot_grouped(
                labels_rel,
                series_rel,
                f"Test-suite compile time: tpde_cg relative to clang_O1 ({arch})",
                "Compile time (% of clang_O1, clang_O1 = 100%)",
                out_rel,
                yscale="log",
                hline=100.0,
            )
            outputs.append(out_rel)
        else:
            emit_missing("testsuite", arch, "cannot build relative tpde_cg plot")
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

        labels_abs = ["geomean"] + analysis_benches
        out = output_dir / f"ct_analysis_breakdown_testsuite_{arch}.png"
        plot_analysis_breakdown(
            labels_abs,
            old_analysis,
            tpde_pl,
            tpde_spill,
            tpde_other,
            f"Test-suite compile time: analysis tpde vs tpde_old ({arch})",
            "Compile time",
            out,
        )
        outputs.append(out)

        rel_benches, old_rel = build_relative_list(
            analysis_benches,
            baseline_o1,
            old_analysis,
        )
        _, pl_rel = build_relative_list(analysis_benches, baseline_o1, tpde_pl)
        _, spill_rel = build_relative_list(analysis_benches, baseline_o1, tpde_spill)
        _, other_rel = build_relative_list(analysis_benches, baseline_o1, tpde_other)
        if rel_benches:
            out_rel = (
                output_dir
                / f"ct_analysis_breakdown_testsuite_relative_to_clang_o1_{arch}.png"
            )
            plot_analysis_breakdown(
                ["geomean"] + rel_benches,
                old_rel,
                pl_rel,
                spill_rel,
                other_rel,
                f"Test-suite compile time: analysis relative to clang_O1 ({arch})",
                "Compile time (% of clang_O1, clang_O1 = 100%)",
                out_rel,
                hline=100.0,
            )
            outputs.append(out_rel)
        else:
            emit_missing("testsuite", arch, "cannot build relative analysis plot")
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
            delta_benches = [b for b, _, _ in positive_rows]
            labels_abs = ["geomean"] + delta_benches
            raw_series = {
                "tpde codegen - tpde_old codegen": [d for _, d, _ in positive_rows],
                "clang LLVM_RA (O1)": [r for _, _, r in positive_rows],
            }
            series_abs = {
                "tpde codegen - tpde_old codegen": with_geomean(
                    raw_series["tpde codegen - tpde_old codegen"]
                ),
                "clang LLVM_RA (O1)": with_geomean(raw_series["clang LLVM_RA (O1)"]),
            }
            out = output_dir / f"ct_codegen_delta_vs_llvm_ra_testsuite_{arch}.png"
            plot_grouped(
                labels_abs,
                series_abs,
                f"Test-suite: (tpde - tpde_old) codegen vs clang LLVM_RA ({arch})",
                "Compile time",
                out,
                yscale="log",
            )
            outputs.append(out)

            labels_rel, series_rel = build_relative_series(
                delta_benches,
                baseline_o1,
                raw_series,
            )
            if labels_rel:
                out_rel = (
                    output_dir
                    / f"ct_codegen_delta_vs_llvm_ra_testsuite_relative_to_clang_o1_{arch}.png"
                )
                plot_grouped(
                    labels_rel,
                    series_rel,
                    f"Test-suite: codegen delta vs LLVM_RA relative to clang_O1 ({arch})",
                    "Compile time (% of clang_O1, clang_O1 = 100%)",
                    out_rel,
                    yscale="log",
                    hline=100.0,
                )
                outputs.append(out_rel)
            else:
                emit_missing(
                    "testsuite",
                    arch,
                    "cannot build relative codegen-delta vs LLVM_RA plot",
                )
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
    baseline_o1: dict[str, float] = {}
    if o1_path.exists():
        _, values_o1 = parse_ct_file(o1_path)
        baseline_o1 = {
            b: values_o1[b][("codegen", "clang")]
            for b in values_o1
            if ("codegen", "clang") in values_o1[b]
            and values_o1[b][("codegen", "clang")] > 0
        }

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
            labels_abs = ["geomean"] + codegen_benches
            raw_series = {
                "tpde_old codegen": [
                    values_o0[b][("codegen", "tpde_old")] for b in codegen_benches
                ],
                "tpde codegen": [
                    values_o0[b][("codegen", "tpde")] for b in codegen_benches
                ],
                "clang_O0 codegen": [
                    values_o0[b][("codegen", "clang")] for b in codegen_benches
                ],
                "clang_O1 codegen": [
                    values_o1[b][("codegen", "clang")] for b in codegen_benches
                ],
            }
            series_abs = {
                "tpde_old codegen": with_geomean(raw_series["tpde_old codegen"]),
                "tpde codegen": with_geomean(raw_series["tpde codegen"]),
                "clang_O0 codegen": with_geomean(raw_series["clang_O0 codegen"]),
                "clang_O1 codegen": with_geomean(raw_series["clang_O1 codegen"]),
            }
            out = output_dir / f"ct_codegen_spec_{arch}.png"
            plot_grouped(
                labels_abs,
                series_abs,
                f"SPEC compile time: codegen comparison ({arch})",
                "Compile time",
                out,
                yscale="log",
            )
            outputs.append(out)

            labels_rel, series_rel = build_relative_series(
                codegen_benches,
                baseline_o1,
                raw_series,
            )
            if labels_rel:
                out_rel = (
                    output_dir / f"ct_codegen_spec_relative_to_clang_o1_{arch}.png"
                )
                plot_grouped(
                    labels_rel,
                    series_rel,
                    f"SPEC compile time: codegen relative to clang_O1 ({arch})",
                    "Compile time (% of clang_O1, clang_O1 = 100%)",
                    out_rel,
                    yscale="log",
                    hline=100.0,
                )
                outputs.append(out_rel)
            else:
                emit_missing("spec", arch, "cannot build relative codegen plot")
        else:
            emit_missing("spec", arch, "no common benchmarks for codegen comparison")

    tpde_cg_keys = [("tpde_cg", "tpde"), ("tpde_cg", "tpde_old")]
    tpde_cg_benches = common_benches(bench_o0, values_o0, tpde_cg_keys)
    if tpde_cg_benches:
        labels_abs = ["geomean"] + tpde_cg_benches
        raw_series = {
            "tpde_cg tpde_old": [
                values_o0[b][("tpde_cg", "tpde_old")] for b in tpde_cg_benches
            ],
            "tpde_cg tpde": [
                values_o0[b][("tpde_cg", "tpde")] for b in tpde_cg_benches
            ],
        }
        series_abs = {
            "tpde_cg tpde_old": with_geomean(raw_series["tpde_cg tpde_old"]),
            "tpde_cg tpde": with_geomean(raw_series["tpde_cg tpde"]),
        }
        out = output_dir / f"ct_tpde_cg_spec_{arch}.png"
        plot_grouped(
            labels_abs,
            series_abs,
            f"SPEC compile time: tpde_cg tpde vs tpde_old ({arch})",
            "Compile time",
            out,
            yscale="log",
        )
        outputs.append(out)

        if baseline_o1:
            labels_rel, series_rel = build_relative_series(
                tpde_cg_benches,
                baseline_o1,
                raw_series,
            )
            if labels_rel:
                out_rel = (
                    output_dir / f"ct_tpde_cg_spec_relative_to_clang_o1_{arch}.png"
                )
                plot_grouped(
                    labels_rel,
                    series_rel,
                    f"SPEC compile time: tpde_cg relative to clang_O1 ({arch})",
                    "Compile time (% of clang_O1, clang_O1 = 100%)",
                    out_rel,
                    yscale="log",
                    hline=100.0,
                )
                outputs.append(out_rel)
            else:
                emit_missing("spec", arch, "cannot build relative tpde_cg plot")
        else:
            emit_missing(
                "spec", arch, "missing clang_O1 baseline for relative tpde_cg plot"
            )
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

        labels_abs = ["geomean"] + analysis_benches
        out = output_dir / f"ct_analysis_breakdown_spec_{arch}.png"
        plot_analysis_breakdown(
            labels_abs,
            old_analysis,
            tpde_pl,
            tpde_spill,
            tpde_other,
            f"SPEC compile time: analysis tpde vs tpde_old ({arch})",
            "Compile time",
            out,
        )
        outputs.append(out)

        if baseline_o1:
            rel_benches, old_rel = build_relative_list(
                analysis_benches,
                baseline_o1,
                old_analysis,
            )
            _, pl_rel = build_relative_list(analysis_benches, baseline_o1, tpde_pl)
            _, spill_rel = build_relative_list(
                analysis_benches, baseline_o1, tpde_spill
            )
            _, other_rel = build_relative_list(
                analysis_benches, baseline_o1, tpde_other
            )
            if rel_benches:
                out_rel = (
                    output_dir
                    / f"ct_analysis_breakdown_spec_relative_to_clang_o1_{arch}.png"
                )
                plot_analysis_breakdown(
                    ["geomean"] + rel_benches,
                    old_rel,
                    pl_rel,
                    spill_rel,
                    other_rel,
                    f"SPEC compile time: analysis relative to clang_O1 ({arch})",
                    "Compile time (% of clang_O1, clang_O1 = 100%)",
                    out_rel,
                    hline=100.0,
                )
                outputs.append(out_rel)
            else:
                emit_missing("spec", arch, "cannot build relative analysis plot")
        else:
            emit_missing(
                "spec", arch, "missing clang_O1 baseline for relative analysis plot"
            )
    else:
        emit_missing("spec", arch, "no common benchmarks for analysis breakdown")

    delta_keys = [
        ("codegen", "tpde"),
        ("codegen", "tpde_old"),
    ]
    delta_benches = common_benches(bench_o0, values_o0, delta_keys)
    delta_benches = [
        b for b in delta_benches if ("LLVM_RA", "clang") in values_o1.get(b, {})
    ]
    if delta_benches:
        delta = [
            values_o0[b][("codegen", "tpde")] - values_o0[b][("codegen", "tpde_old")]
            for b in delta_benches
        ]
        llvm_ra = [values_o1[b][("LLVM_RA", "clang")] for b in delta_benches]
        positive_rows = [
            (b, d, r)
            for b, d, r in zip(delta_benches, delta, llvm_ra)
            if d > 0 and r > 0
        ]

        if positive_rows:
            delta_benches = [b for b, _, _ in positive_rows]
            labels_abs = ["geomean"] + delta_benches
            raw_series = {
                "tpde codegen - tpde_old codegen": [d for _, d, _ in positive_rows],
                "clang LLVM_RA (O1)": [r for _, _, r in positive_rows],
            }
            series_abs = {
                "tpde codegen - tpde_old codegen": with_geomean(
                    raw_series["tpde codegen - tpde_old codegen"]
                ),
                "clang LLVM_RA (O1)": with_geomean(raw_series["clang LLVM_RA (O1)"]),
            }
            out = output_dir / f"ct_codegen_delta_vs_llvm_ra_spec_{arch}.png"
            plot_grouped(
                labels_abs,
                series_abs,
                f"SPEC: (tpde - tpde_old) codegen vs clang LLVM_RA ({arch})",
                "Compile time",
                out,
                yscale="log",
            )
            outputs.append(out)

            if baseline_o1:
                labels_rel, series_rel = build_relative_series(
                    delta_benches,
                    baseline_o1,
                    raw_series,
                )
                if labels_rel:
                    out_rel = (
                        output_dir
                        / f"ct_codegen_delta_vs_llvm_ra_spec_relative_to_clang_o1_{arch}.png"
                    )
                    plot_grouped(
                        labels_rel,
                        series_rel,
                        f"SPEC: codegen delta vs LLVM_RA relative to clang_O1 ({arch})",
                        "Compile time (% of clang_O1, clang_O1 = 100%)",
                        out_rel,
                        yscale="log",
                        hline=100.0,
                    )
                    outputs.append(out_rel)
                else:
                    emit_missing(
                        "spec",
                        arch,
                        "cannot build relative codegen-delta vs LLVM_RA plot",
                    )
            else:
                emit_missing(
                    "spec",
                    arch,
                    "missing clang_O1 baseline for relative codegen-delta vs LLVM_RA plot",
                )
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
