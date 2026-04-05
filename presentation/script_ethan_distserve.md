# Speaker Script: Ethan Chen (DistServe)
# Target: ~9 minutes
# Ethan, feel free to rework any of this to match how you actually talk.

---

## SLIDE 18: DistServe Section Title (10 sec)

Thanks Berat. Now I'll go through DistServe, which tackles the same problem from a different angle.

---

## SLIDE 19: Goodput (1 min)

DistServe formalizes what we're optimizing for with goodput: the max request rate while keeping 90% of users within latency targets. Not just raw throughput, but throughput that actually meets SLOs.

Their approach: disaggregate prefill and decoding onto separate GPU instances, then automatically optimize parallelism and resource allocation for each phase independently.

Now the common response to interference is chunked prefill from the Sarathi paper: break prefills into smaller chunks and slot decode tokens alongside them. But chunks too small means unsaturated GPU, too big means no room for decodes. And there's a hidden cost: the KV-cache reloads from HBM for every subsequent chunk, scaling O(N-squared) instead of O(N). It helps a little but doesn't solve it.

---

## SLIDE 20: Tradeoff Analysis (1.5 min)

What's really cool about DistServe is the formal analysis after disaggregation. Each phase becomes its own optimization problem.

For prefill, they model it as an M/D/1 queue. At low request rates, execution time dominates, so tensor parallelism helps since it reduces per-request latency. At high rates, queuing dominates, and pipeline parallelism is better since it increases throughput capacity.

For decoding, a single job barely uses the GPU. Batching is essential. Disaggregation helps here: multiple prefill instances feed one decoder, naturally building bigger batches and better utilization. Batch enough and decoding becomes compute-bound, where parallelism choices matter too.

The key point: after disaggregation, each phase has independent knobs. Different parallelism, batch sizes, GPU counts. Impossible when sharing hardware.

---

## SLIDE 21: DistServe Architecture Figure (10 sec)

Here's the system. Controller dispatches to prefill instances, KV-cache gets pulled by decode instances. Each manages its own GPUs with a parallel runtime.

---

## SLIDE 22: Placement Algorithms (1.5 min)

This is the core contribution. Given a model, workload, SLOs, and cluster hardware, the algorithm automatically finds the best setup.

For fast cross-node networks, Algorithm 1 enumerates parallelism configs for each phase, simulates goodput for each, picks the best, then replicates to hit the target rate. Finishes in under a minute and a half.

For limited bandwidth, Algorithm 2 constrains prefill and decode to the same node, using NVLINK for transfer.

Their simulator is under 2% error compared to real hardware, so you explore the design space in simulation instead of expensive experiments.

Online optimizations handle the rest: batching requests to hit GPU saturation for pipeline bubbles, pull-based KV-cache transfer for bursty traffic, and automatic replanning when workload patterns shift.

---

## SLIDE 23: DistServe Results (1 min)

Evaluated on 32 A100 GPUs across 4 nodes, OPT models from 13B to 175B.

Chatbot on ShareGPT: 2x to 4.6x the request rate of vLLM, 1.6x to 7.4x over DeepSpeed-MII. Sustains 1.8x to 3.2x tighter SLOs.

Code completion on HumanEval: 5.7x higher rate. Big win because code completion needs fast TTFT.

Summarization on LongBench: 4.3x higher rate and 12.6x tighter SLO. Long inputs cause severe interference when colocated.

---

## SLIDE 24: Chatbot Results Figure (15 sec)

Top row: SLO attainment versus request rate. DistServe in blue stays high much longer. Bottom row: under tighter SLOs, the baselines fall apart while DistServe holds.

---

## SLIDE 25: Code and Summarization Figure (10 sec)

Same pattern. Code completion shows a big gap from eliminating prefill interference. Summarization is even more dramatic with long inputs.

---

## SLIDE 26: Ablation (45 sec)

Two key findings. First, KV-cache transfer on OPT-175B is less than 0.1% of total latency. 95% of requests under 30ms delay. Transfer is not the bottleneck.

Second, they gave vLLM an exhaustive parallelism search, called vLLM++. Same performance as default vLLM. Interference cancels out any parallelism gains. You have to disaggregate first.

And the configs DistServe chose are telling: OPT-66B gets tensor parallel 4 for prefill, but tensor parallel 2 with pipeline parallel 2 for decode. Totally different strategies, only possible on separate instances.

---

## SLIDE 27: Latency Breakdown Figure (10 sec)

The bar chart shows transmission is that tiny red sliver, under 0.1%. The CDF confirms 95% of requests see under 30ms transfer delay.

---

## SLIDE 28: Comparison (45 sec)

Both papers arrived at the same conclusion independently: prefill and decoding should not share hardware.

Splitwise focuses on hardware. Token generation doesn't need expensive compute, so use cheaper GPUs. Most useful for cloud providers designing clusters.

DistServe focuses on software. Given your existing hardware, find the best parallelism and placement automatically. Most useful for service operators.

The ideal system would combine both: heterogeneous hardware with automated placement.

---

## SLIDE 29: Limitations and Open Questions (30 sec)

Both agree: colocation is wrong for latency-sensitive workloads, transfer overhead is negligible, each phase wants different resources.

Open questions: preemptive scheduling, heterogeneous hardware with automated placement, million-token contexts, and mixture-of-experts interactions. SGLang, vLLM, and Mooncake already support disaggregation. This isn't research-only anymore.

---

## SLIDE 30: Summary (20 sec)

Splitwise: 1.4x throughput at 20% lower cost, or 2.35x at the same budget. DistServe: up to 7.4x higher request rates.

Prefill and decoding are different workloads. Treating them as one wastes resources. Disaggregation fixes that.

---

## SLIDES 31-32: References & Thank You

Thanks, we're happy to take questions.

---

## TOTAL: ~9 minutes
