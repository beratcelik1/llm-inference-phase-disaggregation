# Phase Disaggregation in Large Language Model Inference

A comprehensive analysis of prefill-decode disaggregation techniques for optimizing LLM serving systems. This repository contains a structured knowledge base examining how separating the compute-intensive prompt computation phase from the memory-bound token generation phase can improve throughput, latency, cost, and power efficiency in production LLM deployments.

## Papers Analyzed

- **Splitwise**: *Efficient Generative LLM Inference Using Phase Splitting* (Patel et al., ISCA 2024) — Heterogeneous hardware allocation for phase-specific resource optimization. [arXiv:2311.18677](https://arxiv.org/abs/2311.18677)

- **DistServe**: *Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving* (Zhong et al., OSDI 2024) — Goodput-optimal placement and parallelism co-optimization. [arXiv:2401.09670](https://arxiv.org/abs/2401.09670)

## Repository Structure

```
wiki/                          # Knowledge base articles
  01_llm_inference_background  # Transformer inference, KV-cache, GPU hardware
  02_problem_phase_interference # Why colocating prefill/decode fails
  03_splitwise_deep_dive       # Characterization, architecture, evaluation
  04_distserve_deep_dive       # Goodput optimization, placement algorithms
  05_comparison                # Side-by-side analysis
  06_related_systems           # vLLM, Sarathi, Orca, SGLang landscape

presentation/                  # Slide deck and speaker notes
research_notes.md              # Extended literature review
```

## Key Findings

1. **Prefill and decoding have fundamentally different computational profiles** — prefill is compute-bound (high arithmetic intensity), decoding is memory-bandwidth-bound
2. **Colocating phases causes 2-5x interference** — adding one prefill job to a decode batch causes significant latency degradation for both phases
3. **KV-cache transfer overhead is negligible** — <0.1% of E2E latency with optimized per-layer transfer on modern interconnects
4. **Disaggregation enables 2-7x goodput improvement** — through independent parallelism strategies, resource allocation, and hardware matching per phase
5. **Heterogeneous hardware further reduces cost** — token generation can run on cheaper/older GPUs (A100 vs H100) with minimal performance impact

## Contributors

- [Berat Celik](https://github.com/beratcelik) — Splitwise analysis
- [Ethan Chen](https://github.com/ethanchen143) — DistServe analysis
