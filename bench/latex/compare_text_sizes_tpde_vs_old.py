#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ARCHITECTURES = ("x86_64", "aarch64")
TEXT_TPDE_RE = re.compile(r"^(\d+)\s+text\s+tpde:\s+([0-9+]+)\s*$")
TEXT_TPDE_OLD_RE = re.compile(r"^(\d+)\s+text\s+tpde-old:\s+([0-9+]+)\s*$")


def parse_size(value: str) -> int:
    return sum(int(part) for part in value.split("+"))


def geomean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot compute geomean of empty list")
    return math.exp(sum(math.log(v) for v in values) / len(values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare tpde vs tpde-old text sizes and generate a per-benchmark ratio plot."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="charts/res-spec-raw-ct-o1-{arch}",
        help="input results file (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default="charts/text_size_tpde_vs_tpde_old_{arch}.png",
        help="output image path (default: %(default)s)",
    )
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=list(ARCHITECTURES),
        help="Architectures to plot (default: x86_64 aarch64)",
    )
    return parser.parse_args()


def normalize_input_path(path_text: str) -> Path:
    # Allow CLI-style @file shorthand.
    normalized = path_text[1:] if path_text.startswith("@") else path_text
    return Path(normalized)


def path_for_arch(path_text: str, arch: str) -> Path:
    normalized = path_text[1:] if path_text.startswith("@") else path_text
    if "{arch}" in normalized:
        return Path(normalized.format(arch=arch))
    for token in ARCHITECTURES:
        if token in normalized:
            return Path(normalized.replace(token, arch))
    return Path(normalized)


def output_path_for_arch(path_text: str, arch: str) -> Path:
    base_path = path_for_arch(path_text, arch)
    if "{arch}" in path_text:
        return base_path
    return base_path.with_name(f"{base_path.stem}_{arch}{base_path.suffix}")


def parse_text_sizes(path: Path) -> list[tuple[str, int, int]]:
    tpde_by_bench: dict[str, int] = {}
    old_by_bench: dict[str, int] = {}

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = TEXT_TPDE_RE.match(line)
        if m:
            bench, size = m.groups()
            tpde_by_bench[bench] = parse_size(size)
            continue

        m = TEXT_TPDE_OLD_RE.match(line)
        if m:
            bench, size = m.groups()
            old_by_bench[bench] = parse_size(size)

    benches = sorted(set(tpde_by_bench) | set(old_by_bench), key=int)
    rows: list[tuple[str, int, int]] = []
    for bench in benches:
        if bench not in tpde_by_bench or bench not in old_by_bench:
            raise ValueError(
                f"missing tpde or tpde-old text size for benchmark {bench}"
            )
        rows.append((bench, tpde_by_bench[bench], old_by_bench[bench]))

    return rows


def main() -> None:
    args = parse_args()
    outputs: list[Path] = []
    for arch in args.architectures:
        input_path = path_for_arch(args.input, arch)
        output_path = output_path_for_arch(args.output, arch)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found for {arch}: {input_path}")

        rows = parse_text_sizes(input_path)

        ratios: list[float] = []
        for _bench, tpde, old in rows:
            ratios.append(tpde / old)

        gm = geomean(ratios)
        labels = ["geomean"] + [bench for bench, _, _ in rows]
        values = [gm] + ratios

        x = np.arange(len(labels))
        plt.figure(figsize=(max(10, len(labels) * 0.5), 6))
        plt.bar(x, values, width=0.7, color="steelblue")
        plt.axhline(1.0, color="black", linestyle="--", linewidth=1)
        plt.yscale("log")
        plt.ylabel("Text size ratio (tpde / tpde-old)")
        plt.xlabel("SPEC benchmark")
        plt.title(f"TPDE text size vs TPDE-old ({arch})")
        plt.xticks(x, labels, rotation=75, ha="right")
        plt.tight_layout()

        if output_path.parent and output_path.parent != Path("."):
            output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=220)
        plt.close()
        outputs.append(output_path)

        print(
            f"Wrote {output_path} for {len(rows)} benchmarks "
            f"(geomean tpde/tpde-old: {gm:.6f})"
        )

    print(f"Done. Wrote {len(outputs)} plot(s).")


if __name__ == "__main__":
    main()
