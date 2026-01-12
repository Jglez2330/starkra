#!/usr/bin/env python3
import argparse
import subprocess
import time
import csv
import re
from pathlib import Path

# -------------------------- Parsing -----------------------------

def parse_time_ms(label: str, text: str):
    """
    Parse a time like:
      'Prove: 2.283ms'
      'Verify: 169.891µs'
      'Prove: 0.5s'
    and return milliseconds (float) or None.
    """
    pattern = rf"{label}:\s*([0-9.]+)\s*([uµμ]?s|ms|s)"
    m = re.search(pattern, text)
    if not m:
        return None

    value = float(m.group(1))
    unit = m.group(2)

    if unit in ("us", "µs", "μs"):
        return value / 1000.0      # µs → ms
    elif unit == "ms":
        return value               # already ms
    elif unit == "s":
        return value * 1000.0      # s → ms
    else:
        return None


PROOF_RE = re.compile(r"Proof:\s*.*\((\d+)\s*bytes\)")


def parse_output(stdout: str):
    """
    Extract prove_ms, verify_ms, proof_bits from the command stdout.
    All times in ms, proof size in bits.
    """
    prove_ms = parse_time_ms("Prove", stdout)
    verify_ms = parse_time_ms("Verify", stdout)

    proof_bytes = None
    m = PROOF_RE.search(stdout)
    if m:
        proof_bytes = int(m.group(1))
    proof_bits = proof_bytes * 8 if proof_bytes is not None else None

    return prove_ms, verify_ms, proof_bits


# -------------------------- CFG Generation -----------------------------

def build_cfg_with_neighbors(n_nodes: int, neighbor_count: int):
    """
    Build a CFG where each node has exactly 'neighbor_count' outgoing edges.
    The actual neighbor *values* don't matter (they can all be 0); only the
    number of neighbors per node is important.

    So for n_nodes = 5, neighbor_count = 4, one possible adjacency is:

      0 -> 0,0,0,0
      1 -> 0,0,0,0
      2 -> 0,0,0,0
      3 -> 0,0,0,0
      4 -> 0,0,0,0

    We encode this as an *edge list* (one "src dst" per line).
    """
    adj = {i: [] for i in range(n_nodes)}

    for i in range(n_nodes):
        for _ in range(neighbor_count):
            adj[i].append(0)  # always 0; we only care about count

    return adj


def write_numified_files(n_nodes: int, neighbor_count: int):
    """
    Write:
      - numified_adjlist : edge list with 'neighbor_count' outgoing edges per node
      - numified_path    : linear path 0 -> 1 -> ... -> n-1 (same as before)
    """
    adjlist = build_cfg_with_neighbors(n_nodes, neighbor_count)

    # Execution path: still a simple chain 0→1→...→n-1
    with open("numified_path", "w") as f:
        f.write(f"initial_node=0 final_node={n_nodes - 1}\n")
        for edge_id in range(1, n_nodes):
            f.write(f"jump {edge_id}\n")

    # Adjacency as edge list: one "src dst" per line
    with open("numified_adjlist", "w") as f:
        for src in range(n_nodes):
            for dst in adjlist[src]:
                f.write(f"{src} {dst}\n")


# -------------------------- Execution -----------------------------

def run_starkra(executable: str):
    start = time.perf_counter()
    proc = subprocess.run(
        [executable, "numified_adjlist", "numified_path"],
        text=True,
        capture_output=True
    )
    elapsed = time.perf_counter() - start
    return elapsed, proc.returncode, proc.stdout, proc.stderr


# -------------------------- MAIN -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark starkra over CFGs of size 2^k and increasing neighbors."
    )

    parser.add_argument("--min_power", type=int, default=4,
                        help="Minimum k for n = 2^k.")
    parser.add_argument("--max_power", type=int, default=10,
                        help="Maximum k for n = 2^k.")
    parser.add_argument("--min_neighbors", type=int, default=1,
                        help="Minimum number of neighbors per node.")
    parser.add_argument("--max_neighbors", type=int, default=4,
                        help="Maximum number of neighbors per node.")
    parser.add_argument("--reps", type=int, default=5,
                        help="Number of runs per (k, neighbors).")
    parser.add_argument("--exec", type=str, default="./starkra",
                        help="Path to starkra executable.")
    parser.add_argument("--csv", type=str, default="starkra_results.csv",
                        help="Output CSV file.")
    parser.add_argument("--verbose", action="store_true",
                        help="Print per-run details.")

    args = parser.parse_args()

    if args.min_neighbors <= 0:
        raise ValueError("min_neighbors must be >= 1")
    if args.max_neighbors < args.min_neighbors:
        raise ValueError("max_neighbors must be >= min_neighbors")

    csv_path = Path(args.csv)
    new_csv = not csv_path.exists()

    # Open CSV and write header if new
    with csv_path.open("a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if new_csv:
            writer.writerow([
                "power_k",
                "n_nodes",
                "path_len",
                "max_neighbors",
                "run",
                "elapsed_wall_ms",
                "prove_ms",
                "verify_ms",
                "proof_bits",
                "return_code",
            ])

        for k in range(args.min_power, args.max_power + 1):
            n_nodes = 2 ** k
            path_len = n_nodes - 1

            if args.verbose:
                print(f"\n=== k={k}, n={n_nodes}, path_len={path_len} ===")

            # For each path length, sweep neighbors from min_neighbors to max_neighbors
            for neighbor_count in range(args.min_neighbors, args.max_neighbors + 1):
                if args.verbose:
                    print(f"  → neighbors={neighbor_count}")

                # Generate CFG + path
                write_numified_files(n_nodes, neighbor_count)

                # Logs: logs/synth/k/neigh_<neighbor_count>/run_i
                logdir = Path(f"logs/synth/{k}/neigh_{neighbor_count}")
                logdir.mkdir(parents=True, exist_ok=True)

                for run_i in range(1, args.reps + 1):
                    elapsed, rc, stdout, stderr = run_starkra(args.exec)

                    prove_ms, verify_ms, proof_bits = parse_output(stdout)
                    elapsed_ms = elapsed * 1000.0

                    # Save stdout
                    out_file = logdir / f"run_{run_i}"
                    with out_file.open("w") as f:
                        f.write(stdout)

                    # Write CSV row
                    writer.writerow([
                        k,
                        n_nodes,
                        path_len,
                        neighbor_count,
                        run_i,
                        elapsed_ms,
                        prove_ms,
                        verify_ms,
                        proof_bits,
                        rc,
                    ])

                    if args.verbose:
                        print(
                            f"    run={run_i}: wall={elapsed_ms:.3f} ms, "
                            f"prove={prove_ms}, verify={verify_ms}, "
                            f"proof_bits={proof_bits}, rc={rc}"
                        )


if __name__ == "__main__":
    main()

