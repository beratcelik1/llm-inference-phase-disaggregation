# Speaker Script — Ethan Chen (DistServe)
## Target Time: ~10 minutes
## NOTE: Ethan — feel free to modify this script to match your speaking style. This is a starting template.

---

## SLIDE: DistServe: Motivation & Key Idea (~1 minute)

"Thanks Berat. So we've seen the problem — colocation of prefill and decoding causes interference and wastes resources. Now I'll talk about DistServe, which takes a different but complementary angle to solve this.

DistServe's key contribution is formalizing **goodput** as the optimization target. Goodput isn't just raw throughput — it's the maximum request rate you can achieve while actually meeting your latency SLOs. For a chatbot, that might mean 90% of requests get their first token within 250 milliseconds AND each subsequent token within 100 milliseconds. A system that blasts through requests but violates SLOs is useless for production.

DistServe's approach: disaggregate prefill and decoding onto separate GPU instances, then **co-optimize** the resource allocation and parallelism strategies for each phase independently. And it does this automatically with a placement algorithm."

---

## SLIDE: DistServe: Prefill-Decoding Interference in Detail (~1 minute)

"Berat showed the high-level interference problem. Let me drill into DistServe's analysis.

Looking at Figure 2, with input length 128: a decoding-only batch runs at about 5ms per step. Add one prefill job and it jumps to 15ms — a 3x slowdown. With input length 1024, the prefill slowdown from adding decoding is even worse — 50ms to 125ms.

The three root causes are compute contention, memory bandwidth contention, and scheduling conflicts. And importantly, the existing mitigation — chunked prefill from Sarathi — doesn't solve it. If your chunk size is too small, the GPU is underutilized during prefill. If it's too large, there's no room for decode tokens. And there's a hidden cost: KV-cache reloading grows as O(N-squared) for N chunks, versus O(N) without chunking. Chunked prefill is a band-aid, not a solution."

---

## SLIDE: DistServe: Tradeoff Analysis (~1.5 minutes)

"What makes DistServe academically rigorous is the formal tradeoff analysis. Once you disaggregate, each phase becomes its own independent optimization problem.

For prefill instances, they model it using M/D/1 queueing theory. The average TTFT is the execution time plus the queuing delay. At low arrival rates, **intra-op parallelism** — that's tensor parallelism — is better because it reduces the execution time, which dominates. But as the rate increases, the queuing delay term grows, and **inter-op parallelism** — pipeline parallelism — becomes advantageous because it scales the rate capacity.

For decoding instances, the story is different. A single decode job is memory-bandwidth-bound and underutilizes the GPU. So batching is absolutely critical. With disaggregation, multiple prefill instances can feed into a single decoding instance, naturally creating larger decode batches. This improves GPU utilization dramatically. As the batch size grows large enough, decoding even starts to approach compute-bound behavior, at which point parallelism strategies become important here too.

The key insight is: **post-disaggregation, you have independent knobs for each phase**. Different parallelism, different batch sizes, different GPU allocations. This is fundamentally impossible when they share hardware."

---

## SLIDE: DistServe: System Design (~45 seconds)

"Here's the system architecture. All requests hit a centralized controller. The controller dispatches to the prefill instance with the shortest queue. After prefill completes, the request — specifically the KV-cache — moves to the least loaded decoding instance.

The implementation is about 6,500 lines of Python for the algorithm, frontend, and orchestration, plus 8,100 lines of C++ and CUDA for the parallel execution engine. It's built on Ray actors, supports an OpenAI-compatible API, and integrates continuous batching, FlashAttention, and PagedAttention."

---

## SLIDE: DistServe: Placement Algorithms (~1.5 minutes)

"This is the algorithmic heart of DistServe. Given a model, workload, SLO targets, and cluster hardware, the placement algorithm automatically finds the best configuration.

For **high node-affinity clusters** — clusters with InfiniBand where cross-node communication is fast — Algorithm 1 works as follows. It enumerates all feasible parallelism configurations for both prefill and decoding. For each configuration, it runs an event-driven simulator to estimate the goodput. It picks the best config for each phase independently, then calculates how many replicas of each are needed to hit the target traffic rate.

The complexity is O(NM-squared) where N is the node limit and M is GPUs per node, typically 8. This runs in under 1.3 minutes even for 96 GPUs.

For **low node-affinity clusters** — where cross-node bandwidth is limited — Algorithm 2 adds constraints. Now prefill and decode instances must share the same physical node to use NVLINK for fast KV-cache transfer. It groups model layers into stages, co-locates same-stage segments within a node, and co-optimizes within the node's GPU budget.

A critical enabler is their simulator, which achieves less than 2% error compared to real system measurements. This means they can explore the design space without running actual experiments for every configuration."

---

## SLIDE: DistServe: Online Scheduling Optimizations (~45 seconds)

"Beyond the offline placement, DistServe has several online scheduling tricks.

To reduce pipeline bubbles from variable prompt lengths, they batch prefill requests to a total of about L_m tokens — the saturation point for the GPU. Multiple short prompts get batched together; long prompts run solo.

