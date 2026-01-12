mod cfg;
use std::env::{self, args};
use std::fmt::Debug;
use cfg::{Cfg};
mod air;
use air::*;
use winterfell::{AcceptableOptions, Air, DefaultConstraintCommitment, FieldExtension, ProofOptions, Prover, Trace, TraceTable, crypto::{DefaultRandomCoin, MerkleTree, hashers::Blake3_256}, math::{FieldElement, fields::f64::BaseElement}, verify, VerifierError};
use log::trace;
use crate::{exe_path::{JmpType, parse_execution_path_file}, prover::StarkraProver};
mod prover;

pub fn build_trace(start: BaseElement, steps: usize) -> TraceTable<BaseElement> {
    // One column, `steps` rows
    let mut trace = TraceTable::new(1, steps);

    // Fill the column with the recurrence: x_{i+1} = x_i^3 + 42
    trace.fill(
        |state| {
            state[0] = start;
        },
        |_, state| {
            state[0] = state[0].exp(3u32.into()) + BaseElement::new(42);
        },
    );

    trace
}

mod exe_path;
use std::time::Instant;

fn fmt_bytes(n: usize) -> String {
    const KB: f64 = 1024.0;
    const MB: f64 = KB * 1024.0;
    const GB: f64 = MB * 1024.0;
    let n_f = n as f64;
    if n_f >= GB {
        format!("{:.2} GiB ({} bytes)", n_f / GB, n)
    } else if n_f >= MB {
        format!("{:.2} MiB ({} bytes)", n_f / MB, n)
    } else if n_f >= KB {
        format!("{:.2} KiB ({} bytes)", n_f / KB, n)
    } else {
        format!("{} bytes", n)
    }
}


pub fn print_trace_table_with_headers(trace: &TraceTable<BaseElement>, max_succ: usize) {
    let width = trace.width();
    let length = trace.length();

    // ---- build header names ----
    let mut headers = Vec::new();
    headers.push("nonce".to_string());
    headers.push("current".to_string());
    headers.push("stack".to_string());

    for i in 0..max_succ {
        headers.push(format!("nei{}", i));
    }

    headers.push("valid".to_string());
    headers.push("ret".to_string());
    headers.push("call".to_string());

    assert_eq!(headers.len(), width, "header/width mismatch");

    // ---- print headers ----
    print!("row |");
    for h in &headers {
        print!(" {:>7} |", h);
    }
    println!();

    // ---- separator ----
    print!("----+");
    for _ in &headers {
        print!("---------+");
    }
    println!();

    // ---- print rows ----
    for r in 0..length {
        print!("{:>3} |", r);
        for c in 0..width {
            let v = trace.get(c, r).as_int();
            print!(" {:>7} |", v);
        }
        println!();
    }
}


fn main() {
    let args: Vec<String> = env::args().collect();
    let cfg = Cfg::from_file(args[1].as_str()).expect("error cfg");
    let (path, a, b) = parse_execution_path_file(args[2].as_str()).expect("error");

    let num_queries: usize = args.get(3)
        .and_then(|s| s.parse().ok())
        .unwrap_or(20);   // default value

    let blowup_factor: usize = args.get(4)
        .and_then(|s| s.parse().ok())
        .unwrap_or(64);    // default value

    let grinding_factor: u32 = args.get(5)
        .and_then(|s| s.parse().ok())
        .unwrap_or(0);     // default value

    println!("num_queries = {}", num_queries);
    println!("blowup_factor = {}", blowup_factor);
    println!("grinding_factor = {}", grinding_factor);

    let t_build_start = Instant::now();
    let trace = StarkraAir::build_trace(path, cfg.clone(), 123);
    let build_dur = t_build_start.elapsed();
    println!("Trace built in {:.3?}", build_dur);

    print_trace_table_with_headers(&trace, cfg.max_successors());
    // 2) public inputs
    let public_inputs = PublicInputs{
        start: BaseElement::from(a.expect("Error Start")),
        end:   BaseElement::from(b.expect("Error End")),
        nonce: BaseElement::new(123),
    };

    // 3) prover/options
    let options = ProofOptions::new(
        num_queries,
        blowup_factor,
        grinding_factor,
        FieldExtension::Cubic,
        4,
        255,
        winterfell::BatchingMethod::Linear,
        winterfell::BatchingMethod::Linear,
    );
    let prover = StarkraProver::new(options);

    // 4) generate proof (timed)
    let t_prove_start = Instant::now();
    let proof = Prover::prove(&prover, trace).expect("prove");
    let prove_dur = t_prove_start.elapsed();
    println!("Proving time: {:.3?}", prove_dur);

    // 4.1) proof size (and basic check)
    let proof_bytes = proof.to_bytes();
    let proof_len = proof_bytes.len();
    println!("Proof size: {}", fmt_bytes(proof_len));


    // 5) verify (timed)
    let min_security = AcceptableOptions::MinConjecturedSecurity(128);
    let t_verify_start = Instant::now();
    match verify::<
        StarkraAir,
        Blake3_256<BaseElement>,
        DefaultRandomCoin<Blake3_256<BaseElement>>,
        MerkleTree<Blake3_256<BaseElement>>,
    >(proof, public_inputs, &min_security) {
        Ok(_) => {println!("Valid Proof")}
        Err(_) => {println!("Failed to verify proof")}
    }
    let verify_dur = t_verify_start.elapsed();
    println!(" Verification succeeded in {:.3?}", verify_dur);

    // 6) summary line
    println!(
        "Done. Trace build: {:.3?} | Prove: {:.3?} | Verify: {:.3?} | Proof: {}",
        build_dur, prove_dur, verify_dur, fmt_bytes(proof_len)
    );
}

