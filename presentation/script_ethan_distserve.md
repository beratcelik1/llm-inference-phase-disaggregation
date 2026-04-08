# Speaker Script: Ethan Chen (DistServe)
# Target: ~9 minutes
# Ethan, feel free to rework any of this to match how you actually talk.

---

## SLIDE 18: DistServe Section Title (1 min)

Thanks Berat. Now I'll go through DistServe, another important paper from 2024. It tackles the same problem, but just one level up, on the orchestration / allocation layer. 

The problem, just to reiterate, is that:
Before DistServe, systems tend to colocate prefill and decode, which means both stages need to share the same parallelism and hardware configurations, and other resource. 

But they have very different characteristics - (prefill is compute bound and decode is memory bound) and they have different goals and metrics to optimize for.

If we couple these two stages together, we lose out on opportunities to solve the problem of interference from the root. 

---

## SLIDE 19: Goodput / How DistServe Works (2 min)

DistServe introduced this concept of goodput. It is basically the maximum throughput, when the system can sustain let's say 90% of user requests with TTFT less than 400 miliseconds, and TPOT less than 40 miliseconds. which shown by the dotted lines.

This graph basically shows the tradeoff between throughput on the x axis, and latency on the y axis.  When you look at the blue line, for existing mixed chunk systems, one A100 can only serve 1.6 request per second. But the same GPU can serve 5.6 rps for prefill or 10 rps for decode if it's disaggregated.

So for example, Imagine we have 3 A100s using mixed chunk, we could serve 3 * 1.6, or 4.8 rps, but if we allocate 2 A100s for prefill and 1 for decode, we could serve 10 rps, which is more than double the goodput.

The reason that mixed chunk is slow here is that it introduces blocking, if a new long requests comes in, we need to spend a lot of time computing the KV cache, which slows down the decode, hurts TPOT, which is kind of similar to head of line blocking. But if we prioritize those smaller decode tasks instead, like a lot of production LLM systems do, then we might risk extremely long TTFT for the long requests, which is similar to starvation.

---

## SLIDE 20: Why Not Chunked Prefill? (1 min)

Now the common response to interference is chunked prefill with continuous batching, from the Sarathi paper. the main idea is we break a longer prefill into smaller chunks and attach decode tokens in the batch. But it doesn't eliminate the problem. If chunk size is set too small, then prefill will take too long, if it's set too big, then it kind of defeats the purpose of piggybacking for decode tokens.

Also there's way more KV cache transfers, because we need to repeatedly load the KV cache of previous chunk from HBM to SRAM. Turning it into O of (N-squared)

---

## SLIDE 21: Formal Analysis / Parallelism Tradeoff (2 min)

Let's talk about the formal analysis, after disaggregation, each phase becomes its own optimization problem where we could apply different parallelism stratgies.

For prefill, they modeled it as an M/D/1 queue, which means poisson request arrival, each request take deterministic time, and on one server.

Average TTFT is execution time which is the first terms, D, plus the queueing delay, which is the second term, where R is the arrival rate.

At low request rates, execution time dominates, because we dont have that much queuing delay.
Tensor parallelism is the clear winner because it slashes the execution time for one request or D.
by a factor of K. If have 2 GPUs, K should be 2 but because of communication costs, it is usually 1.8 or 1.7 realistically.

At higher request rates, queuing delay dominates, and pipeline parallelism is better since it increases throughput capacity, so we can handle more requests at the same time.

For decoding, a single job barely uses the GPU. Batching is essential. Disaggregation helps here: multiple prefill instances feeding into one decode instance, so we naturally building bigger batches and better the GPUs utilization. If Batch enough and decoding becomes compute-bound, and we can do the same parallelism tradeoff we did for prefill.

The key point: after disaggregation, each phase has independent knobs. Different parallelism, batch sizes, GPU counts. Impossible when sharing hardware.

---

## SLIDE 22: DistServe Architecture Figure (10 sec)

Here's the system. Controller dispatches requests to prefill instances, KV-cache gets pulled by decode instances. Each manages its own GPUs with a parallel runtime.

---

## SLIDE 23: Placement Algorithms (2 min)

Now let's talk about placement algorithms. One of the core contributions is that, given a model, workload, SLOs, the algorithm automatically finds the best parallelism stratgey and number of instances that maximize the per-gpu goodput.

For fast cross-node networks, Algorithm 1 enumerates parallelism configs for each phase, simulates goodput for each, picks the best, then replicates to hit the target reequest rate. 

For limited bandwidth networks, Algorithm 2 constrains prefill and decode to the same node, using NVLINK for transfer.

Their simulator is under 2% error compared to real hardware, so you explore the design space in simulation instead of expensive real experiments.

Online optimizations handle the rest: batching requests to hit GPU saturation for pipeline bubbles, pull-based KV-cache transfer for bursty traffic and avoid memory overload on decode instances, and periods automatic replanning when the workload shift.

---

## SLIDE 24: DistServe Results (1 min)

They evaluated with 32 A100s across 4 nodes, OPT models from 13B to 175B.

On the conversational chatbot workload or ShareGPT: we see 2x to 4.6x the request rate of vLLM, 1.6x to 7.4x over DeepSpeed-MII. Sustains 1.8x to 3.2x tighter SLOs.

On code completion workloads, we see 5.7x higher rate over vLLM.

On summarization workloads, or LongBench: 4.3x higher rate and 12.6x tighter SLO. This is because long inputs cause severe interference when colocated.

---

## SLIDES 25-26: Results Figures (15 sec)

And then these are the actual result figures.

---

## SLIDE 27: Comparison (45 sec)

Both papers arrived at the same conclusion independently: prefill and decoding should not share hardware.

Splitwise focuses on hardware. Token generation doesn't need expensive compute, so use cheaper GPUs. Most useful for cloud providers designing clusters.

DistServe focuses on software. Given your existing hardware, find the best parallelism and placement automatically. Most useful for service operators.

The ideal system would combine both: heterogeneous hardware with automated placement. 
SGLang, vLLM, and Mooncake already support disaggregation. This isn't research-only anymore.

---

## SLIDES 28-29: References & Thank You

Thanks, we're happy to take questions.

---

## TOTAL: ~9 minutes
