# Phase Disaggregation for LLM Inference
## Splitwise & DistServe

### ECE 5545: ML Hardware & Systems
### Berat Celik & Jiayang (Ethan) Chen
### Spring 2026

---

# Presentation Outline

**Part 1 — Berat Celik: Splitwise**
- Background: LLM Inference & The Two Phases
- The Problem: Why Colocation Fails
- Splitwise: Phase Splitting with Heterogeneous Hardware
- Evaluation & Results

**Part 2 — Ethan Chen: DistServe**
- DistServe: Goodput-Optimized Disaggregation
- Tradeoff Analysis & Placement Algorithms
- Evaluation & Results
- Comparison, Discussion & Future Directions

---

# ============================================
# PART 1: SPLITWISE (Berat Celik)
# ============================================

---

# Background: How LLM Inference Works

An LLM responds to a query in **two distinct phases**:

**Phase 1 — Prefill (Prompt Computation)**
- Process ALL input tokens in parallel → generate first output token
- Single forward pass through the entire model
- Generates and stores KV-cache for all input tokens

**Phase 2 — Decoding (Token Generation)**
- Generate tokens ONE at a time, autoregressively
- Each step: attend to all previous tokens via KV-cache → produce next token
- Repeat until end-of-sequence or max length

> *Example: "Is tomato a fruit?" → [Prefill: process 5 tokens] → "Yes" → [Decode] → "," → "it" → "is" → "." → [EOS]*

[Reference: Splitwise Figure 1 — LLM inference example showing prompt phase and token generation phase]

---

# The Two Phases Have Fundamentally Different Characteristics

| Property | Prefill (Prompt) | Decoding (Token Gen) |
|----------|-----------------|---------------------|
| **Bottleneck** | Compute-bound | Memory bandwidth-bound |
| **Tokens processed** | All input (parallel) | 1 per step (sequential) |
| **GPU utilization** | HIGH | LOW (without batching) |
| **Power draw** | Near TDP (~700W on H100) | Well below TDP |
| **Key latency metric** | TTFT | TPOT / TBT |
| **Batching benefit** | Limited (already saturated) | Large (improves utilization) |
| **Ideal parallelism** | Tensor parallelism | Pipeline parallelism |

**This asymmetry is the key insight behind both papers.**

[Reference: Splitwise Table IV — A100 vs H100 metrics showing different ratios per phase]

---

# Key Performance Metrics

| Metric | What It Measures | Who Cares |
|--------|-----------------|-----------|
| **TTFT** (Time to First Token) | Latency of prefill phase | User responsiveness |
| **TBT** (Time Between Tokens) | Streaming token latency | Reading experience |
| **TPOT** (Time Per Output Token) | Average decode latency | Similar to TBT |
| **E2E Latency** | TTFT + TPOT × output_len | Total wait time |
| **Throughput** | Requests per second | System capacity |
| **Goodput** | Throughput under SLO | Cost efficiency |

**SLO (Service Level Objective)**: Latency targets the system must meet
- Example: "90% of chatbot requests must have TTFT < 0.25s AND TPOT < 0.1s"

---

# The Problem: Why Colocating Phases Fails

## Problem 1: Prefill-Decoding Interference

When both phases share the same GPU:

- Adding ONE prefill job to a decode batch → **up to 3x slower decoding** (input=128) to **5x** (input=1024)
- Adding decode jobs to a prefill batch → **increased TTFT**
- Even with separate scheduling → queuing delays hurt both

[Reference: DistServe Figure 2 — Batch execution time showing prefill slowdown and decoding slowdown]

**The interference is unavoidable when sharing hardware.**

---

# The Problem (continued)

## Problem 2: Resource & Parallelism Coupling

Prefill wants tensor parallelism (reduce latency) but decoding wants pipeline parallelism (scale throughput).

**When colocated: you must pick ONE strategy → suboptimal for at least one phase.**

## Problem 3: Over-Provisioning

To meet both TTFT and TPOT SLOs simultaneously:
- Must over-provision GPUs to handle worst-case interference
- Single A100 with OPT-13B: only ~1.6 req/s goodput (colocated)
- With disaggregation: **3.3 req/s per GPU** (2.1x improvement)

**The solution: separate the phases onto different hardware entirely.**

---

# Splitwise: Production Trace Characterization

Splitwise starts with a unique advantage: **real Azure production traces** from two LLM inference services.

### Key Findings from Azure Production Data:

