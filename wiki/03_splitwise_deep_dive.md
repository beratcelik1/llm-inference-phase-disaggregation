# Splitwise Deep Dive

**Paper**: "Splitwise: Efficient Generative LLM Inference Using Phase Splitting"
**Authors**: Pratyush Patel, Esha Choukse, Chaojie Zhang, Aashaka Shah, Inigo Goiri, Saeed Maleki, Ricardo Bianchini
**Affiliation**: University of Washington + Microsoft
**arXiv**: 2311.18677v2 (May 2024)
**Venue**: Published at ISCA 2024

## Key Contribution
Splitwise proposes splitting LLM inference phases onto **separate machines**, enabling **heterogeneous hardware** deployment. Unlike DistServe which focuses on software-level disaggregation within homogeneous clusters, Splitwise takes a hardware-aware approach, exploring which GPU types are best suited for each phase.

## Unique Methodology: Production Trace Characterization

### Data Source
- Production traces from **two Azure LLM inference services** (November 2023)
- Two workload types: **coding** and **conversation**
- 20-minute traces with arrival times, input sizes, output sizes
- Real-world data, not synthetic benchmarks

### 7 Key Insights from Characterization

**Insight I**: Different inference services have widely different prompt and token distributions
- Coding: median 1500 prompt tokens, 13 output tokens
- Conversation: median 1020 prompt tokens, 129 output tokens

**Insight II**: Mixed continuous batching spends most time with very few active tokens
- 60-70% of time running ≤20 tokens for conversation
- Coding even worse (very few output tokens)
- Token generation machines are severely underutilized

**Insight III**: For most requests, the majority of E2E time is spent in token generation
- Even for coding (large prompts, few outputs): prompt phase with 1500 tokens ≈ token phase with 6 tokens on BLOOM-176B
- Token generation dominates wall-clock time

**Insight IV**: Prompt phase batch size should be limited; token phase batching scales well
- Prompt throughput plateaus after ~2048 tokens per batch (compute saturated)
- Token throughput keeps scaling until memory runs out

**Insight V**: Prompt phase is compute-bound; token phase is memory-capacity-bound
- Different bottlenecks → different hardware requirements

**Insight VI**: Prompt phase utilizes power budget efficiently; token phase does not
- Prompt: power draw scales with batch size, near TDP
- Token: power draw flat regardless of batch size, well below TDP

**Insight VII**: Token generation can run on less compute-capable hardware
- A100 vs H100 comparison: TBT ratio is only 0.70x (vs 0.51x for TTFT)
- Token phase barely benefits from H100's 3.43x compute advantage
- **A100 is actually more cost-efficient for token generation**

## Splitwise Architecture

### Three Machine Pools
1. **Prompt Pool**: Machines dedicated to processing prompts (compute-heavy GPUs)
2. **Token Pool**: Machines dedicated to token generation (can use cheaper/older GPUs)
3. **Mixed Pool**: Flexible machines that can handle either phase (overflow/load balancing)

### Two-Level Scheduling

#### Cluster-Level Scheduler (CLS)
- Manages machine pool sizes (can re-purpose machines between pools)
- Routes requests using **Join-the-Shortest-Queue (JSQ)** scheduling
- Assigns both a prompt machine and token machine simultaneously
- Overlaps KV-cache transfer with prompt computation to hide latency
- Handles overflow: when queues exceed threshold, uses mixed pool machines

#### Machine-Level Scheduler (MLS)
- Runs on each machine, tracks GPU memory utilization
- Manages pending queue and batching decisions
- **Prompt machines**: FCFS, batch up to 2048 tokens total
- **Token machines**: FCFS, batch as much as memory allows (continuous batching)
- **Mixed machines**: Prioritize prompts (for TTFT SLO), preempt tokens if needed
  - Age-based priority to prevent token starvation

### KV-Cache Transfer Optimization

#### Naive (Serialized) Transfer
- Wait for entire prompt phase to complete
- Transfer full KV-cache to token machine
- Then start token generation
- **Problem**: Adds significant latency to TBT for the second token

#### Optimized (Per-Layer) Transfer
- As each layer computes during prompt phase, immediately transfer that layer's KV-cache
- Uses MSCCL++ zero-copy one-sided `put` over InfiniBand
- Transfer happens **in parallel** with computation of next layers
- Result: constant ~5-8ms non-overlapped transfer time (vs linear growth with serialized)
- For small prompts (<512 tokens on H100): use serialized (simpler, total KV-cache is small)
- For large prompts: use per-layer (hides most transfer latency)

#### Transfer Overhead (measured)
- Per-layer: ~0.8% of E2E latency
- Serialized: up to 3% of E2E for large prompts
- For the second token specifically: 16.5% overhead (per-layer) vs 64% (serialized)
- **Overall: transfer is NOT the bottleneck** on modern GPU clusters

## Cluster Design Exploration

### Four Splitwise Variants

| Design | Prompt GPU | Token GPU | Cost | Power |
|--------|-----------|-----------|------|-------|
| Splitwise-AA | DGX-A100 | DGX-A100 | 1x | 1x |
| Splitwise-HH | DGX-H100 | DGX-H100 | 2.35x | 1.75x |
| Splitwise-HA | DGX-H100 | DGX-A100 | mixed | mixed |
| Splitwise-HHcap | DGX-H100 | H100 @70% power | 2.35x | 1.23x |

### Key Results

#### Iso-Power Throughput-Optimized (same power budget, conversation trace)
- **Splitwise-AA**: 2.15x more throughput than Baseline-A100 at same cost and power
- **Splitwise-HH**: Better latency across all metrics
- **Splitwise-HHcap**: Best latency overall (token machines at 70% power = no latency impact)
- **Splitwise-HA**: 1.18x more throughput at 10% lower cost

#### Iso-Cost Throughput-Optimized
- **Splitwise-AA**: 1.4x more throughput than Baseline-H100 at same cost
- Uses 2x the space but older, cheaper A100 GPUs
- Interesting for customers who don't care about power/space

#### Iso-Throughput Power-Optimized
- **Splitwise-HHcap**: Same throughput as Baseline-H100 at **25% lower power**
- Clear win for CSPs trying to reduce datacenter power

#### Iso-Throughput Cost-Optimized
- **Splitwise-AA**: Same throughput as Baseline-H100 at **25% lower cost**

### Summary of Splitwise Results
- **1.4x higher throughput** at 20% lower cost
- OR **2.35x more throughput** at same cost and power
- **1.76x better throughput** with 15% lower power
- Robust to workload changes (7% throughput setback when wrong workload)
- Robust to model changes (LLaMA-70B on BLOOM-176B cluster still works well)

## Practical Considerations

### Accuracy Impact
- **Zero impact**: Splitwise uses lossless KV-cache transfer
- Same parameters and state as single-machine inference

### Scalability
- LLM requests are longer than typical ML requests → scheduling overhead is manageable
- CLS could become bottleneck at very large scale → partitioned/replicated scheduling

### Fault Tolerance
- If prompt or token machine fails: restart from scratch (same as existing systems)
- Could checkpoint KV-cache after prompt phase for faster recovery
- Future work: periodic KV-cache checkpointing during token phase

### Extensibility
- Applicable to ALL modern transformer-based generative LLMs
- Works with MoE (Mixture of Experts) models
- Hardware-agnostic: could use CPUs, FPGAs, ASICs, AMD GPUs for token machines
