# Q&A Preparation — Splitwise (Berat)
## Anticipated Questions & Answers

---

## Category 1: Fundamental Understanding

### Q1: "Why not just use chunked prefill instead of disaggregating? Isn't it simpler?"

**Answer:** "Chunked prefill is simpler but has fundamental limitations. First, there's a chunk size dilemma — too small and the GPU is underutilized during prefill, too large and you can't fit decode tokens. Second, and this is the killer — when you split a prefill into N chunks, you need to reload all previous KV-cache chunks for each subsequent chunk. This means the KV-cache loading scales as O(N-squared), versus O(N) without chunking. For long prompts, this overhead is significant. Third, chunked prefill still colocates the phases on the same GPU, so you can't use different parallelism strategies or hardware. Disaggregation eliminates all three problems."

### Q2: "What exactly is the KV-cache and why is it so important?"

**Answer:** "During the attention mechanism, each transformer layer computes Key and Value projections for every input token. These K and V tensors are the KV-cache. During decoding, each new token needs to attend to ALL previous tokens — so it reads the entire KV-cache. Without storing it, you'd have to recompute all previous tokens at every step, which is wildly expensive. The KV-cache size scales as 2 times the number of layers times hidden size times sequence length times the data type size. For a 66B parameter model with 512 tokens, that's about 1.13 GB per request. When you disaggregate, this is what needs to be transferred between machines."

### Q3: "Why is prefill compute-bound and decoding memory-bound? Can you explain intuitively?"

**Answer:** "Think about the matrix multiplications. In prefill, you process say 512 tokens at once, so the matrices are 512-by-hidden-size. That's a large, dense matrix multiply — lots of arithmetic operations per byte of data loaded. The arithmetic intensity exceeds what the GPU's memory bandwidth can handle, so the GPU is compute-saturated.

In decoding, you're processing just 1 token per request. Even with batching of say 32 requests, your matrix is 32-by-hidden-size — much smaller. The arithmetic intensity is low. You spend more time loading model weights from memory than doing actual computation. The operations finish faster than you can feed data to them, so you're waiting on memory bandwidth."

---

## Category 2: Splitwise-Specific Design

### Q4: "How does the per-layer KV-cache transfer actually work?"

**Answer:** "As each transformer layer completes its computation during the prefill phase, the KV-cache for that specific layer is immediately sent to the token machine. Splitwise uses MSCCL++, a GPU-driven communication library, with a zero-copy one-sided 'put' primitive over InfiniBand. The key is that it's asynchronous — the prompt machine sends the data as soon as it's ready, without needing the token machine to issue any receive instructions. Once all layers have been put, the prompt machine signals via a semaphore that the token machine waits on. This overlap means the transfer happens in parallel with the computation of subsequent layers, resulting in only 5-8ms of non-overlapped transfer time regardless of prompt size."

### Q5: "What happens when the mixed pool gets overwhelmed?"

**Answer:** "The mixed pool is a buffer — if it also fills up, you're just over capacity and requests will queue longer, same as any system. But the mixed pool makes the system more graceful under load. At low load, it stays empty and machines are in their dedicated pools. As load increases, machines migrate into the mixed pool. If load deviates significantly from what the cluster was provisioned for, Splitwise employs coarse-grained re-purposing — actually moving machines between the prompt and token pools. The system was tested with mismatched workloads and only saw a 7% throughput drop."

### Q6: "Why three pools? Why not just prompt and token?"

**Answer:** "The mixed pool handles the mismatch between predicted and actual workload patterns. Real workloads are bursty and unpredictable. If you only have prompt and token pools, and a burst of long prompts arrives, the prompt pool gets overloaded while token machines sit idle. The mixed pool can absorb these spikes. Mixed machines use mixed continuous batching — the same approach as non-Splitwise systems — so they're not wasting anything, they're just less optimized than dedicated machines."

### Q7: "How does Splitwise handle fault tolerance?"

**Answer:** "Currently, it's basic — if a prompt or token machine fails, the affected requests restart from scratch, same as existing systems like vLLM. The paper discusses two potential improvements: first, checkpointing the KV-cache after the prompt phase, so recovery skips the prompt recomputation. Second, periodic KV-cache checkpointing during token generation. But these are listed as future work. The key vulnerability in disaggregation is that a single decoding instance failure could affect multiple prefill instances that were sending work to it."

---

## Category 3: Performance & Evaluation

### Q8: "The paper says 0.8% overhead for KV-cache transfer. Under what conditions might this be worse?"

**Answer:** "The 0.8% is for per-layer transfer with InfiniBand or NVLINK. It could be worse with: (1) slower interconnects — if you're using Ethernet instead of InfiniBand, bandwidth drops by 10x or more; (2) extremely long prompts — the KV-cache grows linearly with sequence length, so million-token contexts would produce very large transfers; (3) high request rates where the network becomes saturated. But the paper addresses this — they require prefill and decode instances to stay on the same node when cross-node bandwidth is limited, using NVLINK at 600 GB/s which makes transfer negligible."

### Q9: "Why does Splitwise-AA (all A100s) outperform Baseline-H100?"

**Answer:** "It seems counterintuitive, but it comes down to cost-efficiency. Under the same cost budget, you can afford 75% more A100 machines than H100 machines because A100s are 2.16x cheaper. With Splitwise, those A100 machines are well-utilized — the token generation phase doesn't need H100 compute, so A100s are perfectly adequate. More machines means more parallel capacity, and the disaggregation ensures each machine is doing the right job. You're essentially using the savings from cheaper hardware to buy more hardware, which Splitwise can utilize efficiently."

