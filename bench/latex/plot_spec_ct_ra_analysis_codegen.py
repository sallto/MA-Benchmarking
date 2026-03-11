#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ARCHITECTURES = ["x86_64"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot SPEC compile-time comparisons for LLVM_RA/analysis and codegen, "
            "including geomean."
        )
    )
    parser.add_argument(
        "--o1ir",
        default="charts/res-spec-raw-ct-o1ir-{arch}",
        help="Path to o1ir compile-time results (default: charts/res-spec-raw-ct-o1ir-{arch})",
    )
    parser.add_argument(
        "--o1",
        default="charts/res-spec-raw-ct-o1-{arch}",
        help="Path to o1 compile-time results (default: charts/res-spec-raw-ct-o1-{arch})",
    )
    parser.add_argument(
        "--ra-output",
        default="charts/spec_ct_ra_vs_tpde_analysis_{arch}.png",
        help="Output path for LLVM_RA/analysis plot",
    )
    parser.add_argument(
        "--codegen-output",
        default="charts/spec_ct_codegen_4variants_{arch}.png",
        help="Output path for codegen comparison plot",
    )
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=ARCHITECTURES,
        help="Architectures to plot (default: x86_64 aarch64)",
    )
    return parser.parse_args()


def path_for_arch(path_text: str, arch: str) -> Path:
    if "{arch}" in path_text:
        return Path(path_text.format(arch=arch))
    for token in ARCHITECTURES:
        if token in path_text:
            return Path(path_text.replace(token, arch))
    return Path(path_text)


def output_path_for_arch(path_text: str, arch: str) -> Path:
    base = path_for_arch(path_text, arch)
    if "{arch}" in path_text:
        return base
    return base.with_name(f"{base.stem}_{arch}{base.suffix}")


def benchmark_sort_key(name: str) -> tuple[int, str]:
    return (0, f"{int(name):08d}") if name.isdigit() else (1, name)


def geometric_mean(values: list[float]) -> float | None:
    positives = [v for v in values if v > 0]
    if not positives:
        return None
    return float(np.exp(np.mean(np.log(positives))))


def parse_ct_file(path: Path) -> dict[str, dict[tuple[str, str], float]]:
    rows: dict[str, dict[tuple[str, str], float]] = {}
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.endswith(":"):
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            bench, metric, variant, value_text = parts[:4]
            try:
                value = float(value_text)
            except ValueError:
                continue

            bench_map = rows.setdefault(bench, {})
            bench_map[(metric, variant)] = value
    return rows


def collect_ra_analysis(
    o1ir: dict[str, dict[tuple[str, str], float]],
    o1: dict[str, dict[tuple[str, str], float]],
) -> tuple[list[str], dict[str, list[float]]]:
    required = [
        (("LLVM_RA", "clang"), "clangO0 LLVM_RA"),
        (("LLVM_RA", "clang"), "clangO1 LLVM_RA"),
        (("analysis", "tpde_old"), "tpde-old analysis"),
        (("tpde_pl", "tpde"), "tpde pl"),
        (("tpde_spill", "tpde"), "tpde spill"),
        (("analysis","tpde"), "tpde analysis")
    ]

    benches = sorted(set(o1ir) & set(o1), key=benchmark_sort_key)
    out: dict[str, list[float]] = {
        "clangO0 LLVM_RA": [],
        "clangO1 LLVM_RA": [],
        "tpde-old analysis": [],
        "tpde pl": [],
        "tpde spill": [],
        "tpde rest":[],
    }
    selected_benches: list[str] = []

    for bench in benches:
        row_o1ir = o1ir[bench]
        row_o1 = o1[bench]

        if any(k not in row_o1ir for k, _ in required[:1] + required[2:]):
            continue
        if required[1][0] not in row_o1:
            continue

        selected_benches.append(bench)
        out["clangO0 LLVM_RA"].append(row_o1ir[("LLVM_RA", "clang")])
        out["clangO1 LLVM_RA"].append(row_o1[("LLVM_RA", "clang")])
        out["tpde-old analysis"].append(row_o1ir[("analysis", "tpde_old")])
        out["tpde pl"].append(row_o1ir[("tpde_pl", "tpde")])
        out["tpde spill"].append(row_o1ir[("tpde_spill", "tpde")])
        out["tpde rest"].append(row_o1ir[("analysis","tpde")]- row_o1ir[("tpde_pl", "tpde")] - row_o1ir[("tpde_spill", "tpde")])

    if selected_benches:
        selected_benches.insert(0, "geomean")
        for key in list(out):
            gm = geometric_mean(out[key])
            out[key].insert(0, gm if gm is not None else np.nan)

    return selected_benches, out


