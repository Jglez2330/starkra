#!/usr/bin/env bash

# Benches
BENCHES="aha-mont64 crc32 cubic edn matmult-int nbody nsichneu slre statemate ud"

OUT="times_summary.csv"

# CSV header
echo "bench,run,trace_build,prove,verify,proof_kib,proof_bytes" > "$OUT"

for bench in $BENCHES; do
  for run in 1 2 3 4 5; do
    log="logs/$bench/run_$run/stdout.log"
    [ -f "$log" ] || continue

    awk -v bench="$bench" -v run="$run" -v OUT="$OUT" '
      /Done\. Trace build:/ {
        line = $0

        # Remove leading "Done. "
        sub(/^Done\. /, "", line)

        # Split by "|"
        n = split(line, p, /\|/)

        # p[1]: "Trace build: 41.074µs "
        tb = p[1]
        sub(/^Trace build:[[:space:]]*/, "", tb)
        gsub(/[[:space:]]+$/, "", tb)
        trace_build = tb

        # p[2]: " Prove: 10.023ms "
        pr = (n >= 2 ? p[2] : "")
        sub(/^[[:space:]]*Prove:[[:space:]]*/, "", pr)
        gsub(/[[:space:]]+$/, "", pr)
        prove = pr

        # p[3]: " Verify: 240.442µs "
        vr = (n >= 3 ? p[3] : "")
        sub(/^[[:space:]]*Verify:[[:space:]]*/, "", vr)
        gsub(/[[:space:]]+$/, "", vr)
        verify = vr

        # p[4]: " Proof: 16.85 KiB (17251 bytes)"
        pf = (n >= 4 ? p[4] : "")
        sub(/^[[:space:]]*Proof:[[:space:]]*/, "", pf)
        gsub(/[[:space:]]+$/, "", pf)
        # pf now like: "16.85 KiB (17251 bytes)"

        proof_kib = ""
        proof_bytes = ""

        if (pf != "") {
          split(pf, c, /[[:space:]]+/)
          # c[1] = "16.85", c[2] = "KiB", c[3] = "(17251", ...
          proof_kib = c[1]

          bytes_str = c[3]   # "(17251"
          gsub(/^\(/, "", bytes_str)
          gsub(/\)$/, "", bytes_str)
          proof_bytes = bytes_str
        }

        # Output CSV line
        printf "\"%s\",\"%d\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"\n",
          bench, run,
          trace_build, prove, verify, proof_kib, proof_bytes >> OUT
      }
    ' "$log"

  done
done

