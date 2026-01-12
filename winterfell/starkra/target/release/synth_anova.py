#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.formula.api import ols
from scipy.stats import shapiro, levene

# ============================================================
# Load data
# ============================================================
df = pd.read_csv("starkra_results.csv")

# Ensure factors are treated as categorical
df['power_k'] = df['power_k'].astype(int)
df['max_neighbors'] = df['max_neighbors'].astype(int)

# ============================================================
# Helper: Run ANOVA + assumption tests
# ============================================================

def run_anova(metric):
    print("\n====================================================")
    print(f"ANALYZING METRIC: {metric}")
    print("====================================================\n")

    df[f"log_{metric}"] = np.log10(df[metric])

    # ---------------------------------------------------------
    # Assumption checks
    # ---------------------------------------------------------

    # Shapiro–Wilk test per group
    normality_pass = True
    for (k, n), subset in df.groupby(['power_k', 'max_neighbors']):
        if len(subset) >= 3:
            stat, p = shapiro(subset[f"log_{metric}"])
            if p < 0.05:
                normality_pass = False
        else:
            p = np.nan
        print(f"Shapiro group (k={k}, n={n}): p={p:.4f}")

    print("\nNormality assumption:",
          "PASS" if normality_pass else "FAIL")

    # Levene’s test for variance homogeneity
    groups = [group[f"log_{metric}"].values
              for _, group in df.groupby(['power_k', 'max_neighbors'])]
    stat, p = levene(*groups)
    print(f"\nLevene test p={p:.4f}")
    print("Homogeneity assumption:", "PASS" if p > 0.05 else "FAIL")

    # ---------------------------------------------------------
    # Two–way ANOVA
    # ---------------------------------------------------------
    model = ols(f"log_{metric} ~ C(power_k) + C(max_neighbors) + C(power_k):C(max_neighbors)", data=df).fit()
    anova_table = sm.stats.anova_lm(model, typ=2)
    print("\nANOVA TABLE:")
    print(anova_table)

    # Save as LaTeX
    latex = anova_table.to_latex(float_format="%.4f")
    with open(f"anova_{metric}.tex", "w") as f:
        f.write(latex)

    print(f"LaTeX ANOVA table saved to anova_{metric}.tex")

    return anova_table


# ============================================================
# Helper: Generate interaction plot
# ============================================================

def interaction_plot(metric):
    plt.figure(figsize=(8, 6))

    for n, group in df.groupby("max_neighbors"):
        means = group.groupby("power_k")[metric].mean()
        plt.plot(means.index, means.values, marker="o", label=f"neighbors={n}")

    plt.xlabel("Path length exponent k (path = 2^k)")
    plt.ylabel(metric.replace("_", " "))
    plt.title(f"Interaction plot for {metric}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"interaction_{metric}.png")
    plt.close()

    print(f"Saved interaction plot: interaction_{metric}.png")


# ============================================================
# Helper: Group means + std → LaTeX
# ============================================================

def save_group_stats(metric):
    group = df.groupby(['power_k', 'max_neighbors'])[metric]
    means = group.mean()
    stds = group.std()

    table = pd.DataFrame({
        "mean": means,
        "std": stds
    }).reset_index()

    latex = table.to_latex(index=False, float_format="%.4f")

    with open(f"table_{metric}.tex", "w") as f:
        f.write(latex)

    print(f"Saved LaTeX table: table_{metric}.tex")


# ============================================================
# Execute analysis for all three metrics
# ============================================================

metrics = ["prove_ms", "verify_ms", "proof_bits"]

for m in metrics:
    interaction_plot(m)
    save_group_stats(m)
    run_anova(m)

print("\nAll analysis complete.")

