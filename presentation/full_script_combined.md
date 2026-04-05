# Full Presentation Script
# Phase Disaggregation for LLM Inference
# Berat Celik & Jiayang (Ethan) Chen
# ECE 5545 — Spring 2026

---

# Speaker Script: Berat Celik (Splitwise)
# Target: ~11 minutes

---

## SLIDE 1: Title (20 sec)

Hey everyone, I'm Berat. Me and Ethan are going to talk about phase disaggregation in LLM inference. We're covering two papers, Splitwise and DistServe. I'll do background and Splitwise, then Ethan takes over for DistServe and we wrap up together.

---

## SLIDE 2: Outline (10 sec)

Here's the plan. I'll explain how LLM inference works, why the current approach has problems, then get into Splitwise. Ethan picks it up with DistServe.

---

## SLIDE 3: How LLM Inference Works (1.5 min)

When you send a query to something like ChatGPT, the model goes through two separate phases.

First is prefill, or prompt computation. The model takes your entire input and processes all the tokens in parallel through the transformer layers. At the end, you get your first output token. And as it runs through each layer, it computes Key and Value tensors for attention that get saved as the KV-cache. This cache is critical because the second phase depends on it.

Second is decoding, or token generation. Now the model generates tokens one by one. Each step, it reads the full KV-cache, produces one token, and repeats until done.

Quick example: you ask "Is tomato a fruit?", prefill crunches all 5 tokens at once and produces "Yes." Then decoding generates "comma, it, is, a, fruit, period" one at a time.

---

## SLIDE 4: Phase Characteristics (1.5 min)

Here's what makes this interesting from a systems perspective. These two phases look completely different computationally.

Prefill is compute-bound. Big matrix multiplies, hundreds of tokens at once, GPU fully saturated.

Decoding is memory-bandwidth-bound. One new token at a time, tiny computation. The bottleneck is reading model weights and KV-cache from memory. GPU utilization is low.

They have different latency targets too. For prefill, users care about TTFT, time to first token, how responsive the system feels. For decoding, it's TPOT or TBT, time per output token, the streaming speed.

Two phases, different compute profiles, different bottlenecks, different metrics, and ideally different hardware. That mismatch is what both papers address.

---

## SLIDE 5: Performance Metrics (30 sec)

Quick rundown on the key metrics. TTFT is prefill latency. TBT is streaming speed, needs to be faster than reading speed, about 250 words per minute.

The important one for this talk is goodput: the maximum request rate you can sustain while meeting your latency targets. If your SLO says 90% of requests need TTFT under 250ms and TPOT under 100ms, goodput tells you how many requests per second you can handle while hitting that bar.

---

## SLIDE 6: The Problem (1 min)

So why is this a problem? Every serving system runs both phases on the same GPU, and that causes three issues.

First, interference. Adding one prefill job into a decode batch causes up to a 3x latency hit with short inputs, even worse with longer inputs. It goes both ways.

Second, parallelism coupling. Prefill wants tensor parallelism, decoding wants pipeline parallelism. When they share GPUs, you pick one strategy and the other phase loses.

Third, over-provisioning. A 13B model on one A100 tops out at 1.6 requests per second colocated. Separated, you get 3.3. More than double.

Both papers arrived at the same conclusion: put them on separate hardware.

---

## SLIDE 7: Interference Figure (15 sec)

Here's the actual data. Left panel, short inputs: one prefill job almost triples decode latency. Right panel, 1024 tokens: even worse. That gap is why colocation doesn't work.

---

## SLIDE 8: Splitwise Section Title (transition)

---

## SLIDE 9: Production Trace Insights (1 min)

What makes Splitwise unique is real production data from two Azure LLM services at Microsoft: a coding assistant and a conversation service.

They found these workloads look completely different. Coding has massive prompts, median 1500 tokens, but only generates 13 tokens. Conversation is more balanced, 1020 input and 129 output tokens.

With mixed continuous batching, the machines spend 60 to 70 percent of their time running 20 or fewer tokens in the batch. GPU sitting mostly idle. And even for coding with its huge prompts, most wall-clock time is still in token generation.

---

## SLIDE 10: Trace Distribution Figure (10 sec)

Here are the actual distributions. Coding has massive prompts but tiny outputs. Conversation is more spread out on both sides. These shapes drove the Splitwise design.

