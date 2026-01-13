#!/usr/bin/env bash
set -euo pipefail

# Benches
BENCHES="aha-mont64 crc32 cubic edn matmult-int nbody nsichneu slre statemate ud"

OUT="times_summary.csv"

# New CSV header
echo "bench,run,num_queries,blowup_factor,grinding_factor,trace_build,prove,verify,proof_kib,proof_bytes" > "$OUT"

for bench in $BENCHES; do
  for run in 1 2 3 4 5; do
    log="/home/rpi/starkra/winterfell/starkra/target/release/logs/$bench/run_$run/stdout.log"
    [ -f "$log" ] || continue

    awk -v bench="$bench" -v run="$run" -v OUT="$OUT" '
      BEGIN {
        num_queries = ""
        blowup_factor = ""
        grinding_factor = ""
      }

      # Capture params anywhere in the log (only first occurrence kept)
      /^num_queries[[:space:]]*=[[:space:]]*/ {
        if (num_queries == "") {
          num_queries = $0
          sub(/^num_queries[[:space:]]*=[[:space:]]*/, "", num_queries)
          gsub(/[[:space:]]+$/, "", num_queries)
        }
        next
      }

      /^blowup_factor[[:space:]]*=[[:space:]]*/ {
        if (blowup_factor == "") {
          blowup_factor = $0
          sub(/^blowup_factor[[:space:]]*=[[:space:]]*/, "", blowup_factor)
          gsub(/[[:space:]]+$/, "", blowup_factor)
        }
        next
      }

      /^grinding_factor[[:space:]]*=[[:space:]]*/ {
        if (grinding_factor == "") {
          grinding_factor = $0
          sub(/^grinding_factor[[:space:]]*=[[:space:]]*/, "", grinding_factor)
          gsub(/[[:space:]]+$/, "", grinding_factor)
        }
        next
      }

      # Final summary line (this is the reliable one)
      /^Done\. Trace build:/ {
        line = $0
        sub(/^Done\. /, "", line)

        n = split(line, p, /\|/)

        # Trace build
        tb = p[1]
        sub(/^Trace build:[[:space:]]*/, "", tb)
        gsub(/[[:space:]]+$/, "", tb)
        trace_build = tb

        # Prove
        pr = (n >= 2 ? p[2] : "")
        sub(/^[[:space:]]*Prove:[[:space:]]*/, "", pr)
        gsub(/[[:space:]]+$/, "", pr)
        prove = pr

        # Verify
        vr = (n >= 3 ? p[3] : "")
        sub(/^[[:space:]]*Verify:[[:space:]]*/, "", vr)
        gsub(/[[:space:]]+$/, "", vr)
        verify = vr

        # Proof
        pf = (n >= 4 ? p[4] : "")
        sub(/^[[:space:]]*Proof:[[:space:]]*/, "", pf)
        gsub(/[[:space:]]+$/, "", pf)
        # pf: "45.60 KiB (46699 bytes)"

        proof_kib = ""
        proof_bytes = ""

        if (pf != "") {
          # KiB value (first token)
          split(pf, c, /[[:space:]]+/)
          proof_kib = c[1]

          # Bytes: try to extract the number inside "(... bytes)"
          # Safer than relying on c[3] only.
          if (match(pf, /\([0-9]+[[:space:]]*bytes\)/)) {
            bytes_str = substr(pf, RSTART, RLENGTH)   # "(46699 bytes)"
            gsub(/[()]/, "", bytes_str)               # "46699 bytes"
            sub(/[[:space:]]*bytes$/, "", bytes_str)  # "46699"
            gsub(/[[:space:]]+$/, "", bytes_str)
            proof_bytes = bytes_str
          }
        }

        # Output CSV line
        printf "\"%s\",\"%d\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"\n",
          bench, run,
          num_queries, blowup_factor, grinding_factor,
          trace_build, prove, verify, proof_kib, proof_bytes >> OUT
      }
    ' "$log"

  done
done