### Q10: "What are the 1.4x and 2.35x numbers referring to exactly?"

**Answer:** "1.4x higher throughput at 20% lower cost — this compares Splitwise-AA against Baseline-H100 in an iso-throughput cost-optimized setting. Same throughput target, but Splitwise-AA achieves it with 25% less money by using cheaper A100s allocated efficiently.

2.35x more throughput at same cost and power — this compares Splitwise-AA against Baseline-A100 in an iso-power throughput-optimized setting. Same power budget, but Splitwise gets 2.35x more requests through because disaggregation dramatically improves per-GPU utilization."

---

## Category 4: Broader Context & Comparison

### Q11: "How is Splitwise different from DistServe?"

**Answer:** "They solve the same problem from different angles. Splitwise focuses on **hardware heterogeneity** — using different GPU types for each phase, targeting cloud providers designing new clusters. DistServe focuses on **software-level optimization** — co-optimizing parallelism strategies and placement within an existing homogeneous cluster. Splitwise uses production traces from Azure; DistServe uses queueing theory and simulation. They're complementary — the ideal system would combine heterogeneous hardware from Splitwise with optimized per-phase parallelism from DistServe."

### Q12: "Has this approach been adopted in practice?"

**Answer:** "Yes, significantly. As mentioned in our Ed Discussion post, mainstream frameworks like SGLang, vLLM, and Mooncake have all adopted prefill-decode disaggregation. The concept has moved from research to standard practice in about two years. Follow-up papers like PolyServe and DuetServe build on this foundation. The industry consensus is clear — disaggregation is the right architecture for production LLM serving."

### Q13: "What about Mixture of Experts (MoE) models? Does disaggregation still help?"

**Answer:** "Yes — MoE models like Mixtral still have the same two-phase structure. The prompt phase processes all tokens in parallel through the router and selected experts, while decoding generates one token at a time. The computational asymmetry between phases persists. In fact, MoE might make disaggregation even more interesting because the expert selection patterns could differ between prefill and decode, suggesting different optimization strategies for each phase. Both papers note their approach applies to all transformer-based generative models, including MoE variants."

### Q14: "Does this work for very small models where a single GPU can handle everything easily?"

**Answer:** "For small models on a single GPU, the overhead of disaggregation — network communication, separate model copies, scheduling complexity — may outweigh the benefits. Both papers acknowledge this as a limitation. DistServe specifically mentions 'resource-constrained scenarios' where disaggregation provides less benefit. The sweet spot is medium-to-large scale deployments where you already need multiple GPUs and where the interference between phases creates real performance problems."

### Q15: "What about long context windows (1M+ tokens)? How does that change things?"

**Answer:** "Long context actually makes disaggregation MORE valuable, not less. Here's why: the prefill computation grows quadratically with context length (due to attention), while the KV-cache grows linearly. This means the prefill phase becomes even more compute-heavy relative to decoding, widening the asymmetry between phases. The interference problem gets worse. At the same time, the KV-cache to transfer gets larger, but it still grows linearly, and bandwidth scales with hardware upgrades. Both papers note this as a promising direction — disaggregation becomes even more important as context windows grow."

---

## Category 5: Technical Deep Dives (from Professor)

### Q16: "Can you walk through the queueing theory analysis? Why M/D/1?"

**Answer:** "The M/D/1 queue models Markovian arrivals (Poisson process — M), Deterministic service time (D — because execution time is roughly constant for uniform-length prefills), and 1 server. After disaggregation, each prefill instance processes requests independently with roughly consistent execution times, so M/D/1 is a reasonable approximation. The average TTFT equals D plus RD-squared over 2 times (1 minus RD), where D is execution time and R is the arrival rate. The first term is the execution time, the second is the queuing delay. This simple model shows how arrival rate affects latency and helps compare parallelism strategies analytically before resorting to simulation."

### Q17: "How does the simulator achieve <2% error?"

**Answer:** "DistServe's simulator analyzes the FLOPs and memory accesses for each operation in both phases. For prefill, it models the four main GEMM operations (QKV linear, attention output, FFN input, FFN output) and the attention computation. For decoding, similarly. They build a piece-wise linear performance model calibrated against real profiling data at various batch sizes, input sizes, and output sizes. The key insight from prior work is that DNN execution is highly predictable — the same operation with the same input size takes the same time every time. This determinism is what makes simulation accurate."

### Q18: "What is SLO attainment and why use 90%?"

**Answer:** "SLO attainment is the percentage of requests that meet all latency targets. If you set TTFT < 0.25s and TPOT < 0.1s with 90% attainment, that means 90% of requests must satisfy both conditions. The 90% threshold is a reasonable production target — it means only 1 in 10 requests experiences a latency violation, which is generally acceptable for interactive applications. The papers also test at 99% attainment for more stringent requirements. The choice of threshold significantly affects the goodput — stricter attainment means the system can handle fewer requests."

---

## Quick Reference: Key Numbers to Remember

| Fact | Number |
|------|--------|
| H100 compute advantage over A100 | 3.43x |
| H100 memory bandwidth advantage | 1.64x |
| H100 cost premium | 2.16x |
| KV-cache size (OPT-66B, 512 tokens) | ~1.13 GB |
| KV-cache transfer overhead (per-layer) | 0.8% of E2E |
| Splitwise throughput improvement | 1.4x-2.35x |
| DistServe rate improvement vs vLLM | 2.0x-7.4x |
| DistServe SLO improvement vs vLLM | up to 12.6x |
| DistServe simulator accuracy | <2% error |
| Splitwise robustness (wrong workload) | only 7% drop |