---

## SLIDE 11: Hardware Insight (1 min)

Here's where Splitwise gets really interesting. They compared A100 and H100 for each phase separately.

H100 has 3.43x the compute. For prefill, TTFT drops to 0.51x. But token generation only improves to 0.70x. You're paying 2.16x more per hour and the decode phase barely benefits because it's bottlenecked on memory bandwidth, not compute.

This is the main insight: you don't need expensive GPUs for token generation. An A100 does the job at much better cost per token. And if you power-cap token machines to 70%, there's no latency impact. Free savings.

---

## SLIDE 12: Splitwise Architecture (45 sec)

Splitwise has three pools of machines. The Prompt Pool runs compute-heavy GPUs doing prefill. The Token Pool runs cheaper GPUs doing generation. The Mixed Pool is flexible, it handles overflow from either side.

A cluster-level scheduler routes requests, assigning a prompt and token machine for each one. The mixed pool absorbs traffic spikes in either direction.

---

## SLIDE 13: Architecture Figure (10 sec)

Here's the paper's diagram. Cluster-level scheduler on top, prompt pool left, token pool right, InfiniBand for KV-cache transfer, and the mixed pool for overflow.

---

## SLIDE 14: KV-Cache Transfer (45 sec)

The obvious question: doesn't transferring the KV-cache between machines add overhead?

Naively, yes. Wait for full prefill, transfer everything at once: 64% overhead on the second token.

Splitwise does per-layer transfer instead. Each transformer layer ships its KV-cache immediately after computing, overlapping with the next layer's computation. By the time prefill finishes, most of the cache is already there.

End result: 5 to 8 milliseconds of non-overlapped transfer, 0.8% of end-to-end latency. Both papers confirm: KV-cache transfer is not the bottleneck.

---

## SLIDE 15: Cluster Configurations (20 sec)

They evaluate four configurations: all A100s, all H100s, H100 prompt with A100 token, and all H100s with token machines power-capped. An open-source simulator searches the design space.

---

## SLIDE 16: Splitwise Results (20 sec)

Splitwise-AA gets 2.15x more throughput than baseline A100. The headline: up to 1.4x throughput at 20% lower cost, or 2.35x throughput at the same budget. HHcap matches baseline at 25% less power. And it's robust, only 7% throughput drop with the wrong workload.

---

## SLIDE 17: Results Figure (10 sec)

These plots show latency across request rates. Dashed red lines are SLO targets. Splitwise designs stay under those lines at much higher rates than the baselines.

---

## SLIDE 18: Splitwise Summary (20 sec)

To recap: real production traces revealed two fundamentally different workloads. Three-pool architecture with optimized KV-cache transfer. Cheaper GPUs work fine for token generation. Matching hardware to each phase saves money and power.

I'll hand it over to Ethan for DistServe.

---

## TOTAL: ~11 minutes


\newpage


# Speaker Script: Ethan Chen (DistServe)
# Target: ~9 minutes
# Ethan, feel free to rework any of this to match how you actually talk.

---

## SLIDE 19: DistServe Section Title (10 sec)

Thanks Berat. Now I'll go through DistServe, which tackles the same problem from a different angle.

---

## SLIDE 20: Goodput (1 min)

DistServe formalizes what we're optimizing for with goodput: the max request rate while keeping 90% of users within latency targets. Not just raw throughput, but throughput that actually meets SLOs.

Their approach: disaggregate prefill and decoding onto separate GPU instances, then automatically optimize parallelism and resource allocation for each phase independently.

Now the common response to interference is chunked prefill from the Sarathi paper: break prefills into smaller chunks and slot decode tokens alongside them. But chunks too small means unsaturated GPU, too big means no room for decodes. And there's a hidden cost: the KV-cache reloads from HBM for every subsequent chunk, scaling O(N-squared) instead of O(N). It helps a little but doesn't solve it.

---

## SLIDE 21: Tradeoff Analysis (1.5 min)

What's really cool about DistServe is the formal analysis after disaggregation. Each phase becomes its own optimization problem.

For prefill, they model it as an M/D/1 queue. At low request rates, execution time dominates, so tensor parallelism helps since it reduces per-request latency. At high rates, queuing dominates, and pipeline parallelism is better since it increases throughput capacity.

