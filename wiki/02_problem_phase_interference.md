# The Problem: Phase Interference in LLM Serving

## The Core Issue
Current LLM serving systems (vLLM, TGI, DeepSpeed-MII) colocate prefill and decoding on the same GPUs. This causes three fundamental problems:

## Problem 1: Prefill-Decoding Interference

### How it manifests
When a prefill job is added to a batch of decoding requests:
- **Decoding slows down**: Decoding tasks must wait for the prefill to complete, increasing TPOT
  - With input length 128: decoding latency increases from ~5ms to ~15ms (3x slower)
  - With input length 1024: decoding latency increases from ~5ms to ~25ms (5x slower)
- **Prefill slows down**: Adding decoding jobs to a prefill batch also increases TTFT
  - At capacity: prefill execution time increases significantly

### Evidence from DistServe (Figure 2)
- Adding ONE prefill job to a decode-only batch causes marked increases in both TTFT and TPOT
- The interference grows worse with longer input lengths
- Even scheduling them separately (not batched together) causes queuing delays

### Evidence from Splitwise (Figure 4)
- Active batch tokens are very low most of the time (60-70% of time: ≤20 tokens)
- Token generation machines are severely underutilized
- Mixed continuous batching wastes GPU resources

## Problem 2: Resource and Parallelism Coupling

### The dilemma
- Prefill prefers **intra-op (tensor) parallelism** at low request rates → reduces execution time → better TTFT
- Decoding prefers **inter-op (pipeline) parallelism** for throughput scaling → better TPOT at scale
- When colocated, you must pick ONE parallelism strategy for both → suboptimal for at least one phase

### From DistServe's analysis (Figure 4a)
- At low arrival rates: intra-op is better for TTFT
- At high arrival rates: inter-op becomes better (queuing delay dominates)
- The crossover point depends on the model, hardware, and SLO requirements
- **You can't optimize for both simultaneously when they share GPUs**

## Problem 3: Over-provisioning

### The consequence
- To meet BOTH TTFT and TPOT SLOs simultaneously on colocated systems:
  - Must over-provision GPUs to handle worst-case interference
  - On a single A100 with OPT-13B: max goodput is ~1.6 req/s (DistServe Figure 1)
  - With disaggregation: 5.6 rps prefill + 10 rps decode → 3.3 rps per GPU (2.1x better)
- Real cost impact: cloud GPU costs are $17-38/hr per machine
- Over-provisioning directly translates to wasted money

## Why Existing Mitigations Fall Short

### Chunked Prefill (Sarathi)
- Splits long prefills into chunks, piggybacks decode tokens
- **Problems**:
  - If chunk size too small: GPU not saturated, prefill takes longer
  - If chunk size too large: no room for decode tokens
  - KV-cache must be reloaded for each chunk: O(N^2) memory access overhead
  - Still fundamentally colocates the two phases

### Priority Scheduling
- Prioritize one phase over the other
- **Problems**:
  - Prioritizing prefill → decoding starved → bad TPOT
  - Prioritizing decoding → prefill queued → bad TTFT
  - No way to satisfy both simultaneously

### The Solution: Disaggregation
Both Splitwise and DistServe independently arrived at the same insight:
> **Separate the two phases onto different hardware to eliminate interference entirely**

This enables:
1. No interference between phases
2. Independent parallelism strategies per phase
3. Independent resource allocation per phase
4. Better GPU utilization (right-size hardware for each phase)
5. Independent scaling of each phase
