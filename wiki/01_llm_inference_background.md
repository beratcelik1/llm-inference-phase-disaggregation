# LLM Inference Background

## Transformer Architecture Recap
Modern LLMs (GPT-4, LLaMA, BLOOM, OPT) are decoder-only transformers. Each layer contains:
- **Multi-Head Attention (MHA)**: Q, K, V linear projections + attention computation + output projection
- **Feed-Forward Network (FFN)**: Two linear layers with activation (typically SwiGLU or GELU)
- **Layer Normalization**: RMSNorm or LayerNorm

Key architectural parameters:
- `h`: hidden size (e.g., 8192 for LLaMA-70B)
- `n`: number of attention heads (e.g., 64)
- `s`: head size = h/n (e.g., 128)
- `m`: FFN intermediate size (e.g., 28672)
- `L`: number of layers (e.g., 80 for LLaMA-70B)

## The Two Phases of LLM Inference

### Phase 1: Prefill (Prompt Computation)
- Processes ALL input tokens in parallel in a single forward pass
- Generates the first output token
- **Compute-bound**: High arithmetic intensity (AI > 156 on A100 for 512 tokens)
- Matrix multiplications are large: shapes like (t, h) x (h, 3h) where t = total tokens
- GPU utilization is HIGH - saturates compute
- TTFT (Time to First Token) is dominated by this phase
- Power draw approaches TDP (Thermal Design Power)

### Phase 2: Decoding (Token Generation)
- Generates tokens ONE AT A TIME, autoregressively
- Each step processes only 1 new token per request
- **Memory-bandwidth-bound**: Low arithmetic intensity (AI ~ O(B) where B = batch size)
- Matrix multiplications are thin: shapes like (B, h) x (h, 3h) - batch size is tiny
- GPU utilization is LOW without large batching
- TPOT/TBT (Time Per Output Token / Time Between Tokens) is dominated by this phase
- Power draw is well below TDP

### Why They're Fundamentally Different

| Property | Prefill | Decoding |
|----------|---------|----------|
| Tokens processed | All input tokens (parallel) | 1 token per step (sequential) |
| Compute intensity | High (compute-bound) | Low (memory-bound) |
| GPU utilization | High | Low (without batching) |
| Memory access pattern | Large matrices | Small matrices, large KV cache reads |
| Power consumption | Near TDP | Well below TDP |
| Batching benefit | Limited (already saturated) | High (improves utilization) |
| Key metric | TTFT | TPOT / TBT |
| Ideal parallelism | Intra-op (tensor) at low rates | Inter-op (pipeline) for throughput |

## KV-Cache: The Bridge Between Phases
- During prefill, the attention mechanism generates Key and Value tensors for every layer
- These are stored in GPU memory as the **KV-cache**
- During decoding, each new token attends to ALL previous tokens via the KV-cache
- KV-cache size per request: `2 * L * n * s * seq_len * dtype_size`
  - For OPT-66B, 512 tokens: ~1.13 GB per request
  - For LLaMA-70B, 2048 tokens: ~5 GB per request
- KV-cache is what must be transferred when phases are on different machines
- Transfer is over NVLINK (600 GB/s intra-node) or InfiniBand (25-400 Gbps cross-node)

## Performance Metrics

| Metric | Definition | Importance |
|--------|-----------|------------|
| TTFT | Time from request arrival to first output token | User-perceived responsiveness |
| TPOT | Average time to generate each subsequent token | Streaming speed |
| TBT | Time between consecutive tokens (similar to TPOT) | Online streaming experience |
| E2E Latency | Total time = TTFT + TPOT * output_length | Overall request completion |
| Throughput | Tokens generated per second (system-wide) | System capacity |
| Goodput | Max throughput while meeting SLO targets | Cost-efficiency metric |

## GPU Hardware Context

### NVIDIA A100 (80GB)
- 19.5 TFLOPS (FP16)
- 80GB HBM2e, 2039 GB/s bandwidth
- 400W TDP
- NVLINK: 50 GB/s per direction
- InfiniBand: 200 Gbps
- Cost: ~$17.6/hr per machine (8 GPUs)

### NVIDIA H100 (80GB)
- 66.9 TFLOPS (FP16) - **3.43x more compute**
- 80GB HBM3, 3352 GB/s bandwidth - **1.64x more bandwidth**
- 700W TDP - **1.75x more power**
- NVLINK: 100 GB/s per direction - **2x**
- InfiniBand: 400 Gbps - **2x**
- Cost: ~$38/hr per machine - **2.16x more expensive**

**Critical insight**: Compute scaled 3.43x but memory bandwidth only 1.64x and capacity stayed flat at 80GB. This divergence is exactly why Splitwise's heterogeneous approach makes sense - the token generation phase doesn't need H100-level compute.

## Model Parallelism Strategies

### Tensor Parallelism (TP / Intra-op)
- Splits individual matrix operations across GPUs
- Each GPU holds a slice of every layer's weights
- Requires ALL-REDUCE communication every layer
- Needs high-bandwidth interconnect (NVLINK)
- Reduces per-operation latency (good for TTFT)
- Limited scaling (communication overhead grows)

### Pipeline Parallelism (PP / Inter-op)
- Assigns different layers to different GPUs
- Each GPU processes full operations for its layers
- Only point-to-point communication between stages
- Works with lower bandwidth interconnects
- Linearly scales throughput with more GPUs
- Increases latency (pipeline depth)

### Replication
- Multiple identical copies of the model
- Each replica handles independent requests
- Linearly scales throughput
- No inter-replica communication needed
- Increases total memory usage

## Batching Strategies

### Request-Level Batching
- Batch ready requests, run all forward passes, return results
- Simple but causes head-of-line blocking
- Long token generation phases block new prompts

### Continuous Batching (Orca, 2022)
- Schedule at each forward pass iteration
- New requests can join / completed requests can leave mid-batch
- Reduces TTFT by not waiting for long generations
- Still colocates prefill and decode

### Mixed Batching
- Prompt and token phases can run together in same forward pass
- Scheduling decision at each iteration
- Reduces idle time but causes interference

### Chunked Prefill (Sarathi)
- Split long prefills into chunks
- Piggyback decode tokens with prefill chunks
- Reduces interference somewhat but has O(N^2) KV-cache reloading overhead
