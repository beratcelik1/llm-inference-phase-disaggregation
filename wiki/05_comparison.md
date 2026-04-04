# Splitwise vs DistServe: Comparative Analysis

## Timeline & Relationship
- **Splitwise**: arXiv November 2023, published at **ISCA 2024** (computer architecture venue)
- **DistServe**: arXiv January 2024, published at **OSDI 2024** (systems venue)
- Concurrent and independent work arriving at the same fundamental insight
- DistServe cites Splitwise as concurrent work (reference [38])
- They approach the problem from different angles (hardware vs software optimization)

## Side-by-Side Comparison

| Dimension | Splitwise | DistServe |
|-----------|-----------|-----------|
| **Core focus** | Hardware heterogeneity + cluster design | Software-level goodput optimization |
| **Cluster type** | Heterogeneous (different GPUs per phase) | Homogeneous (same GPUs, different allocation) |
| **Key metric** | Throughput, cost, power | Goodput (throughput under SLO) |
| **Optimization target** | Minimize cost/power for target throughput | Maximize per-GPU goodput |
| **Analytical approach** | Production trace characterization | Queueing theory + simulation |
| **Scheduling** | Two-level (CLS + MLS), JSQ routing | Centralized controller, FCFS + shortest queue |
| **Machine pools** | Prompt pool + Token pool + Mixed pool | Prefill instances + Decoding instances |
| **KV-cache transfer** | Per-layer optimized (MSCCL++) | Pull-based (on-demand by decode instance) |
| **Parallelism** | TP across 8 GPUs/machine (hardware focus) | Co-optimized TP+PP per phase (algorithmic) |
| **Placement algorithm** | Cluster provisioning search | Goodput-optimal placement (Alg 1 & 2) |
| **Evaluation models** | BLOOM-176B, LLaMA-70B | OPT-13B, OPT-66B, OPT-175B |
| **Evaluation data** | Real Azure production traces | Synthetic from ShareGPT, HumanEval, LongBench |
| **Hardware tested** | A100 + H100 (real) + simulator | A100 only (real) + simulator |
| **Venue** | ISCA 2024 (architecture) | OSDI 2024 (systems) |

## Complementary Strengths

### Splitwise's Unique Contributions
1. **Production trace characterization**: Real Azure data provides ground truth about LLM workloads
2. **Hardware heterogeneity insight**: Token generation doesn't need expensive GPUs
3. **Power optimization**: Power-capping token machines saves 25% power with no latency impact
4. **Mixed pool design**: Graceful degradation under load via flexible machine repurposing
5. **Per-layer KV-cache transfer**: Overlaps transfer with computation for minimal overhead

### DistServe's Unique Contributions
1. **Goodput formalization**: First to formally define and optimize for per-GPU goodput
2. **Parallelism co-optimization**: Automatically finds best TP+PP for each phase
3. **Placement algorithms**: Handles both high and low node-affinity clusters
4. **Queueing theory analysis**: Formal model for prefill/decode behavior under load
5. **Simulator with <2% error**: Accurate prediction without real hardware testing

## Where They Agree
1. Colocation of prefill and decoding is fundamentally flawed for SLO-sensitive workloads
2. KV-cache transfer overhead is negligible on modern GPU clusters
3. Each phase benefits from different parallelism and resource allocation strategies
4. Disaggregation enables 2-7x improvement in effective capacity
5. The approach is applicable to all modern transformer-based LLMs
6. Long context windows make disaggregation even more valuable

## Where They Differ in Philosophy

### Splitwise: "Use the right hardware for the job"
- The prompt phase is compute-bound → give it compute-heavy GPUs (H100)
- The token phase is memory-bound → cheaper GPUs work fine (A100, power-capped H100)
- Optimize for TCO (Total Cost of Ownership) of the entire cluster
- More relevant for **cloud service providers** designing new datacenters

### DistServe: "Optimize what you have"
- Given a fixed homogeneous cluster, maximize the value you extract
- Different parallelism strategies per phase can dramatically improve goodput
- Automatic algorithm finds the best configuration
- More relevant for **LLM service operators** with existing hardware

## Limitations Comparison

| Limitation | Splitwise | DistServe |
|-----------|-----------|-----------|
| Requires heterogeneous hardware | Yes (for full benefit) | No |
| Fault tolerance addressed? | Basic (restart) | Discussed but not implemented |
| Works with few GPUs? | Less benefit | Less benefit |
| Handles workload shifts? | Mixed pool + re-provisioning | Replanning algorithm |
| Preemption support? | Token preemption in mixed pool | Not implemented |

## Impact on the Field
Both papers have been highly influential:
- Adopted by mainstream frameworks: SGLang, vLLM, Mooncake
- Spawned follow-up work: PolyServe, DuetServe
- Established prefill-decode disaggregation as a standard technique
- The Ed Discussion post for this presentation notes these frameworks have adopted this paradigm