For burstiness — where many prompts finish at once and flood decode instances with KV-caches — they use a pull model. Decoding instances fetch KV-caches from prefill instances when they're ready, rather than getting pushed KV-caches they can't handle. The prefill instance keeps the KV-cache in GPU memory as a buffer.

And there's replanning: a workload profiler monitors arrival patterns. If the workload shifts significantly, the placement algorithm reruns. This takes seconds for the algorithm plus minutes to reload models — well within the timescale of real workload changes."

---

## SLIDE: DistServe: Evaluation Results (~1 minute)

"The evaluation uses 32 A100 GPUs across 4 nodes, testing OPT models from 13B to 175B on three application workloads.

On the chatbot workload with ShareGPT data, DistServe achieves 2x to 4.6x higher request rates than vLLM, and 1.6x to 7.4x higher than DeepSpeed-MII. Under tighter SLOs, DistServe can handle 1.8x to 3.2x more stringent latency requirements.

For code completion on HumanEval, 5.7x higher rate and 1.4x tighter SLO than vLLM. This is because code completion has very stringent TTFT requirements, and disaggregation eliminates the interference that was killing prefill latency.

The summarization results on LongBench are the most dramatic — 4.3x higher rate and 12.6x more stringent SLO. Long inputs create severe interference in colocated systems, and DistServe's disaggregation eliminates it entirely."

---

## SLIDE: DistServe: Latency Breakdown & Ablation (~1 minute)

"Let me highlight two important findings.

First, the latency breakdown. For OPT-175B — the most demanding model — KV-cache transmission accounts for less than 0.1% of total latency. 95% of requests have transfer delays under 30ms. This confirms what Splitwise also found: **transmission is not the bottleneck**. The concern that splitting phases would create expensive communication overhead is simply not borne out on modern hardware.

Second, the ablation study. They test vLLM-plus-plus — vLLM with an exhaustive search over parallelism strategies. The result? Same performance as default vLLM. Why? Because when prefill and decoding are colocated, the interference prevents any parallelism improvement from helping. The phases fight each other. Only by disaggregating can you actually realize the benefits of optimized parallelism.

And look at the parallelism strategies DistServe actually chose — for OPT-66B, the prefill uses tensor parallelism of 4 with no pipeline parallelism, while decoding uses tensor parallelism of 2 with pipeline parallelism of 2. **Completely different strategies for each phase.** This is only possible with disaggregation."

---

## SLIDE: Comparison: Splitwise vs DistServe (~1 minute)

"So how do these two papers relate? They're concurrent work that independently arrived at the same fundamental insight — disaggregate the phases — but from different perspectives.

Splitwise comes from the hardware angle. It says: token generation doesn't need expensive compute, so use cheaper or power-capped GPUs for it. It's primarily targeting cloud providers designing new clusters.

DistServe comes from the software optimization angle. It says: given your existing cluster, maximize goodput by finding the optimal parallelism and placement for each phase. It's targeting operators running LLM services.

They're complementary. The ideal production system would use Splitwise's heterogeneous hardware insight combined with DistServe's placement optimization. H100s for prefill with optimized tensor parallelism, A100s for decoding with optimized pipeline parallelism, and an automatic algorithm to figure out the exact configuration."

---

## SLIDE: Both Papers Agree On (~30 seconds)

"Six points of consensus. Colocation is fundamentally flawed. KV-cache transfer is cheap. Each phase needs different resources and parallelism. Disaggregation gives 2 to 7x improvements. It works for all modern transformer LLMs. And long context windows — which are the trend — make disaggregation even more valuable as the compute asymmetry between phases grows."

---

## SLIDE: Limitations & Future Directions (~45 seconds)

"Shared limitations: both struggle with very few GPUs, both have basic fault tolerance, both use FCFS which can cause convoy effects with mixed request sizes, and both are designed for latency-sensitive workloads — for pure batch throughput, colocation might still be fine.

The exciting open questions: preemptive scheduling with disaggregation, combining heterogeneous hardware with optimized placement, handling million-token contexts where prefill computation grows quadratically, interaction with Mixture-of-Experts routing, and KV-cache compression for extreme context lengths.

The industry has already voted with its feet — SGLang, vLLM, and Mooncake have all adopted disaggregated architectures. Phase disaggregation is becoming the standard paradigm for LLM serving."

---

## SLIDE: Summary (~30 seconds)

"To wrap up. Splitwise characterized production workloads and showed that heterogeneous hardware for different phases achieves 1.4x throughput at 20% lower cost. DistServe formalized goodput optimization and achieved up to 7.4x higher request rates through optimized placement.

The big picture: prefill and decoding are fundamentally different workloads. Treating them as one wastes hardware, power, and money. Disaggregation is the right abstraction.

Thank you. We're happy to take questions."

---

## TOTAL ESTIMATED TIME: ~10 minutes

### Pacing Notes:
- Tradeoff analysis and placement algorithms are the most technical — slow down here
- Evaluation numbers: emphasize the 12.6x SLO improvement for summarization (most dramatic)
- Comparison slide: this is where you tie the whole talk together — don't rush it
- If running short on time, compress the online scheduling slide
- If running long, compress the "Both Papers Agree On" slide (the audience already gets it)
