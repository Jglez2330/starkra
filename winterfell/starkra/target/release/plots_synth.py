#!/usr/bin/env python3
import argparse
from pathlib import Path
import numpy as np

import pandas as pd
import matplotlib.pyplot as plt


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["path_len"] = df["n_nodes"] - 1
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["power_k", "n_nodes", "path_len"], as_index=False)
        .agg(
            mean_wall_ms=("elapsed_wall_ms", "mean"),
            mean_prove_ms=("prove_ms", "mean"),
            mean_verify_ms=("verify_ms", "mean"),
            mean_proof_bits=("proof_bits", "mean"),
            runs=("run", "count"),
        )
    )
    return grouped


# ---------------------------------------------------------------------
# Complexity curve helper: scale complexity curve to real data
# ---------------------------------------------------------------------
def scale_curve(x, curve, real_y):
    """
    Scale complexity curve so it visually matches magnitude of data.
    """
    curve = np.array(curve)
    real_y = np.array(real_y)

    # Avoid divide by zero
    if curve.max() == 0:
        return curve

    # scale by ratio of max values
    scale = real_y.max() / curve.max()
    return curve * scale


# ---------------------------------------------------------------------
# Prove plot (with n log n)
# ---------------------------------------------------------------------
def plot_prove(summary: pd.DataFrame, out_path: Path):
    x = summary["path_len"].values
    y = summary["mean_prove_ms"].values

    # Complexity curve: n log n
    nlogn = x * np.log2(x + 1)
    nlogn_scaled = scale_curve(x, nlogn, y)

    plt.figure()
    plt.plot(x, y, marker="o", label="Prove time (mean, ms)")
    plt.plot(x, nlogn_scaled, linestyle="--", label="n log n (scaled)")
    plt.xlabel("Path length (n jumps)")
    plt.ylabel("Prove time (ms)")
    plt.title("Mean Prove Time vs Path Length")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


# ---------------------------------------------------------------------
# Verify plot (with log n)
# ---------------------------------------------------------------------
def plot_verify(summary: pd.DataFrame, out_path: Path):
    x = summary["path_len"].values
    y = summary["mean_verify_ms"].values

    # Complexity curve: log n
    logn = np.log2(x + 1)
    logn_scaled = scale_curve(x, logn, y)

    plt.figure()
    plt.plot(x, y, marker="o", color="orange", label="Verify time (mean, ms)")
    plt.plot(x, logn_scaled, linestyle="--", label="log n (scaled)")
    plt.xlabel("Path length (n jumps)")
    plt.ylabel("Verify time (ms)")
    plt.title("Mean Verify Time vs Path Length")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


# ---------------------------------------------------------------------
# Proof size plot (with log n)
# ---------------------------------------------------------------------
def plot_proof_size(summary: pd.DataFrame, out_path: Path):
    x = summary["path_len"].values
    y = summary["mean_proof_bits"].values

    # Complexity curve: log n
    logn = np.log2(x + 1)
    logn_scaled = scale_curve(x, logn, y)

    plt.figure()
    plt.plot(x, y, marker="o", color="green", label="Proof size (bits)")
    plt.plot(x, logn_scaled, linestyle="--", label="log n (scaled)")
    plt.xlabel("Path length (n jumps)")
    plt.ylabel("Proof size (bits)")
    plt.title("Mean Proof Size vs Path Length")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Analyze starkra benchmark CSV, compute means, and plot."
    )
    parser.add_argument("csv", type=str, help="Input CSV file")
    parser.add_argument("--outdir", type=str, default="analysis",
                        help="Output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_data(Path(args.csv))

    if "return_code" in df.columns:
        df = df[df["return_code"] == 0]  # remove failed runs

    summary = summarize(df)
    (outdir / "starkra_summary.csv").write_text(summary.to_csv(index=False))

    plot_prove(summary, outdir / "prove_vs_path.png")
    plot_verify(summary, outdir / "verify_vs_path.png")
    plot_proof_size(summary, outdir / "proofsize_vs_path.png")

    print("Generated:")
    print(" - prove_vs_path.png (with n log n)")
    print(" - verify_vs_path.png (with log n)")
    print(" - proofsize_vs_path.png (with log n)")
    print("Done.")


if __name__ == "__main__":
    main()

