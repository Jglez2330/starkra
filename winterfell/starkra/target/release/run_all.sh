#!/bin/sh
set -e

# Experiment parameter grids
NUM_QUERIES="32 64 128"
BLOWUP_FACTORS="16 32 64 128"
GRINDINGS="0 2 4 8 16"

# Number of repetitions per (bench, addr, size, num_queries, blowup_factor, grinding)
RUNS=5

# BENCHES variable from your Makefile
BENCHES="huffbench aha-mont64 crc32 cubic edn  matmult-int nbody nsichneu slre statemate ud"

# Address and path/size configurations (some combos may not exist for all benches;
# missing ones will just be skipped with a message).
ADDRS="24"
SIZES="500"

# Root directory that contains all benchmark subdirectories
BENCH_ROOT="/home/joseph.gonzalez/Documents/jgonzalez/STARK-ntt-attesttation/experiments/experiments"

# Where to store logs
BASE="logs"
mkdir -p "$BASE"

for bench in $BENCHES; do
  echo ""
  echo "================================================================="
  echo " Running benchmark: $bench"
  echo "================================================================="

  for addr in $ADDRS; do
    for size in $SIZES; do

      CFG="${BENCH_ROOT}/${bench}/numified_adjlist"
      PTH="${BENCH_ROOT}/${bench}/numified_path"

      if [ ! -f "$CFG" ]; then
        echo "[SKIP] Missing CFG file: $CFG"
        continue
      fi
      if [ ! -f "$PTH" ]; then
        echo "[SKIP] Missing PTH file: $PTH"
        continue
      fi

      echo ""
      echo "[ $bench | ADDR=$addr | SIZE=$size ]"
      echo ""

      # Sweep over experiment parameters
      for nq in $NUM_QUERIES; do
        for bf in $BLOWUP_FACTORS; do
          for gr in $GRINDINGS; do

            echo ""
            echo "  → Params: num_queries=$nq, blowup_factor=$bf, grinding=$gr"
            echo ""

            # Logs organized by bench / addr / size / parameters
            OUTDIR="${BASE}/${bench}/addr_${addr}_size_${size}/q${nq}_b${bf}_g${gr}"
            mkdir -p "$OUTDIR"

            r=1
            while [ "$r" -le "$RUNS" ]; do
              echo "    → Run #$r"

              RUNDIR="${OUTDIR}/run_${r}"
              mkdir -p "$RUNDIR"

              /usr/bin/time -v \
                ./starkra "$CFG" "$PTH" "$nq" "$bf" "$gr" \
                >"${RUNDIR}/stdout.log" 2>"${RUNDIR}/stderr.log"

              r=$((r + 1))
            done

          done
        done
      done

    done
  done
done