For decoding, a single job barely uses the GPU. Batching is essential. Disaggregation helps here: multiple prefill instances feed one decoder, naturally building bigger batches and better utilization. Batch enough and decoding becomes compute-bound, where parallelism choices matter too.

The key point: after disaggregation, each phase has independent knobs. Different parallelism, batch sizes, GPU counts. Impossible when sharing hardware.

---

## SLIDE 22: DistServe Architecture Figure (10 sec)

Here's the system. Controller dispatches to prefill instances, KV-cache gets pulled by decode instances. Each manages its own GPUs with a parallel runtime.

---

## SLIDE 23: Placement Algorithms (1.5 min)

This is the core contribution. Given a model, workload, SLOs, and cluster hardware, the algorithm automatically finds the best setup.

For fast cross-node networks, Algorithm 1 enumerates parallelism configs for each phase, simulates goodput for each, picks the best, then replicates to hit the target rate. Finishes in under a minute and a half.

For limited bandwidth, Algorithm 2 constrains prefill and decode to the same node, using NVLINK for transfer.

Their simulator is under 2% error compared to real hardware, so you explore the design space in simulation instead of expensive experiments.

Online optimizations handle the rest: batching requests to hit GPU saturation for pipeline bubbles, pull-based KV-cache transfer for bursty traffic, and automatic replanning when workload patterns shift.

---

## SLIDE 24: DistServe Results (1 min)

Evaluated on 32 A100 GPUs across 4 nodes, OPT models from 13B to 175B.

Chatbot on ShareGPT: 2x to 4.6x the request rate of vLLM, 1.6x to 7.4x over DeepSpeed-MII. Sustains 1.8x to 3.2x tighter SLOs.

Code completion on HumanEval: 5.7x higher rate. Big win because code completion needs fast TTFT.

Summarization on LongBench: 4.3x higher rate and 12.6x tighter SLO. Long inputs cause severe interference when colocated.

---

## SLIDE 25: Chatbot Results Figure (15 sec)

Top row: SLO attainment versus request rate. DistServe in blue stays high much longer. Bottom row: under tighter SLOs, the baselines fall apart while DistServe holds.

---

## SLIDE 26: Code and Summarization Figure (10 sec)

Same pattern. Code completion shows a big gap from eliminating prefill interference. Summarization is even more dramatic with long inputs.

---

## SLIDE 27: Ablation (45 sec)

Two key findings. First, KV-cache transfer on OPT-175B is less than 0.1% of total latency. 95% of requests under 30ms delay. Transfer is not the bottleneck.

Second, they gave vLLM an exhaustive parallelism search, called vLLM++. Same performance as default vLLM. Interference cancels out any parallelism gains. You have to disaggregate first.

And the configs DistServe chose are telling: OPT-66B gets tensor parallel 4 for prefill, but tensor parallel 2 with pipeline parallel 2 for decode. Totally different strategies, only possible on separate instances.

---

## SLIDE 28: Latency Breakdown Figure (10 sec)

The bar chart shows transmission is that tiny red sliver, under 0.1%. The CDF confirms 95% of requests see under 30ms transfer delay.

---

## SLIDE 29: Comparison (45 sec)

Both papers arrived at the same conclusion independently: prefill and decoding should not share hardware.

Splitwise focuses on hardware. Token generation doesn't need expensive compute, so use cheaper GPUs. Most useful for cloud providers designing clusters.

DistServe focuses on software. Given your existing hardware, find the best parallelism and placement automatically. Most useful for service operators.

The ideal system would combine both: heterogeneous hardware with automated placement.

---

## SLIDE 30: Limitations and Open Questions (30 sec)

Both agree: colocation is wrong for latency-sensitive workloads, transfer overhead is negligible, each phase wants different resources.

Open questions: preemptive scheduling, heterogeneous hardware with automated placement, million-token contexts, and mixture-of-experts interactions. SGLang, vLLM, and Mooncake already support disaggregation. This isn't research-only anymore.

---

## SLIDE 31: Summary (20 sec)

Splitwise: 1.4x throughput at 20% lower cost, or 2.35x at the same budget. DistServe: up to 7.4x higher request rates.

Prefill and decoding are different workloads. Treating them as one wastes resources. Disaggregation fixes that.

---

## SLIDES 32-33: References & Thank You

Thanks, we're happy to take questions.

---

## TOTAL: ~9 minutes
