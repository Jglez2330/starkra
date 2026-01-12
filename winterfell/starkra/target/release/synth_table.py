#!/usr/bin/env python3
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description="Summarize STARK RA results as a LaTeX table."
    )
    parser.add_argument(
        "csv_path",
        help="Path to the CSV file (e.g. starkra_results.csv)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Optional path to write the LaTeX table (.tex). If omitted, prints to stdout.",
    )
    args = parser.parse_args()

    # Read CSV
    df = pd.read_csv(args.csv_path)

    # Group by k and neighbor, compute means
    grouped = (
        df.groupby(["power_k", "max_neighbors"], as_index=False)
          .agg(
              mean_prove_ms=("prove_ms", "mean"),
              mean_verify_ms=("verify_ms", "mean"),
              mean_proof_bits=("proof_bits", "mean"),
          )
    )

    # Make column names LaTeX-friendly / nicer
    grouped = grouped.rename(
        columns={
            "power_k": r"$k$",
            "max_neighbors": r"neighbors",
            "mean_prove_ms": r"$t_{\mathrm{prove}}$ [ms]",
            "mean_verify_ms": r"$t_{\mathrm{verify}}$ [ms]",
            "mean_proof_bits": r"proof bits",
        }
    )

    # Convert to LaTeX tabular (no index, 3 decimal places for floats)
    latex_table = grouped.to_latex(
        index=False,
        escape=False,          # allow LaTeX in column names
        float_format="%.3f".__mod__,
    )

    # Optionally wrap in a table environment; uncomment if you prefer this:
    # latex_table = (
    #     r"\begin{table}[ht]" "\n"
    #     r"\centering" "\n"
    #     r"\caption{Mean proving/verifying time and proof size by $k$ and neighbors.}" "\n"
    #     r"\label{tab:starkra_means}" "\n"
    #     + latex_table + "\n"
    #     r"\end{table}"
    # )

    if args.output:
        with open(args.output, "w") as f:
            f.write(latex_table)
    else:
        print(latex_table)


if __name__ == "__main__":
    main()

