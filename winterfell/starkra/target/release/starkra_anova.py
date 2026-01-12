#!/usr/bin/env python3
"""
starkra_anova.py

Analysis script for starkra benchmark:

- Reads CSV produced by bench_starkra.py
- Computes 2-way ANOVA:
    metric ~ C(path_len) + C(max_neighbors) + C(path_len):C(max_neighbors)
- Checks ANOVA assumptions:
    - Normality of residuals (Shapiro–Wilk, QQ plot, histogram)
    - Homoscedasticity (Levene, Bartlett)
    - Independence (Durbin–Watson)
- Produces interaction plots for each metric.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from statsmodels.formula.api import ols
import statsmodels.api as sm

from scipy.stats import shapiro, levene, bartlett
from statsmodels.stats.stattools import durbin_watson


# ========================= Data loading =========================

def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Ensure path_len exists
    if "path_len" not in df.columns:
        df["path_len"] = df["n_nodes"] - 1

    # Filter successful runs (if column exists)
    if "return_code" in df.columns:
        df = df[df["return_code"] == 0]

    return df


# ========================= ANOVA =========================

def run_two_way_anova(df: pd.DataFrame, outdir: Path, metric: str):
    """
    Run 2-way factorial ANOVA for a given metric:
        metric ~ C(path_len) + C(max_neighbors) + C(path_len):C(max_neighbors)
    Saves ANOVA table to CSV and prints it.
    Returns the fitted OLS model and the filtered data used.
    """
    print(f"\n====== ANOVA for {metric} ======")

    d = df.dropna(subset=[metric, "path_len", "max_neighbors"]).copy()
    d["path_len"] = d["path_len"].astype(int).astype("category")
    d["max_neighbors"] = d["max_neighbors"].astype(int).astype("category")

    formula = f"{metric} ~ C(path_len) + C(max_neighbors) + C(path_len):C(max_neighbors)"
    model = ols(formula, data=d).fit()
    anova_table = sm.stats.anova_lm(model, typ=2)

    # Save table
    csv_file = outdir / f"anova_{metric}.csv"
    anova_table.to_csv(csv_file)
    print(f"ANOVA table saved → {csv_file}")
    print(anova_table)

    return model, d


# ========================= Assumption checks =========================

def check_anova_assumptions(model, df_metric: pd.DataFrame, metric: str, outdir: Path):
    """
    Perform standard ANOVA diagnostics:
        - Normality of residuals
        - Homoscedasticity (equal variances)
        - Independence of residuals

    Generates:
        - QQ plot of residuals
        - Histogram of residuals
    """
    print(f"\n=== Checking ANOVA Assumptions for {metric} ===")

    residuals = model.resid

    # ------------------- Normality of residuals -------------------
    stat, p = shapiro(residuals)
    print(f"Shapiro–Wilk normality test: p = {p:.4g}")
    if p < 0.05:
        print("⚠ Residuals are NOT normally distributed (p < 0.05)")
    else:
        print("✔ Residuals appear normally distributed (p ≥ 0.05)")

    # QQ Plot
    plt.figure()
    sm.qqplot(residuals, line='45', fit=True)
    plt.title(f"QQ Plot of Residuals ({metric})")
    qq_path = outdir / f"qqplot_{metric}.png"
    plt.savefig(qq_path)
    plt.close()
    print(f"QQ plot saved → {qq_path}")

    # Histogram of residuals
    plt.figure()
    plt.hist(residuals, bins=30, density=True, alpha=0.7)
    plt.title(f"Residual Distribution ({metric})")
    hist_path = outdir / f"residual_hist_{metric}.png"
    plt.savefig(hist_path)
    plt.close()
    print(f"Residual histogram saved → {hist_path}")

    # ------------------- Homoscedasticity -------------------
    # Group original metric by (path_len, max_neighbors)
    # This tests equal variances across cells
    groups = []
    for (_, _), grp in df_metric.groupby(["path_len", "max_neighbors"]):
        vals = grp[metric].dropna()
        if len(vals) > 1:  # need at least two per group
            groups.append(vals)

    if len(groups) >= 2:
        # Levene test (robust)
        stat, p = levene(*groups)
        print(f"Levene test (equal variances): p = {p:.4g}")
        if p < 0.05:
            print("⚠ Variances are NOT equal (heteroscedastic, p < 0.05)")
        else:
            print("✔ Variances appear equal (homoscedastic, p ≥ 0.05)")

        # Bartlett test (more sensitive, assumes normality)
        stat, p = bartlett(*groups)
        print(f"Bartlett test: p = {p:.4g}")
        if p < 0.05:
            print("⚠ Bartlett also suggests unequal variances (p < 0.05)")
        else:
            print("✔ Bartlett suggests variances are equal (p ≥ 0.05)")
    else:
        print("Not enough groups with ≥2 samples for Levene/Bartlett tests.")

    # ------------------- Independence -------------------
    dw = durbin_watson(residuals)
    print(f"Durbin–Watson statistic = {dw:.3f}")
    print("Interpretation:")
    print("  ≈2.0 → residuals roughly independent")
    print("  <1.5 → positive autocorrelation")
    print("  >2.5 → negative autocorrelation")

    print("=====================================================")


# ========================= Interaction plots =========================

def interaction_plot_metric(df: pd.DataFrame,
                            x_factor: str,
                            trace_factor: str,
                            metric: str,
                            out_path: Path,
                            xlabel: str,
                            ylabel: str,
                            title: str):
    """
    Create an interaction plot:
        x-axis: levels of x_factor (numeric)
        separate lines: levels of trace_factor
        y-axis: mean(metric)
    """
    d = df.dropna(subset=[metric, x_factor, trace_factor]).copy()
    d[x_factor] = d[x_factor].astype(int)
    d[trace_factor] = d[trace_factor].astype(int)

    grouped = (
        d.groupby([x_factor, trace_factor])[metric]
        .mean()
        .reset_index()
    )

    pivot = grouped.pivot(index=x_factor, columns=trace_factor, values=metric)
    pivot = pivot.sort_index().sort_index(axis=1)

    plt.figure()
    for trace_val in pivot.columns:
        plt.plot(
            pivot.index,
            pivot[trace_val],
            marker="o",
            label=f"{trace_factor}={trace_val}"
        )

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.legend(title=trace_factor)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Interaction plot saved → {out_path}")


# ========================= Main =========================

def main():
    parser = argparse.ArgumentParser(
        description="Two-way ANOVA and interaction plots for starkra benchmarks."
    )
    parser.add_argument(
        "csv",
        type=str,
        help="Input CSV file produced by bench_starkra.py"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="analysis_anova",
        help="Directory to store ANOVA tables, diagnostics, and interaction plots."
    )

    args = parser.parse_args()
    csv_path = Path(args.csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Load raw per-run data
    df = load_data(csv_path)

    # Ensure required columns exist
    for col in ["path_len", "max_neighbors", "prove_ms", "verify_ms", "proof_bits"]:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in CSV.")

    # ---------- Two-way ANOVA + assumption checks ----------

    print("\n=== Running Two-Way ANOVA and assumption checks ===")

    model_prove, df_prove = run_two_way_anova(df, outdir, "prove_ms")
    check_anova_assumptions(model_prove, df_prove, "prove_ms", outdir)

    model_verify, df_verify = run_two_way_anova(df, outdir, "verify_ms")
    check_anova_assumptions(model_verify, df_verify, "verify_ms", outdir)

    model_bits, df_bits = run_two_way_anova(df, outdir, "proof_bits")
    check_anova_assumptions(model_bits, df_bits, "proof_bits", outdir)

    # ---------- Interaction plots ----------

    # 1) Metric vs path_len, separate lines for max_neighbors
    interaction_plot_metric(
        df,
        x_factor="path_len",
        trace_factor="max_neighbors",
        metric="prove_ms",
        out_path=outdir / "interaction_prove_path_neighbors.png",
        xlabel="Path length (number of jumps)",
        ylabel="Prove time (ms)",
        title="Interaction: Prove time vs path_len × max_neighbors",
    )

    interaction_plot_metric(
        df,
        x_factor="path_len",
        trace_factor="max_neighbors",
        metric="verify_ms",
        out_path=outdir / "interaction_verify_path_neighbors.png",
        xlabel="Path length (number of jumps)",
        ylabel="Verify time (ms)",
        title="Interaction: Verify time vs path_len × max_neighbors",
    )

    interaction_plot_metric(
        df,
        x_factor="path_len",
        trace_factor="max_neighbors",
        metric="proof_bits",
        out_path=outdir / "interaction_proof_bits_path_neighbors.png",
        xlabel="Path length (number of jumps)",
        ylabel="Proof size (bits)",
        title="Interaction: Proof size vs path_len × max_neighbors",
    )

    # 2) Metric vs max_neighbors, separate lines for path_len
    interaction_plot_metric(
        df,
        x_factor="max_neighbors",
        trace_factor="path_len",
        metric="prove_ms",
        out_path=outdir / "interaction_prove_neighbors_path.png",
        xlabel="Max neighbors per node",
        ylabel="Prove time (ms)",
        title="Interaction: Prove time vs max_neighbors × path_len",
    )

    interaction_plot_metric(
        df,
        x_factor="max_neighbors",
        trace_factor="path_len",
        metric="verify_ms",
        out_path=outdir / "interaction_verify_neighbors_path.png",
        xlabel="Max neighbors per node",
        ylabel="Verify time (ms)",
        title="Interaction: Verify time vs max_neighbors × path_len",
    )

    interaction_plot_metric(
        df,
        x_factor="max_neighbors",
        trace_factor="path_len",
        metric="proof_bits",
        out_path=outdir / "interaction_proof_bits_neighbors_path.png",
        xlabel="Max neighbors per node",
        ylabel="Proof size (bits)",
        title="Interaction: Proof size vs max_neighbors × path_len",
    )

    print("\nDone. Results in:", outdir)


if __name__ == "__main__":
    main()

