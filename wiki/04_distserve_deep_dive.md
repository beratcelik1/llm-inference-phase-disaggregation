# DistServe Deep Dive

**Paper**: "DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving"
**Authors**: Yinmin Zhong, Shengyu Liu, Junda Chen, Jianbo Hu, Yibo Zhu, Xuanzhe Liu, Xin Jin, Hao Zhang
**Affiliation**: Peking University + StepFun + UC San Diego
**arXiv**: 2401.09670v3 (June 2024)
**Venue**: Published at OSDI 2024

## Key Contribution
DistServe introduces **goodput** (throughput under SLO constraints) as the primary optimization metric and develops algorithms to **co-optimize GPU allocation and parallelism strategies** for disaggregated prefill and decoding instances within a **homogeneous** cluster.

## Problem Formulation: Goodput

### Definition
- **Per-GPU Goodput**: Maximum request rate that can be served while meeting the SLO attainment goal (e.g., 90% of requests meet latency targets)
- Higher goodput = lower cost per query
- This is the RIGHT metric for production LLM services (not raw throughput)

### Why Goodput Matters
- Raw throughput ignores latency → useless for interactive applications
- SLO attainment = proportion of requests meeting both TTFT and TPOT targets
- Real applications have different SLO requirements:
  - Chatbot: TTFT=0.25s, TPOT=0.1s (stringent)
  - Code completion: TTFT=0.125s, TPOT=0.2s (very stringent TTFT)
  - Summarization: TTFT=15s, TPOT=0.15s (loose TTFT, stringent TPOT)

## Analytical Framework

### Prefill Instance Analysis (Section 3.1)

#### Batching
- Prefill is compute-bound
- There exists a critical input length threshold `L_m` beyond which GPU is saturated
- Batching requests shorter than `L_m` is beneficial; beyond it, just delays all requests
- In practice, user prompts average hundreds of tokens → batch sizes stay small

#### Parallelism preferences
- At **low arrival rates**: intra-op parallelism better (reduces execution time → lower TTFT)
- At **high arrival rates**: inter-op parallelism better (scales rate capacity, queuing delay dominates)
- The crossover depends on speedup coefficient K (affected by communication overhead)

#### Queueing theory model
Using M/D/1 queue analysis:
- Without parallelism: `Avg_TTFT = D + RD^2 / (2(1-RD))` where D=execution time, R=arrival rate
- With 2-way inter-op: `Avg_TTFT_inter = D + RD^2 / (4(2-RD))`
- With 2-way intra-op: `Avg_TTFT_intra = D/K + RD^2 / (2K(K-RD))`

### Decoding Instance Analysis (Section 3.2)

#### Batching
- Decoding is memory-bandwidth-bound
- Batching is CRITICAL: increases GPU utilization significantly
- With disaggregation: multiple prefill instances feed one decoding instance → naturally larger batches
- Batch size limited by GPU memory (KV-cache storage)

#### Parallelism preferences
- Large batch sizes push decoding toward compute-bound → resembles prefill
- When TPOT SLO is stringent: intra-op parallelism essential (reduce latency)
- Beyond meeting latency: inter-op for throughput scaling

### Practical Challenges (Section 3.3)

1. **Variable prefill lengths**: Non-uniform prompts cause pipeline bubbles with inter-op parallelism
2. **Communication overhead**: KV-cache transfer between phases
   - OPT-66B, 512 tokens: ~1.13 GB per request
   - At 10 rps: need ~90 Gbps bandwidth → feasible on modern clusters
   - Solution: keep prefill and decode instances on same node (NVLINK) when cross-node bandwidth is limited

## DistServe Method (Section 4)

### The Optimization Problem
Given: model G, workload W, latency SLOs, SLO attainment target, cluster hardware
Find: 
- (a) Parallelism strategies for prefill and decoding instances
- (b) Number of each instance type to deploy  
- (c) Physical placement on the cluster

Goal: **Maximize per-GPU goodput**

### Algorithm 1: High Node-Affinity Placement
For clusters with InfiniBand (fast cross-node communication):
1. Enumerate all feasible parallelism configurations for prefill
2. For each config, simulate prefill goodput using `simu_prefill`
3. Keep the best prefill configuration
4. Similarly find best decoding configuration using `simu_decode`
5. Calculate replication counts: `n = ceil(R / config_p.goodput)`, `m = ceil(R / config_d.goodput)`
6. Return placement: `(n, config_p, m, config_d)`

**Complexity**: O(NM^2) where N = node limit, M = GPUs per node (typically 8)
**Runtime**: Under 1.3 minutes for largest settings