**Insight I**: Workloads vary widely
- Coding service: median 1500 prompt tokens, only 13 output tokens
- Conversation service: median 1020 prompt tokens, 129 output tokens

**Insight II**: Token generation machines are severely underutilized
- 60-70% of time running ≤ 20 active tokens in the batch
- GPU resources wasted during token generation phase

**Insight III**: Most E2E time is spent in token generation
- Even for coding (1500 prompt tokens, 6 output tokens): prompt ≈ token time for BLOOM-176B!

[Reference: Splitwise Figure 3 — Distribution of prompt and generated tokens for coding and conversation]

---

# Splitwise: Hardware Insights

**Insight IV**: Prompt batching has diminishing returns; token batching scales well
- Prompt throughput plateaus after ~2048 tokens (GPU saturated)
- Token throughput keeps scaling until memory runs out

**Insight V**: Prompt is compute-bound; Token is memory-capacity-bound

**Insight VI**: Prompt uses GPU power efficiently; Token does not
- Prompt: power draw scales with batch → near TDP
- Token: power draw flat, well below TDP → **wasting expensive power**

**Insight VII — The Key Insight for Splitwise:**

| Metric | A100 | H100 | Ratio |
|--------|------|------|-------|
| TTFT | 185 ms | 95 ms | 0.51x |
| TBT | 52 ms | 31 ms | 0.70x |
| Cost | $0.42 | $0.52 | 1.24x |

> **Token generation barely benefits from H100's 3.43x compute advantage.**
> **A100 is more cost-efficient for token generation!**

---

# Splitwise Design: Three Machine Pools

[Reference: Splitwise Figure 10 — High-level system diagram]

```
                    Cluster-Level Scheduler (CLS)
                           ↙        ↘
              ┌─────────────┐    ┌─────────────┐
              │ Prompt Pool │    │  Token Pool  │
              │   (H100s)   │    │   (A100s)    │
              │  Compute-   │    │  Memory-     │
              │  optimized  │───→│  optimized   │
              └─────────────┘ KV └─────────────┘
                      ↕     cache       ↕
              ┌────────────────────────────────┐
              │         Mixed Pool             │
              │  (Flexible, handles overflow)  │
              └────────────────────────────────┘
```

- **Prompt Pool**: Dedicated to prefill computation (high-compute GPUs)
- **Token Pool**: Dedicated to token generation (cost-efficient GPUs)
- **Mixed Pool**: Handles overflow from either pool, dynamically repurposed

---

# Splitwise: Two-Level Scheduling

### Cluster-Level Scheduler (CLS)
- Manages pool sizes (can re-purpose machines between pools)
- Routes requests via **Join-the-Shortest-Queue (JSQ)**
- Assigns BOTH a prompt machine AND token machine simultaneously
- Overlaps KV-cache transfer with prompt computation

### Machine-Level Scheduler (MLS)
- Per-machine scheduling and memory management
- **Prompt machines**: FCFS, batch ≤ 2048 tokens
- **Token machines**: FCFS, continuous batching until memory full
- **Mixed machines**: Prioritize prompts, preempt tokens with age-based priority

---

# Splitwise: KV-Cache Transfer Optimization

**Challenge**: After prefill, the KV-cache must be sent to the token machine.

### Naive (Serialized) Transfer
- Wait for full prefill → transfer entire KV-cache → start decoding
- Adds up to 64% overhead to second token latency

### Optimized (Per-Layer) Transfer
- As each layer computes, **immediately** send that layer's KV-cache
- Transfer overlaps with computation of subsequent layers
- Uses MSCCL++ zero-copy one-sided `put` over InfiniBand

**Result:**
- Per-layer: only **0.8% of E2E latency** (vs 3% for serialized)
- Second token overhead: **16.5%** (vs 64% serialized)
- Constant ~5-8ms non-overlapped transfer regardless of prompt size

> **KV-cache transfer is NOT the bottleneck on modern GPU clusters.**

[Reference: Splitwise Figure 14 — KV-cache transfer overhead; Figure 15 — E2E latency impact]

---

# Splitwise: Heterogeneous Cluster Designs

| Design | Prompt Machine | Token Machine | Key Tradeoff |
|--------|---------------|---------------|-------------|
| **Splitwise-AA** | DGX-A100 | DGX-A100 | Lowest cost, use older GPUs |
| **Splitwise-HH** | DGX-H100 | DGX-H100 | Best raw performance |
| **Splitwise-HA** | DGX-H100 | DGX-A100 | Best of both worlds |
| **Splitwise-HHcap** | DGX-H100 | H100 @ 70% power | Power optimization |

