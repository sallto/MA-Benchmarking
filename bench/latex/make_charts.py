#!/usr/bin/env python3
"""
Read "results" and generate:
  - 1 bar-chart PNG per category
  - 1 additional chart: geomean.png (geometric means across all categories)

Expected data lines (whitespace-separated):
<category> <pass_or_bucket> <toolchain> <value>

Rules:
- Ignore WARNING lines.
- Compute totals per (category, toolchain) by summing all values.
- For each category:
    * Bars: tpde, clang_o0, clang_o1
    * Normalize so clang_o1 = 1
    * Log-scale y-axis
    * Save as "<category>.png"
- Geomean chart:
    * Compute geometric mean of normalized ratios across categories
    * Save as "geomean.png"
"""

from __future__ import annotations
import re
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt


INPUT_FILE = Path("res-test-suite-ct-x86_64")
OUT_DIR = Path("charts")


TOOLS = ["tpde_old","tpde", "clang_o0", "clang_o1"]


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w.\-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "category"


def parse_results(path: Path):
    totals = defaultdict(lambda: defaultdict(float))

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("WARNING:"):
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            category, _passname, toolchain, value_str = parts[:4]

            try:
                value = float(value_str)
            except ValueError:
                continue

            totals[category][toolchain] += value

    return totals


def plot_bar_chart(name: str, values: list[float], ylabel: str, title: str):
    eps = 1e-12
    values = [v if v > 0 else eps for v in values]

    plt.figure(figsize=(7, 4.5))
    plt.bar(TOOLS, values)
    plt.yscale("log")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(OUT_DIR / f"{sanitize_filename(name)}.png", dpi=200)
    plt.close()


def geometric_mean(values: list[float]) -> float:
    # values must all be > 0
    logs = [math.log(v) for v in values]
    return math.exp(sum(logs) / len(logs))


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Couldn't find input file: {INPUT_FILE.resolve()}")

    totals = parse_results(INPUT_FILE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Store normalized ratios per category for geomean
    normalized_per_category = {}

    # Per-category charts
    for category, tool_totals in sorted(totals.items()):
        clang_o1_total = tool_totals.get("clang_o1", 0.0)

        if clang_o1_total > 0:
            normalized = [
                tool_totals.get(t, 0.0) / clang_o1_total for t in TOOLS
            ]
            ylabel = "Relative total (log scale, clang_o1 = 1)"
            title = f"{category}: normalized totals"
        else:
            normalized = [tool_totals.get(t, 0.0) for t in TOOLS]
            ylabel = "Total (log scale; clang_o1 missing/0)"
            title = f"{category}: totals (unnormalized)"

        normalized_per_category[category] = normalized
        plot_bar_chart(category, normalized, ylabel, title)

    # ---- Geomean chart ----
    # Collect ratios across categories (only where clang_o1 > 0 and ratio > 0)
    tool_ratios = {tool: [] for tool in TOOLS}

    for category, ratios in normalized_per_category.items():
        clang_o1_ratio = ratios[TOOLS.index("clang_o1")]
        if clang_o1_ratio <= 0:
            continue  # skip invalid normalization

        for tool, ratio in zip(TOOLS, ratios):
            if ratio > 0:
                tool_ratios[tool].append(ratio)

    geomean_values = []
    for tool in TOOLS:
        if tool == "clang_o1":
            # Always 1 by construction
            geomean_values.append(1.0)
        else:
            vals = tool_ratios[tool]
            if vals:
                geomean_values.append(geometric_mean(vals))
            else:
                geomean_values.append(1e-12)

    plot_bar_chart(
        "geomean",
        geomean_values,
        "Geometric mean (log scale, clang_o1 = 1)",
        "Geometric Mean Across All Categories",
    )

    print(f"Done. Wrote {len(totals)} category charts + geomean.png")


if __name__ == "__main__":
    main()