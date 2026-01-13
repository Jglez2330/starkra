#!/usr/bin/env python3
"""
Summarize experiment CSV logs by benchmark.

Outputs:
- Mean prover time (ms)
- Mean verifier time (ms)
- Mean proof size (bits)   (computed as proof_bytes * 8)

All numeric outputs are formatted to 3 decimals.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


_DUR_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*(µs|us|ms|s)\s*$")


def duration_to_ms(s: str) -> float:
    """
    Convert strings like '966.114µs', '1.559ms', '2s' to milliseconds.
    """
    m = _DUR_RE.match(s)
    if not m:
        raise ValueError(f"Unrecognized duration format: {s!r}")
    val = float(m.group(1))
    unit = m.group(2)
    if unit in ("µs", "us"):
        return val / 1000.0
    if unit == "ms":
        return val
    if unit == "s":
        return val * 1000.0
    raise ValueError(f"Unhandled unit: {unit!r}")


@dataclass
class Row:
    bench: str
    prove_ms: float
    verify_ms: float
    proof_bits: float


def mean(xs: List[float]) -> float:
    if not xs:
        raise ValueError("Cannot take mean of empty list")
    return sum(xs) / len(xs)


def read_rows(csv_path: Path) -> List[Row]:
    rows: List[Row] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"bench", "prove", "verify", "proof_bytes"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")

        for i, r in enumerate(reader, start=2):  # header is line 1
            try:
                bench = str(r["bench"]).strip().strip('"')
                prove_ms = duration_to_ms(str(r["prove"]))
                verify_ms = duration_to_ms(str(r["verify"]))
                proof_bytes = int(str(r["proof_bytes"]).strip().strip('"'))
                proof_bits = float(proof_bytes * 8)
                rows.append(Row(bench, prove_ms, verify_ms, proof_bits))
            except Exception as e:
                raise ValueError(f"Error parsing line {i}: {e}") from e
    return rows


def summarize(rows: List[Row]) -> List[Tuple[str, float, float, float]]:
    by_bench: Dict[str, List[Row]] = {}
    for r in rows:
        by_bench.setdefault(r.bench, []).append(r)

    out: List[Tuple[str, float, float, float]] = []
    for bench in sorted(by_bench.keys()):
        rs = by_bench[bench]
        out.append(
            (
                bench,
                mean([x.prove_ms for x in rs]),
                mean([x.verify_ms for x in rs]),
                mean([x.proof_bits for x in rs]),
            )
        )
    return out


def write_summary_csv(summary: List[Tuple[str, float, float, float]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bench", "mean_prover_ms", "mean_verifier_ms", "mean_proof_bits"])
        for bench, p, v, b in summary:
            w.writerow([bench, f"{p:.3f}", f"{v:.3f}", f"{b:.3f}"])


def latex_table(summary: List[Tuple[str, float, float, float]], caption: str, label: str) -> str:
    lines = []
    lines.append(r"\begin{table}[ht!]")
    lines.append(r"\centering")
    lines.append(rf"\caption{{{caption}}}")
    lines.append(rf"\label{{{label}}}")
    lines.append(r"\begin{tabular}{lrrr}")
    lines.append(r"\toprule")
    lines.append(r"bench & proof generation (ms) & proof verification (ms) & proof size (bits) \\")
    lines.append(r"\midrule")
    for bench, p, v, b in summary:
        lines.append(f"{bench} & {p:.3f} & {v:.3f} & {b:.3f} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path, help="Input experiment CSV (per-run rows).")
    ap.add_argument("--out-csv", type=Path, default=Path("summary.csv"), help="Output summary CSV.")
    ap.add_argument("--out-tex", type=Path, default=Path("summary_table.tex"), help="Output LaTeX table file.")
    ap.add_argument("--caption", type=str, default="Benchmark results: mean prover time, verifier time, and proof size.")
    ap.add_argument("--label", type=str, default="tab:bench_summary")
    args = ap.parse_args()

    rows = read_rows(args.csv)
    summ = summarize(rows)

    write_summary_csv(summ, args.out_csv)

    tex = latex_table(summ, caption=args.caption, label=args.label)
    args.out_tex.parent.mkdir(parents=True, exist_ok=True)
    args.out_tex.write_text(tex, encoding="utf-8")


if __name__ == "__main__":
    main()