### Design Space Search
- Event-driven cluster simulator (open-source: SplitwiseSim)
- Input: hardware profiles, SLOs, request traces, optimization goal
- Output: optimal number of prompt/token machines

[Reference: Splitwise Figure 12 — Design space search for Splitwise-HH cluster]

---

# Splitwise: Evaluation Results

### Iso-Power Throughput (same power budget)
- **Splitwise-AA**: **2.15x** more throughput than Baseline-A100 (same cost & power)
- **Splitwise-HA**: **1.18x** more throughput at 10% lower cost

### Iso-Cost Throughput (same cost)
- **Splitwise-AA**: **1.4x** more throughput than Baseline-H100 at 20% lower cost

### Iso-Throughput Power (same throughput target)
- **Splitwise-HHcap**: **25% lower power** than Baseline-H100

### Iso-Throughput Cost (same throughput target)
- **Splitwise-AA**: **25% lower cost** than Baseline-H100

> Overall (from abstract): up to **1.4x throughput at 20% lower cost**, or **2.35x throughput at same cost and power**

[Reference: Splitwise Figure 18 — Summary of cluster designs; Figure 16 — Latency metrics across loads]

---

# Splitwise: Robustness

### Workload Changes
- Run conversation trace on cluster designed for coding → only 7% throughput setback
- Mixed pool absorbs the mismatch gracefully

### Model Changes
- Run LLaMA-70B on cluster designed for BLOOM-176B
- All Splitwise designs outperform baselines at higher load
- Splitwise-HH and Splitwise-HHcap consistently achieve best latency

### Key Takeaway
> **Splitwise enables cloud providers to build more cost-efficient, power-efficient LLM inference clusters by using the right hardware for each phase of inference.**

---

# Splitwise: Summary

1. **Characterized** real production LLM workloads → 7 key insights
2. **Designed** phase splitting architecture with three machine pools
3. **Optimized** KV-cache transfer with per-layer overlapping (<1% overhead)
4. **Explored** heterogeneous cluster designs (AA, HH, HA, HHcap)
5. **Achieved**: 1.4x throughput at 20% lower cost, OR 2.35x throughput at same power

**Limitations:**
- Requires careful cluster provisioning (but provides simulator)
- Less beneficial with very few GPUs
- Basic fault tolerance (restart on failure)
- Scheduling overhead could grow at very large scale

---

# ============================================
# PART 2: DISTSERVE (Ethan Chen)
# ============================================

---

# DistServe: Motivation & Key Idea

### The Goodput Problem
Current systems sacrifice either TTFT or TPOT to meet the other's SLO.

**DistServe's key metric — Goodput:**
> Per-GPU goodput = maximum request rate achievable while meeting the SLO attainment target (e.g., 90% of requests within latency bounds)

### The Approach
- Disaggregate prefill and decoding onto **separate GPU instances**
- **Co-optimize** resource allocation and parallelism for each phase independently
- Automatically find the best **placement** on the physical cluster

[Reference: DistServe Figure 1 — Performance comparison showing prefill-only and decode-only outperforming existing systems]

---

# DistServe: Prefill-Decoding Interference in Detail

### Evidence (DistServe Figure 2)
With input length = 128:
- Decode-only batch: ~5ms per step
- Adding one prefill: latency jumps to **15ms** (3x slowdown)

With input length = 1024:
- Prefill slowdown from adding decoding: 50ms → **125ms** (2.5x)
- Decode slowdown: even worse

### Three Root Causes
1. **Compute contention**: Prefill steals compute from decoding steps
2. **Memory contention**: Both compete for GPU memory bandwidth
3. **Scheduling conflict**: Prioritizing one phase starves the other

### Why Chunked Prefill Doesn't Solve It
- Chunk size too small → GPU underutilized
- Chunk size too large → no room for decode tokens
- KV-cache reloading: O(N^2) for N chunks (vs O(N) without chunking)

---

# DistServe: Tradeoff Analysis

### Prefill Instance Analysis
Using M/D/1 queue theory:
- Average TTFT = Execution time + Queuing delay
- At low rates: **intra-op parallelism** better (reduces execution time)
- At high rates: **inter-op parallelism** better (reduces queuing through pipeline)
- Crossover depends on model, hardware, SLO stringency