def collect_codegen(
    o1ir: dict[str, dict[tuple[str, str], float]],
    o1: dict[str, dict[tuple[str, str], float]],
) -> tuple[list[str], dict[str, list[float]]]:
    benches = sorted(set(o1ir) & set(o1), key=benchmark_sort_key)
    out: dict[str, list[float]] = {
        "clangO0": [],
        "clangO1": [],
        "tpde-old": [],
        "tpde": [],
    }
    selected_benches: list[str] = []

    for bench in benches:
        row_o1ir = o1ir[bench]
        row_o1 = o1[bench]

        keys_o1ir = [
            ("codegen", "clang"),
            ("codegen", "tpde_old"),
            ("codegen", "tpde"),
        ]
        if any(k not in row_o1ir for k in keys_o1ir):
            continue
        if ("codegen", "clang") not in row_o1:
            continue

        selected_benches.append(bench)
        out["clangO0"].append(row_o1ir[("codegen", "clang")])
        out["clangO1"].append(row_o1[("codegen", "clang")])
        out["tpde-old"].append(row_o1ir[("codegen", "tpde_old")])
        out["tpde"].append(row_o1ir[("codegen", "tpde")])

    if selected_benches:
        selected_benches.insert(0, "geomean")
        for key in list(out):
            gm = geometric_mean(out[key])
            out[key].insert(0, gm if gm is not None else np.nan)

    return selected_benches, out


def save_ra_analysis_plot(
    benches: list[str], values: dict[str, list[float]], output: Path, arch: str
) -> None:
    x = np.arange(len(benches))
    width = 0.18

    plt.figure(figsize=(max(11, len(benches) * 0.75), 6))
    plt.bar(
        x - 1.5 * width, values["clangO0 LLVM_RA"], width=width, label="clangO0 LLVM_RA"
    )
    plt.bar(
        x - 0.5 * width, values["clangO1 LLVM_RA"], width=width, label="clangO1 LLVM_RA"
    )
    plt.bar(
        x + 0.5 * width,
        values["tpde-old analysis"],
        width=width,
        label="tpde-old analysis",
    )

    pl = np.array(values["tpde pl"], dtype=float)
    spill = np.array(values["tpde spill"], dtype=float)
    rest = np.array(values["tpde rest"], dtype=float)
    plt.bar(x + 1.5 * width, pl, width=width, label="tpde analysis: pl")
    plt.bar(
        x + 1.5 * width, spill, width=width, bottom=pl, label="tpde analysis: spill"
    )
    plt.bar(
        x + 1.5 * width,
        rest,
        width=width,
        bottom=pl + spill,
        label="tpde analysis: rest",
    )

    plt.ylabel("Compile time (ms)")
    plt.xlabel("SPEC benchmark")
    plt.title(f"LLVM_RA vs TPDE analysis components ({arch})")
    plt.xticks(x, benches, rotation=45, ha="right")
    plt.yscale("log")
    plt.legend()
    plt.tight_layout()

    if output.parent and output.parent != Path("."):
        output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=220)
    plt.close()


def save_codegen_plot(
    benches: list[str], values: dict[str, list[float]], output: Path, arch: str
) -> None:
    variants = ["clangO0", "clangO1", "tpde-old", "tpde"]
    x = np.arange(len(benches))
    width = min(0.8 / len(variants), 0.22)

    plt.figure(figsize=(max(11, len(benches) * 0.75), 6))
    for idx, variant in enumerate(variants):
        offset = (idx - (len(variants) - 1) / 2.0) * width
        plt.bar(x + offset, values[variant], width=width, label=variant)

    plt.ylabel("Codegen time (ms)")
    plt.xlabel("SPEC benchmark")
    plt.title(f"Codegen comparison across 4 variants ({arch})")
    plt.xticks(x, benches, rotation=45, ha="right")
    plt.yscale("log")
    plt.legend()
    plt.tight_layout()

    if output.parent and output.parent != Path("."):
        output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=220)
    plt.close()


def main() -> None:
    args = parse_args()
    outputs: list[tuple[Path, Path]] = []
    print(args.architectures)
    for arch in ["x86_64"]:
        if arch not in ARCHITECTURES:
            continue
        o1ir_path = path_for_arch(args.o1ir, arch)
        o1_path = path_for_arch(args.o1, arch)
        ra_output = output_path_for_arch(args.ra_output, arch)
        codegen_output = output_path_for_arch(args.codegen_output, arch)

        if not o1ir_path.exists():
            raise FileNotFoundError(f"Input file not found for {arch}: {o1ir_path}")
        if not o1_path.exists():
            raise FileNotFoundError(f"Input file not found for {arch}: {o1_path}")

        o1ir = parse_ct_file(o1ir_path)
        o1 = parse_ct_file(o1_path)

        ra_benches, ra_values = collect_ra_analysis(o1ir, o1)
        if not ra_benches:
            raise RuntimeError("No complete rows found for LLVM_RA/analysis plot")
        save_ra_analysis_plot(ra_benches, ra_values, ra_output, arch)

        codegen_benches, codegen_values = collect_codegen(o1ir, o1)
        if not codegen_benches:
            raise RuntimeError("No complete rows found for codegen plot")
        save_codegen_plot(codegen_benches, codegen_values, codegen_output, arch)
        outputs.append((ra_output, codegen_output))

        print(f"Wrote {ra_output} and {codegen_output}")

    print(f"Done. Wrote {2 * len(outputs)} plot(s).")


if __name__ == "__main__":
    main()