### Algorithm 2: Low Node-Affinity Placement  
For clusters without fast cross-node links:
- Additional constraint: prefill and decode must share same node (use NVLINK)
- Enumerate inter-op parallelism degrees
- For each, find all intra-node configurations using `get_intra_node_configs`
- Co-optimize prefill and decode within node constraints

### Simulator
- Event-driven simulator estimates goodput for each configuration
- Analyzes FLOPs and memory accesses for prefill/decoding
- Uses latency model to approximate execution time
- Fits distributions from historical request traces
- Accuracy: **<2% error** compared to real system (Table 2)

## Online Scheduling (Section 4.3)

### Architecture
- Centralized controller receives all requests
- Dispatches to prefill instance with shortest queue
- After prefill, dispatches to least loaded decoding instance
- FCFS within each instance

### Key Optimizations

#### Reducing Pipeline Bubbles
- Balance execution time across batches
- Profile target model/GPU for minimum prompt length `L_m` to saturate GPU
- Batch multiple short prompts to total ~`L_m` tokens
- For decoding: set batch size to `L_m` as maximum

#### Combat Burstiness
- Use "pull" model for KV-cache transfer (not "push")
- Decoding instances fetch KV-cache when ready
- Prefill instances retain KV-cache in GPU memory as buffer
- Prevents memory overload on decoding instances

### Runtime System Architecture (Figure 6)
```
Requests → Controller → Prefill Instance (GPU cluster) --KV Cache--> Decoding Instance (GPU cluster)
```
- RESTful API frontend (OpenAI-compatible)
- Orchestration layer: request dispatching, KV-cache transmission, result delivery
- Parallel execution engine: Ray actors, GPU workers
- Integrates: continuous batching, FlashAttention, PagedAttention

### Replanning
- Workload profiler monitors key parameters (avg input/output length, arrival rate)
- If significant pattern shift detected → rerun placement algorithm
- Algorithm runs in seconds, model reloading in minutes
- Far faster than hourly workload variations in practice

## Evaluation Results

### Setup
- 4 nodes, 32 GPUs total (NVIDIA SXM A100-80GB)
- NVLINK intra-node, 25 Gbps cross-node InfiniBand
- OPT model family: 13B, 66B, 175B
- Three workloads: Chatbot (ShareGPT), Code Completion (HumanEval), Summarization (LongBench)

### Baselines
- **vLLM**: Continuous batching + PagedAttention, colocated phases
- **DeepSpeed-MII**: Chunked prefill, colocated phases

### Key Results

#### Chatbot (ShareGPT)
- DistServe: **2.0x-4.6x** higher request rate than vLLM
- DistServe: **1.6x-7.4x** higher request rate than DeepSpeed-MII
- Under tighter SLOs: **1.8x-3.2x** more stringent SLO than vLLM

#### Code Completion (HumanEval)
- DistServe: **5.7x** higher request rate, **1.4x** more stringent SLO than vLLM
- Stringent TTFT requirement drives the improvement

#### Summarization (LongBench)
- DistServe: **4.3x** higher request rate, **12.6x** more stringent SLO than vLLM
- Long input lengths + stringent TPOT → disaggregation shines

### Latency Breakdown (Figure 10)
- KV-cache transmission: **<0.1%** of total latency (even for OPT-175B!)
- 95% of requests: transfer delay < 30ms
- Transmission is NOT the bottleneck

### Ablation: Disaggregation vs Parallelism Optimization
- vLLM++ (vLLM + best parallelism search): same performance as vLLM default
  - Interference between phases prevents parallelism improvement
- DistServe-High (no placement constraints): achieves further improvements
  - Shows value of the placement algorithm

### Placement Strategies Chosen (Table 3)
| Model | Dataset | Prefill TP,PP | Decoding TP,PP |
|-------|---------|--------------|----------------|
| OPT-13B | ShareGPT | 2, 1 | 1, 1 |
| OPT-66B | ShareGPT | 4, 1 | 2, 2 |
| OPT-175B | ShareGPT | 3, 3 | 4, 3 |

**Note**: Different parallelism strategies for prefill vs decoding - this is only possible with disaggregation!

## Limitations & Future Work
1. **FCFS scheduling**: Can lead to "convoy effect" (long requests block short ones)
   - Preemptive strategies could help
2. **Fault tolerance**: Dependency between prefill and decoding instances
   - Single decoding instance failure could affect multiple prefill instances
3. **Resource-constrained scenarios**: With few GPUs, disaggregation overhead may not be worth it
4. **Throughput-only scenarios**: For offline/batch processing, colocation may be preferred
5. **Long contexts**: As context windows grow to 1M tokens, the disaggregation benefit increases
   - KV-cache grows linearly, prefill computation grows quadratically
   - Makes the phases even MORE different