### Decoding Instance Analysis
- Single decode job is memory-bandwidth-bound
- **Batching is critical** for GPU utilization
- Disaggregation naturally enables larger decode batches (no prefill competition)
- As batch size grows, decoding approaches compute-bound → then parallelism helps

### Key Insight
> Post-disaggregation, each phase can be independently optimized — this is impossible when they share GPUs.

[Reference: DistServe Figure 4 — Parallelism preferences at different arrival rates]
[Reference: DistServe Figure 5 — Decoding latency and throughput under different parallelism]

---

# DistServe: System Design

### Architecture Overview
```
Requests → Centralized Controller
                ↓                    ↓
    ┌──────────────────┐   ┌──────────────────┐
    │ Prefill Instance │   │Decoding Instance  │
    │   LLM Model      │──→│   LLM Model       │
    │ [GPU][GPU]       │KV │ [GPU][GPU]        │
    │ [GPU][GPU]       │   │ [GPU][GPU]        │
    │ Parallel Runtime │   │ Parallel Runtime  │
    └──────────────────┘   └──────────────────┘
```

[Reference: DistServe Figure 6 — Runtime system architecture]

### Implementation
- 6.5K lines Python (algorithm + frontend + orchestration)
- 8.1K lines C++/CUDA (parallel execution engine)
- Built on Ray actors for GPU workers
- OpenAI-compatible API frontend
- Integrates: continuous batching, FlashAttention, PagedAttention

---

# DistServe: Placement Algorithms

### The Optimization Problem
**Given**: Model, workload, SLOs, cluster hardware
**Find**: Parallelism strategies + instance counts + physical placement
**Goal**: Maximize per-GPU goodput

### Algorithm 1: High Node-Affinity (InfiniBand clusters)
1. Enumerate all feasible parallelism configs for prefill and decoding
2. Simulate each config's goodput using event-driven simulator
3. Pick best config for each phase independently
4. Calculate replication needed to meet target rate
- Complexity: O(NM^2), runs in < 1.3 minutes

### Algorithm 2: Low Node-Affinity (limited cross-node bandwidth)
- Constraint: prefill + decode on same node (use NVLINK)
- Co-optimize within node GPU budget
- Group layers into segments, colocate same-stage segments

### Simulator Accuracy
- **< 2% error** compared to real system runs
- Models FLOPs, memory accesses, latency per phase

---

# DistServe: Online Scheduling Optimizations

### Reducing Pipeline Bubbles
- Non-uniform prompt lengths cause uneven pipeline stages
- Solution: batch prefill requests to total ~L_m tokens (saturation point)
- For decoding: set L_m as max batch size

### Combating Burstiness
- Bursty workloads → flood of KV-caches to decode instances
- Solution: **"Pull" model** — decode instances fetch KV-cache when ready
- Prefill instances retain KV-cache in GPU memory as buffer

### Replanning
- Workload profiler monitors average input/output lengths, arrival rate
- If significant pattern shift → rerun placement algorithm
- Algorithm runs in seconds; model reloading in minutes
- Adapts to workload changes faster than they typically occur

---

# DistServe: Evaluation Results

### Setup
- 4 nodes × 8 GPUs = 32 NVIDIA A100-80GB GPUs
- NVLINK intra-node, 25 Gbps InfiniBand cross-node
- Models: OPT-13B, OPT-66B, OPT-175B
- Baselines: vLLM, DeepSpeed-MII

### Chatbot (ShareGPT dataset)
| Comparison | Request Rate Improvement | SLO Improvement |
|-----------|------------------------|-----------------|
| vs vLLM | **2.0x – 4.6x** higher | **1.8x – 3.2x** tighter |
| vs DeepSpeed-MII | **1.6x – 7.4x** higher | **1.7x – 1.8x** tighter |

### Code Completion (HumanEval)
- **5.7x** higher rate, **1.4x** tighter SLO vs vLLM

### Summarization (LongBench)
- **4.3x** higher rate, **12.6x** tighter SLO vs vLLM

[Reference: DistServe Figure 8 — Chatbot SLO attainment curves]
[Reference: DistServe Figure 9 — Code completion and summarization results]

---

# DistServe: Latency Breakdown & Ablation

### KV-Cache Transmission Overhead
- For OPT-175B on ShareGPT: **< 0.1%** of total latency
- 95% of requests: transfer delay < 30ms
- **Transmission is negligible** — confirming Splitwise's findings

