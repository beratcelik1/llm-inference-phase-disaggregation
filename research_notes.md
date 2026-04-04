# LLM Inference Serving Systems and Phase Disaggregation
## Research Notes for ECE 5545 Presentation — Splitwise & DistServe

---

## Table of Contents
1. [Background: LLM Inference Phases](#1-background-llm-inference-phases)
2. [Key Metrics: TTFT, TPOT, and Goodput](#2-key-metrics-ttft-tpot-and-goodput)
3. [KV Cache: Structure, Sizing, and the Transfer Bottleneck](#3-kv-cache-structure-sizing-and-the-transfer-bottleneck)
4. [Serving System Architectures](#4-serving-system-architectures)
5. [Continuous Batching and PagedAttention](#5-continuous-batching-and-pagedattention)
6. [Model Parallelism: Tensor vs Pipeline](#6-model-parallelism-tensor-vs-pipeline)
7. [GPU Hardware: A100 vs H100](#7-gpu-hardware-a100-vs-h100)
8. [Splitwise: Phase Splitting with Heterogeneous Hardware](#8-splitwise-phase-splitting-with-heterogeneous-hardware)
9. [DistServe: Goodput-Optimized Disaggregation](#9-distserve-goodput-optimized-disaggregation)
10. [Related Work](#10-related-work)
11. [Follow-Up Work and Industry Adoption](#11-follow-up-work-and-industry-adoption)
12. [Sources](#12-sources)

---

## 1. Background: LLM Inference Phases

Autoregressive LLM inference consists of two fundamentally different phases with distinct computational profiles.

### Prefill Phase (Prompt Processing)
- Processes the entire input prompt in a single forward pass.
- Involves large matrix-matrix multiplications (GEMMs) across all tokens simultaneously.
- **Compute-bound**: High arithmetic intensity. Tensor Cores are highly utilized. GEMM-intensive kernels (QKV-Proj, O-Proj, FFN-Up, FFN-Down) are stalled primarily by execution dependencies, reflecting warps waiting for long-latency HMMA instructions. Pipeline Busy metrics show sustained Tensor Core utilization.
- Output: KV cache entries for all input tokens + the first output token.
- Latency determines **Time to First Token (TTFT)**.

### Decode Phase (Token Generation)
- Generates tokens one at a time, autoregressively.
- Each step is essentially a matrix-vector operation (batch size = 1 per sequence for the new token, but reads all prior KV cache entries).
- **Memory-bandwidth-bound**: Low arithmetic intensity. Both attention and FFN kernels cluster in the bandwidth-limited region of a roofline model. The speed at which data is transferred from HBM to compute units dominates latency.
- Each step appends one new KV entry to the cache and produces one token.
- Latency per step determines **Time Per Output Token (TPOT)**.

### Why This Matters for Disaggregation
The two phases have opposite resource utilization profiles:
- Prefill wants **high FLOPS** (compute throughput).
- Decode wants **high memory bandwidth** (bytes/sec from HBM).

Colocating them on the same GPU forces a compromise: prefill computations stall ongoing decodes (causing "decode stalls"), and decode's low utilization wastes compute capacity that prefill could use. This is the core interference problem that Splitwise and DistServe address.

### Roofline Model Perspective
Using a roofline model, prefill operations sit in the compute-bound region (high arithmetic intensity, performance limited by peak FLOPS), while decode operations sit in the memory-bound region (low arithmetic intensity, performance limited by memory bandwidth). No single GPU configuration is optimal for both simultaneously.

---

## 2. Key Metrics: TTFT, TPOT, and Goodput

### Time to First Token (TTFT)
- **Definition**: Latency from request arrival to the emission of the first output token.
- **Components**: Queuing delay + prefill computation time + network latency.
- **Why it matters**: Determines perceived responsiveness. A chatbot needs TTFT < 500ms to feel interactive. Code completion tools need < 100ms. Streaming applications display tokens as they arrive, so TTFT is the "time to first visible response."
- **What affects it**: Prompt length (longer prompts = more prefill compute), queuing delay (if GPUs are saturated), and interference from other requests sharing the GPU.

### Time Per Output Token (TPOT)
- **Definition**: Average time between consecutive output tokens after the first token.
- **Why it matters**: Determines streaming speed. At 100ms/token, you get 10 tokens/sec (~450 words/min), which is faster than human reading speed (~250 words/min). TPOT only matters until it is faster than reading speed; beyond that, further reduction is imperceptible to users.
- **What affects it**: Batch size (more concurrent decodes sharing the GPU), KV cache size (longer contexts = more memory reads per attention step), and interference from prefill operations.

### End-to-End Latency
- Total latency = TTFT + (number_of_output_tokens - 1) * TPOT
- For short outputs (e.g., classification), TTFT dominates.
- For long outputs (e.g., code generation, summarization), TPOT dominates.

### Service Level Objectives (SLOs)
- SLOs define acceptable performance targets: e.g., "P90 TTFT < 200ms AND P90 TPOT < 50ms."
- Real-world services set SLOs based on application type. Different applications have different tolerances.
- **SLO attainment**: The fraction of requests meeting all SLO constraints (e.g., "90% of requests meet both TTFT and TPOT targets").

### Goodput: The Production Metric
- **Definition**: The number of completed requests per second that meet all SLO constraints.
- **Per-GPU goodput**: Maximum request rate achievable per GPU while maintaining the SLO attainment target (e.g., 90%). Higher per-GPU goodput = lower cost per query.
- **Why throughput alone is insufficient**: A system can have high throughput but violate latency SLOs for most requests. Goodput captures both throughput AND quality of service.
- **DistServe's key insight**: Optimizing for goodput (not raw throughput) naturally leads to disaggregation, because colocated systems hit TTFT or TPOT SLO limits well before GPU compute is saturated.
- **Example**: A colocated system might achieve goodput = min(TTFT_capacity, TPOT_capacity) = min(3.0, 1.6) = 1.6 rps/GPU, bottlenecked by TPOT. A disaggregated system can independently scale prefill and decode to remove this bottleneck.

---

## 3. KV Cache: Structure, Sizing, and the Transfer Bottleneck

### What Is the KV Cache?
During the attention computation, each transformer layer produces Key and Value projections for every token. To avoid recomputing these for all previous tokens at every decode step, they are cached in GPU memory. This KV cache grows linearly with sequence length and is the dominant memory consumer during inference.

### KV Cache Size Formula
For Multi-Head Attention (MHA):
```
KV_cache_bytes = 2 × num_layers × num_kv_heads × head_dim × seq_len × batch_size × bytes_per_element
```
- Factor of 2: storing both K and V tensors.
- `num_kv_heads`: For GQA (Grouped Query Attention), this is fewer than `num_attention_heads`. For MHA, they are equal.
- `bytes_per_element`: 2 for FP16/BF16, 1 for FP8/INT8.

### Concrete Examples
| Model | Layers | KV Heads | Head Dim | Per-Token KV (BF16) |
|-------|--------|----------|----------|---------------------|
| LLaMA-2 7B | 32 | 32 | 128 | 512 KB |
| LLaMA-2 70B | 80 | 8 (GQA) | 128 | 160 KB |
| LLaMA-3 70B | 80 | 8 (GQA) | 128 | 160 KB |

For LLaMA-3 70B with a 4096-token prompt at batch size 8:
- KV cache = 2 * 80 * 8 * 128 * 4096 * 8 * 2 = ~10 GB

### The Transfer Bottleneck in Disaggregation
When prefill and decode run on separate GPUs, the KV cache must be transferred from the prefill instance to the decode instance after prompt processing. This is the primary communication overhead of disaggregation.

**Transfer sizes and times**:
| Prompt Length | KV Size (70B, BF16) | Time @ PCIe Gen5 (64 GB/s) | Time @ NVLink 4.0 (450 GB/s effective) |
|---------------|---------------------|----------------------------|----------------------------------------|
| 512 tokens | ~80 MB | ~1.25 ms | ~0.18 ms |
| 2048 tokens | ~320 MB | ~5.0 ms | ~0.71 ms |
| 8192 tokens | ~1.28 GB | ~20 ms | ~2.8 ms |
| 32768 tokens | ~5.12 GB | ~80 ms | ~11.4 ms |

**Key observations**:
- At short prompts, transfer overhead is negligible even over PCIe.
- At long prompts (8K+), transfer can account for up to **42.2% of Job Completion Time** if not managed carefully.
- NVLink provides ~7x lower transfer latency than PCIe, making it critical for long-context disaggregation.
- At low concurrency (< 20 simultaneous requests), the overhead of disaggregation can outweigh the throughput benefit.

**Mitigation strategies**:
1. **Pipelining**: Overlap KV transfer with ongoing prefill or decode computation (send layers as they complete, don't wait for all layers).
2. **KV cache compression**: Quantize KV entries (e.g., FP16 -> FP8) before transfer, halving bandwidth requirements.
3. **Placement-aware scheduling**: DistServe places prefill and decode instances on GPUs connected via high-bandwidth links (NVLink/NVSwitch within a node) rather than across nodes (lower bandwidth).
4. **Prefix caching**: If multiple requests share a prompt prefix, cache KV entries and reuse them, avoiding redundant transfer.

---

## 4. Serving System Architectures

### vLLM
- **Origin**: UC Berkeley Sky Computing Lab. Paper: "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP 2023).
- **Key innovations**: PagedAttention (OS-style virtual memory paging for KV cache) + continuous batching.
- **Architecture**: Python-based scheduler + CUDA kernels. Iteration-level scheduling where the scheduler operates at the token level.
- **Memory efficiency**: Existing systems waste 60-80% of KV cache memory due to fragmentation. vLLM achieves < 4% waste via paging.
- **Current state**: De facto open-source standard for LLM serving. Now supports disaggregated prefill/decode (added post-DistServe).

### Hugging Face Text Generation Inference (TGI)
- **Architecture**: Hybrid Rust/Python. A Rust web server (router) handles HTTP requests, batching, and scheduling. gRPC calls to a Python model server for inference.
- **Features**: Continuous batching, token streaming via Server-Sent Events (SSE), Flash Attention, Paged Attention, tensor parallelism.
- **Design philosophy**: Production-ready with built-in safety features (watermarking, token limits). Optimized for Hugging Face model hub integration.
- **Comparison with vLLM**: Generally comparable throughput; TGI has tighter Hugging Face ecosystem integration, vLLM has broader community adoption and more aggressive memory optimization.

### NVIDIA Triton Inference Server + TensorRT-LLM
- **Triton**: General-purpose inference server supporting multiple backends (TensorFlow, PyTorch, ONNX, TensorRT). Handles scheduling, batching, model management.
- **TensorRT-LLM (TRT-LLM)**: NVIDIA's LLM-specific optimization library built on PyTorch. Compiles models to optimized TensorRT engines with FP8 quantization, FlashAttention, inflight batching, paged attention.
- **Integration**: TRT-LLM backend runs inside Triton via the `inflight_batcher_llm` C++ backend. Supports multi-GPU and multi-node via tensor/pipeline parallelism.
- **Performance**: Highest raw throughput on NVIDIA hardware due to deep CUDA optimization. Llama 3.3 70B saw 3x throughput boost with TRT-LLM speculative decoding.
- **Limitations**: NVIDIA GPU-only. More complex deployment than vLLM/TGI.

### SGLang
- **Origin**: LMSYS (UC Berkeley). Paper: "SGLang: Efficient Execution of Structured Language Model Programs" (NeurIPS 2024).
- **Key innovation**: RadixAttention — automatic KV cache reuse via a radix tree data structure. Enables efficient prefix search, insertion, and LRU eviction for shared prompt prefixes.
- **Performance**: Up to 5x faster inference for workloads with shared prefixes (few-shot, multi-turn chat, tree-of-thought).
- **Scale**: Deployed on over 400,000 GPUs worldwide as of 2025.
- **Recent**: Zero-overhead batch scheduler, cache-aware load balancing, DeepSeek V3/R1 support.

---

## 5. Continuous Batching and PagedAttention

### The Static Batching Problem
Naive batching: group N requests, process them together, wait for ALL to finish before accepting new requests. Problem: shorter sequences finish early and their GPU slots sit idle until the longest sequence completes. With variable output lengths, GPU utilization can drop to < 50%.

### Continuous Batching (Iteration-Level Scheduling)
Introduced by **Orca** (OSDI 2022). Key idea: schedule at the granularity of individual iterations, not entire requests.
- After each decode step, the scheduler checks: has any sequence emitted <EOS>?
- Finished sequences are immediately evicted; new sequences from the queue are inserted.
- GPU stays fully utilized at every iteration.
- Also called "in-flight batching" (NVIDIA) or "iteration batching" (FriendliAI).

### Orca's Additional Contribution: Selective Batching
- Not all operations can be naively batched when sequences have different lengths (attention requires matching tensor shapes).
- Orca applies batching selectively: GEMM operations (linear layers) are batched across all sequences, but attention is computed per-sequence.
- This allows iteration-level scheduling while respecting shape constraints.

### PagedAttention (vLLM)
**Insight**: KV cache memory fragmentation is identical to the virtual memory fragmentation problem solved by OS paging.

**Mechanism**:
1. KV cache is divided into fixed-size **blocks** (pages), each holding KV entries for a fixed number of tokens (e.g., 16).
2. A **block table** maps each sequence's logical KV positions to physical block locations in GPU memory.
3. Blocks need not be contiguous — any free block anywhere in GPU memory can be used.
4. Memory is allocated on-demand, block by block, as generation progresses.

**Benefits**:
- Near-zero internal fragmentation (waste limited to last block of each sequence).
- Efficient memory sharing for parallel sampling (beam search, best-of-N): multiple sequences can reference the same physical blocks for shared prefix tokens via copy-on-write.
- Memory utilization jumps from ~20-40% (pre-vLLM systems) to > 96%.

### How Continuous Batching + PagedAttention Interact
Together, they enable:
1. Maximum GPU utilization (continuous batching keeps compute busy).
2. Maximum memory utilization (PagedAttention eliminates fragmentation).
3. Higher effective batch sizes (more sequences fit in memory).
4. Dynamic scaling (sequences enter/exit without disruption).

This combination is now the baseline for all modern LLM serving systems.

---

## 6. Model Parallelism: Tensor vs Pipeline

### Tensor Parallelism (TP) — Intra-Operator
- **What it does**: Splits individual weight matrices across GPUs. Each GPU computes a portion of every layer's matrix multiplication in parallel, then results are combined via all-reduce.
- **Communication pattern**: All-reduce after every attention and FFN layer (2 all-reduces per transformer block).
- **Latency impact**: Reduces per-request latency because each forward pass is faster (work split across GPUs).
- **Bandwidth requirement**: High. Requires fast interconnects (NVLink) because all-reduce happens at every layer. With PCIe, communication overhead dominates.
- **Scaling**: Typically TP=2, 4, or 8 within a single node (connected via NVLink). Beyond 8, all-reduce overhead grows significantly.

### Pipeline Parallelism (PP) — Inter-Operator
- **What it does**: Assigns consecutive groups of layers to different GPUs. Data flows sequentially: GPU 0 processes layers 0-19, GPU 1 processes layers 20-39, etc.
- **Communication pattern**: Point-to-point activation transfer between pipeline stages (much less data than all-reduce).
- **Latency impact**: Increases per-request latency because stages execute sequentially (pipeline depth adds latency).
- **Bandwidth requirement**: Low. Only activation tensors (not full gradients) transfer between stages. Works over PCIe or even cross-node links.
- **Scaling**: Can scale across nodes. Pipeline bubbles reduce utilization, mitigated by micro-batching.

### Phase-Specific Trade-Offs (Critical for Splitwise/DistServe)
**Prefill phase**:
- TP: As TP degree increases, communication overhead from all-reduce grows significantly because all GPUs participate in every operation. For long prompts, the compute-to-communication ratio is favorable, but TP's overhead can still dominate.
- PP: Better for prefill because pipeline stages process large chunks in parallel with only point-to-point communication. The large input token count amortizes pipeline bubble overhead.

**Decode phase**:
- TP: Better for decode because each decode step is tiny (one token), and TP reduces the per-step memory bandwidth bottleneck by distributing KV cache reads.
- PP: Worse for decode because micro-batching overhead is significant for the small per-token computation, and sequential stage traversal adds per-token latency.

### DistServe's Approach
DistServe allows **independent parallelism strategies** for prefill and decode instances:
- Prefill might use PP=4 (4 GPUs in a pipeline) for throughput.
- Decode might use TP=4 (4 GPUs with tensor parallelism) for low TPOT.
- This is impossible in colocated systems where both phases share the same GPUs and must use the same parallelism configuration.

### Splitwise's Approach
Splitwise also exploits the phase-specific parallelism insight, and additionally considers heterogeneous hardware:
- H100s (higher compute) assigned to prefill with the parallelism strategy optimized for compute throughput.
- A100s (sufficient memory bandwidth, lower cost) assigned to decode.

---

## 7. GPU Hardware: A100 vs H100

### NVIDIA A100 (Ampere Architecture, 2020)
| Spec | A100 SXM (80GB) |
|------|-----------------|
| FP32 TFLOPS | 19.5 |
| FP16 Tensor TFLOPS | 312 |
| BF16 Tensor TFLOPS | 312 |
| FP8 | Not supported |
| HBM | 80 GB HBM2e |
| Memory Bandwidth | 2.0 TB/s |
| NVLink | 3rd gen, 600 GB/s |
| TDP | 400W |
| Interconnect | NVLink 3.0 (12 links) |

### NVIDIA H100 (Hopper Architecture, 2022)
| Spec | H100 SXM (80GB) |
|------|-----------------|
| FP32 TFLOPS | 60 (~3x A100) |
| FP16 Tensor TFLOPS | 990 (~3x A100) |
| BF16 Tensor TFLOPS | 990 (~3x A100) |
| FP8 Tensor TFLOPS | 1,979 (~6x A100 FP16) |
| HBM | 80 GB HBM3 |
| Memory Bandwidth | 3.35 TB/s (~1.7x A100) |
| NVLink | 4th gen, 900 GB/s (1.5x A100) |
| TDP | 700W |
| Transformer Engine | Yes (FP8 automatic mixed precision) |

### Implications for Phase Disaggregation
**Prefill (compute-bound)**:
- H100 is ~3x faster than A100 at FP16, ~6x at FP8. This directly translates to lower TTFT.
- The Transformer Engine's FP8 support is particularly impactful for prefill, where compute throughput is the bottleneck.

**Decode (memory-bandwidth-bound)**:
- H100 has only ~1.7x the memory bandwidth of A100. Decode speedup is proportionally smaller.
- A100 is significantly cheaper (~$10K vs ~$25-30K) and lower power (400W vs 700W).
- For decode, the A100 delivers better performance-per-dollar and performance-per-watt.

**Splitwise's heterogeneous cluster insight**:
- Assign H100s to prefill (where the 3-6x compute advantage matters).
- Assign A100s to decode (where the 1.7x bandwidth advantage of H100 doesn't justify 2.5-3x higher cost).
- This yields the "2.35x more throughput at same cost" result.

### NVLink Bandwidth for KV Transfer
- A100 NVLink 3.0: 600 GB/s bidirectional (enables fast KV transfer within a node).
- H100 NVLink 4.0: 900 GB/s bidirectional.
- Cross-node: Typically InfiniBand at 200-400 Gb/s (25-50 GB/s), orders of magnitude slower.
- This bandwidth disparity is why both papers emphasize **intra-node disaggregation** and bandwidth-aware placement.

---

## 8. Splitwise: Phase Splitting with Heterogeneous Hardware

### Paper Details
- **Title**: Splitwise: Efficient Generative LLM Inference Using Phase Splitting
- **Authors**: Pratyush Patel et al. (Microsoft Research, University of Washington)
- **Venue**: ISCA 2024 (also published in IEEE Micro 2025)
- **ArXiv**: 2311.18677

### Core Idea
Split each LLM inference request into its prefill and decode phases, execute them on **separate machines** (potentially with different GPU types), and transfer the KV cache between them.

### Key Contributions

1. **Detailed phase characterization**: Extensive profiling of prefill vs decode on A100 and H100 GPUs using production traces from Azure. Shows that prefill is compute-bound (high SM utilization, high arithmetic intensity) while decode is memory-bandwidth-bound (low SM utilization, high HBM read traffic).

2. **Mixed-machine scheduling**: A scheduler that routes prefill to compute-optimized machines (H100) and decode to bandwidth-optimized machines (A100). The scheduler considers:
   - Current load on prefill vs decode pools.
   - KV cache transfer cost based on interconnect bandwidth.
   - SLO requirements for TTFT and TPOT.

3. **KV cache transfer optimization**: Uses fast back-plane interconnects (NVLink within nodes, InfiniBand across nodes). Evaluates layer-by-layer pipelined transfer to overlap communication with computation.

4. **Heterogeneous cluster analysis**: Shows that a mixed H100+A100 cluster achieves better cost-efficiency than a homogeneous H100 cluster for the same SLO targets.

### Results
- **1.4x higher throughput at 20% lower cost** compared to colocated baseline.
- **2.35x higher throughput at same cost and power** with heterogeneous hardware allocation.
- Uses production traces from Azure to validate workload assumptions.

### Limitations
- Requires model weights replicated on both prefill and decode machines (2x memory for model parameters).
- KV transfer overhead is non-trivial for very long prompts.
- Scheduling complexity increases (must balance two pools instead of one).

---

## 9. DistServe: Goodput-Optimized Disaggregation

### Paper Details
- **Title**: DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving
- **Authors**: Yinmin Zhong et al. (Peking University, UCSD Hao AI Lab)
- **Venue**: OSDI 2024
- **ArXiv**: 2401.09670

### Core Problem
Existing systems (vLLM, Orca, etc.) colocate prefill and decode on the same GPUs. This causes:
1. **Prefill-decode interference**: A long prefill computation stalls all concurrent decode steps, causing TPOT spikes.
2. **Coupled resource allocation**: Both phases must use the same GPU count and parallelism strategy, even though their optimal configurations differ.
3. **Throughput-latency tradeoff**: Maximizing throughput (large batches) degrades latency (higher TTFT and TPOT).

### Key Contributions

1. **Disaggregated architecture**: Separate GPU pools for prefill and decode instances. Each pool has its own:
   - Parallelism strategy (e.g., PP for prefill, TP for decode).
   - Number of GPUs (independently scalable).
   - Batch size and scheduling policy.

2. **Goodput-driven optimization**: Instead of maximizing throughput, DistServe maximizes **per-GPU goodput** — the maximum request rate per GPU that meets SLO constraints.

3. **Placement algorithm**: A two-stage algorithm that:
   - **Stage 1**: For each phase, enumerate feasible parallelism configurations (TP degree, PP degree) and estimate the per-GPU goodput achievable under the SLO constraint.
   - **Stage 2**: Given the cluster topology (which GPUs are connected via NVLink vs PCIe vs InfiniBand), place prefill and decode instances to minimize KV transfer overhead.
   - The algorithm is bandwidth-aware: it prefers placing paired prefill/decode instances on GPUs with fast interconnects.

4. **Eliminating prefill-decode interference**: Because the phases run on separate GPUs, there is zero interference. TPOT is stable regardless of prefill load, and TTFT is determined solely by prefill pool capacity.

### Results
- **7.4x more requests served** compared to state-of-the-art (vLLM) at the same SLO.
- **12.6x tighter SLO** achievable at the same request rate.
- **4.48x higher goodput** via the placement algorithm alone.
- Evaluated on LLaMA-2 (7B, 13B, 70B) and OPT (13B, 66B, 175B).

### Key Difference from Splitwise
- Splitwise focuses on **cost optimization via heterogeneous hardware** (H100 for prefill, A100 for decode).
- DistServe focuses on **goodput optimization via independent resource allocation and parallelism strategies**, assuming homogeneous hardware.
- Both eliminate prefill-decode interference via disaggregation; they are complementary approaches that can be combined.

---

## 10. Related Work

### Orca (OSDI 2022)
- **Contribution**: Introduced iteration-level scheduling (continuous batching) and selective batching for LLM inference.
- **Mechanism**: The scheduler invokes the execution engine to run only a single iteration on the batch. After each iteration, finished sequences are evicted, new ones are inserted.
- **Selective batching**: Batches GEMM operations across sequences but computes attention per-sequence to handle variable sequence lengths.
- **Impact**: Foundation for all modern LLM serving systems. vLLM, TGI, TRT-LLM all build on this idea.
- **Limitation**: Still colocates prefill and decode. Prefill-prioritizing scheduling means long prefills block ongoing decodes.

### Sarathi / Sarathi-Serve (OSDI 2024)
- **Contribution**: Chunked prefills + stall-free batching.
- **Chunked prefills**: Splits a long prefill into equal-sized chunks, each processed in one iteration. This prevents a single long prefill from monopolizing the GPU for many milliseconds.
- **Decode-maximal batching**: Each iteration contains at most one prefill chunk plus as many decode steps as possible. This uses "arithmetic intensity slack" — idle GPU compute during decode — to piggyback prefill chunks.
- **Stall-free schedule**: Ongoing decodes are never paused for prefill. New requests enter the batch without stalling existing ones.
- **Results**: Up to 10x decode throughput improvement; 2.6-5.6x serving capacity gain.
- **Alternative to disaggregation**: Sarathi-Serve addresses the same interference problem as Splitwise/DistServe but without separating onto different GPUs. Trade-off: simpler deployment, but cannot independently scale or specialize hardware for each phase.

### DéjàVu (ICML 2024)
- **Contribution**: KV-cache streaming library for disaggregation + microbatch swapping + fault tolerance.
- **KV Streaming**: DéjàVuLib enables efficient KV cache transfer between prompt and token machines with support for various configurations (local/remote, different KV structures).
- **Microbatch swapping**: Swaps KV cache per-microbatch between GPU and CPU memory, maximizing batch size for models that already fit in GPU memory.
- **Fault tolerance**: Token-level KV cache replication with minimal overhead. Enables continuous fault tolerance and seamless recovery.
- **Results**: Up to 2x throughput improvement over FasterTransformer in pipeline-parallel setups. 1.54x microbatch latency reduction during failures.
- **Relevance**: One of the first systems to build the infrastructure layer needed for disaggregated serving (KV transfer, fault recovery).

### FastServe (arXiv 2023)
- **Contribution**: Preemptive scheduling via Multi-Level Feedback Queue (MLFQ) to eliminate head-of-line blocking.
- **Problem**: Run-to-completion scheduling means a long generation (e.g., 2048 tokens) blocks shorter requests in the queue.
- **Mechanism**: After each output token, the scheduler can preempt the current request and schedule a higher-priority one. Uses a skip-join MLFQ that leverages input length to assign initial queue priority.
- **Memory management**: Proactive offloading of KV cache between GPU and host memory for preempted requests.
- **Results**: Up to 31.4x throughput improvement over vLLM under same average latency; 17.9x under same tail latency.
- **Relevance**: Addresses latency variance through scheduling, complementary to disaggregation approaches.

### TetriInfer
- **Contribution**: Disaggregates prefill and decode instances to avoid interference, running prefill-only chunks on dedicated instances.
- **Mechanism**: Observes non-negligible interference between prefill and decode (even with chunked prefills), and thus chooses full disaggregation.
- **Relevance**: Concurrent with Splitwise/DistServe; validates the interference problem independently.

### ShuffleInfer
- **Contribution**: Among the first to propose disaggregate-prefill-decode in LLM inference, concurrent with Splitwise, DistServe, and DéjàVu.
- **Focus**: Mixed downstream workloads with different latency requirements.

---

## 11. Follow-Up Work and Industry Adoption

### The "18 Months Later" Retrospective (Hao AI Lab, November 2025)
The DistServe authors published a retrospective noting the trajectory from research to production:
- **2024**: Slow adoption. Disaggregation requires significant engineering to refactor existing serving systems. Most deployments stayed colocated.
- **2025**: Rapid adoption. As businesses scaled LLM applications and latency became critical (not just throughput), disaggregation became the default playbook.
- **Current state**: Nearly every production-grade LLM serving framework now supports disaggregation: NVIDIA Dynamo, llm-d, Ray Serve, SGLang, vLLM, LMCache, and MoonCake.

### NVIDIA Dynamo (GTC 2025)
- Open-source datacenter-scale distributed inference framework.
- Native support for disaggregated prefill/decode.
- Dynamic GPU scheduling based on demand fluctuation.
- LLM-aware request routing to avoid KV cache recomputation.
- Accelerated async data transfer for KV cache between GPUs.
- KV cache offloading across memory hierarchies (GPU HBM -> CPU DRAM -> SSD).
- 7x throughput improvement on NVIDIA Blackwell (GB200 NVL72) with disaggregated serving.
- Integrates with TRT-LLM, vLLM, and SGLang backends.

### llm-d (Red Hat, 2025)
- Open-source community initiative for disaggregated LLM inference on Kubernetes.
- Kubernetes-native deployment of separate prefill and decode pools.
- Integrates NVIDIA Dynamo optimizations.

### LMCache
- Efficient KV cache layer for enterprise-scale disaggregated serving.
- Sub-millisecond KV cache lookup and transfer.
- Supports zero-copy transfer, pipelining, and compression.
- Addresses the KV transfer bottleneck that was the primary concern with early disaggregation proposals.

### BanaServe
- Dynamic orchestration framework for disaggregated serving.
- Layer-level weight migration and attention-level KV cache migration.
- Global KV Cache Store with layer-wise overlapped transmission.

### SPAD (2025)
- Proposes specialized prefill and decode **hardware** (not just software disaggregation).
- Custom accelerator designs optimized for each phase's compute profile.

### BiScale (2025)
- Energy-efficient disaggregated LLM serving via phase-aware placement and Dynamic Voltage/Frequency Scaling (DVFS).
- Extends Splitwise's heterogeneous hardware idea to include power management.

### HexGen-2 (ICLR 2025)
- Heterogeneous GPU cluster serving with fine-grained parallelism.
- Builds on disaggregation with support for mixed GPU types within prefill/decode pools.

---

## 12. Sources

### Primary Papers
- [Splitwise: Efficient Generative LLM Inference Using Phase Splitting (arXiv)](https://arxiv.org/abs/2311.18677)
- [DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving (OSDI 2024)](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin)
- [DistServe PDF](https://www.usenix.org/system/files/osdi24-zhong-yinmin.pdf)
- [Splitwise IEEE Micro](https://www.computer.org/csdl/magazine/mi/2025/04/11024200/27kcMUnFh2o)

### Serving Systems
- [vLLM: Efficient Memory Management for LLM Serving with PagedAttention](https://vllm.ai/)
- [Inside vLLM: Anatomy of a High-Throughput LLM Inference System](https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html)
- [TGI Architecture](https://huggingface.co/docs/text-generation-inference/en/architecture)
- [NVIDIA TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- [SGLang: Efficient Execution of Structured Language Model Programs](https://github.com/sgl-project/sglang)
- [Fast and Expressive LLM Inference with RadixAttention and SGLang](https://www.lmsys.org/blog/2024-01-17-sglang/)

### Related Work Papers
- [Orca: A Distributed Serving System for Transformer-Based Generative Models (OSDI 2022)](https://www.usenix.org/conference/osdi22/presentation/yu)
- [Sarathi-Serve: Taming Throughput-Latency Tradeoff (OSDI 2024)](https://www.usenix.org/conference/osdi24/presentation/agrawal)
- [DéjàVu: KV-cache Streaming for Fast, Fault-tolerant LLM Serving (ICML 2024)](https://arxiv.org/abs/2403.01876)
- [FastServe: Fast Distributed Inference Serving for LLMs](https://arxiv.org/abs/2305.05920)

### Metrics and Analysis
- [Throughput is Not All You Need (DistServe Blog)](https://haoailab.com/blogs/distserve/)
- [Key Metrics for LLM Inference (BentoML Handbook)](https://bentoml.com/llm/inference-optimization/llm-inference-metrics)
- [Revisiting SLO and Goodput Metrics in LLM Serving](https://arxiv.org/abs/2410.14257)
- [LLM Inference Unveiled: Survey and Roofline Model Insights](https://arxiv.org/html/2402.16363v4)

### GPU Hardware
- [NVIDIA H100 vs A100 Comparison (Gcore)](https://gcore.com/blog/nvidia-h100-a100)
- [NVIDIA Hopper Architecture In-Depth](https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/)
- [A100 vs H100 vs H200 Benchmarks (Modal)](https://modal.com/blog/h200-vs-h100-vs-a100)

### Follow-Up and Industry
- [Disaggregated Inference: 18 Months Later (Hao AI Lab)](https://haoailab.com/blogs/distserve-retro/)
- [NVIDIA Dynamo](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/)
- [NVIDIA Dynamo 1.0 Production-Ready](https://developer.nvidia.com/blog/nvidia-dynamo-1-production-ready/)
- [How to Reduce KV Cache Bottlenecks with NVIDIA Dynamo](https://developer.nvidia.com/blog/how-to-reduce-kv-cache-bottlenecks-with-nvidia-dynamo/)
- [LMCache Technical Report](https://lmcache.ai/tech_report.pdf)
- [Disaggregation in LLMs: The Next Evolution in AI Infrastructure (InfoQ)](https://www.infoq.com/articles/llms-evolution-ai-infrastructure/)
- [Parallelism Strategies in LLM Inference (BentoML)](https://bentoml.com/llm/inference-optimization/data-tensor-pipeline-expert-hybrid-parallelism)

### KV Cache
- [KV Cache Size Calculator (LMCache)](https://lmcache.ai/kv_cache_calculator.html)
- [HACK: Homomorphic Acceleration via Compression of KV Cache](https://arxiv.org/html/2502.03589v1)
- [KV Cache Optimization Strategies](https://arxiv.org/html/2603.20397)