### Ablation: What Matters?
- **vLLM++** (vLLM + best parallelism search) = same as vLLM
  → Interference prevents parallelism gains when colocated
- **DistServe-High** (no placement constraints) > DistServe-Low
  → Placement algorithm provides real value
- **Disaggregation alone** is powerful, but **combined with optimized placement** is best

### Parallelism Strategies Chosen
| Model | Prefill (TP, PP) | Decode (TP, PP) |
|-------|-----------------|-----------------|
| OPT-13B | (2, 1) | (1, 1) |
| OPT-66B | (4, 1) | (2, 2) |
| OPT-175B | (3, 3) | (4, 3) |

> **Different strategies per phase — only possible with disaggregation!**

[Reference: DistServe Figure 10 — Latency breakdown; Figure 11 — Ablation study]

---

# Comparison: Splitwise vs DistServe

| Dimension | Splitwise | DistServe |
|-----------|-----------|-----------|
| **Core focus** | Heterogeneous hardware | Goodput optimization |
| **Cluster type** | Mixed GPU types | Same GPU type |
| **Key innovation** | Right hardware per phase | Right parallelism per phase |
| **Target audience** | Cloud providers (CSPs) | LLM service operators |
| **Scheduling** | JSQ + mixed pool | Shortest queue + pull-based KV |
| **KV-cache** | Per-layer overlapped | Pull-based on-demand |
| **Formal analysis** | Characterization-driven | Queueing theory-driven |
| **Evaluation** | Real A100+H100 + simulator | Real A100 + simulator |
| **Venue** | ISCA 2024 | OSDI 2024 |

### Complementary, Not Competing
- Splitwise: "Use the **right hardware** for each phase"
- DistServe: "Use the **right software configuration** for each phase"
- **Best system**: combine both approaches

---

# Both Papers Agree On

1. **Colocation of prefill and decoding is fundamentally flawed** for SLO-sensitive workloads
2. **KV-cache transfer overhead is negligible** on modern GPU clusters
3. Each phase benefits from **different resource allocation and parallelism**
4. Disaggregation enables **2-7x improvement** in effective capacity
5. The approach works for **all modern transformer-based LLMs**
6. **Long context windows** make disaggregation even more valuable

---

# Limitations & Future Directions

### Shared Limitations
- Less beneficial with very few GPUs (disaggregation overhead)
- Fault tolerance: dependency between prefill/decode instances
- FCFS scheduling → convoy effect with heterogeneous request sizes
- Throughput-only workloads (batch/offline) may prefer colocation

### Open Research Questions
1. **Preemptive scheduling** with disaggregation — reduce convoy effects
2. **Heterogeneous hardware + optimized placement** — combine Splitwise + DistServe ideas
3. **Long-context inference** (1M+ tokens) — prefill computation grows quadratically
4. **MoE (Mixture of Experts)** models — how does disaggregation interact with expert routing?
5. **KV-cache compression** — reduce transfer overhead for extreme context lengths
6. **Multi-turn conversations** — cache reuse across turns with disaggregated architecture

### Industry Adoption
- Already adopted by: **SGLang, vLLM, Mooncake**
- Follow-up work: **PolyServe, DuetServe**
- Phase disaggregation is becoming the **standard architecture** for LLM serving

---

# Summary

### Splitwise (Patel et al., ISCA 2024)
- Characterized production workloads → 7 insights about phase asymmetry
- Split phases onto separate, potentially heterogeneous machines
- **1.4x throughput at 20% lower cost** or **2.35x throughput at same power**

### DistServe (Zhong et al., OSDI 2024)
- Formalized goodput as the optimization target
- Co-optimized parallelism and placement per phase
- **Up to 7.4x higher request rate** and **12.6x tighter SLO** vs baselines

### The Big Picture
> Prefill and decoding are fundamentally different workloads. Treating them as one wastes hardware, power, and money. Disaggregation is the right abstraction.

---

# Thank You — Questions?

**Papers:**
- Splitwise: arXiv:2311.18677 (ISCA 2024)
- DistServe: arXiv:2401.09670 (OSDI 2024)

**Code:**
- SplitwiseSim: github.com/Mutinifni/splitwise-sim
- DistServe: github.com/LLMServe/DistServe

**Presenters:** Berat Celik & Jiayang (Ethan) Chen
**Course:** ECE 5545 — ML Hardware & Systems — Spring 2026
