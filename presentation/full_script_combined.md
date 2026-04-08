# Full Presentation Script
# Phase Disaggregation for LLM Inference
# Berat Celik & Jiayang (Ethan) Chen
# ECE 5545 — Spring 2026

---

# Speaker Script: Berat Celik (Splitwise)
# Target: ~11 minutes

---

## SLIDE 1: Title (20 sec)

Hey everyone, I'm Berat and this is Ethan. We're presenting on phase disaggregation in LLM inference, covering two papers: Splitwise and DistServe. I'll start with how inference works, why the current approach breaks down, and how Splitwise solves it. Then Ethan takes DistServe and we'll compare.

---

## SLIDE 2: How LLM Inference Works (1.5 min)

When you send a query to something like ChatGPT, the model goes through two separate phases.

First is prefill, or prompt computation. The model takes your entire input and processes all the tokens in parallel through the transformer layers. At the end, you get your first output token. And as it runs through each layer, it computes Key and Value tensors for attention that get saved as the KV-cache. This cache is critical because the second phase depends on it.

Second is decoding, or token generation. Now the model generates tokens one by one. Each step, it reads the full KV-cache, produces one token, and repeats until done.

Quick example: you ask "Is tomato a fruit?", prefill crunches all 5 tokens at once and produces "Yes." Then decoding generates "comma, it, is, a, fruit, period" one at a time.

---

## SLIDE 3: Phase Characteristics (1.5 min)

Here's what makes this interesting from a systems perspective. These two phases look completely different computationally.

Prefill is compute-bound. Big matrix multiplies, hundreds of tokens at once, GPU fully saturated.

Decoding is memory-bandwidth-bound. One new token at a time, tiny computation. The bottleneck is reading model weights and KV-cache from memory. GPU utilization is low.

They have different latency targets too. For prefill, users care about TTFT, time to first token, how responsive the system feels. For decoding, it's TPOT or TBT, time per output token, the streaming speed.

Two phases, different compute profiles, different bottlenecks, different metrics, and ideally different hardware. That mismatch is what both papers address.

---

## SLIDE 4: Performance Metrics (30 sec)

Quick rundown on the key metrics. TTFT is prefill latency. TBT is streaming speed, needs to be faster than reading speed, about 250 words per minute.

The important one for this talk is goodput: the maximum request rate you can sustain while meeting your latency targets. If your SLO says 90% of requests need TTFT under 250ms and TPOT under 100ms, goodput tells you how many requests per second you can handle while hitting that bar.

---

## SLIDE 5: The Problem (1 min)

So why is this a problem? Every serving system runs both phases on the same GPU, and that causes three issues.

First, interference. Adding one prefill job into a decode batch causes up to a 3x latency hit with short inputs, even worse with longer inputs. It goes both ways.

Second, parallelism coupling. Prefill wants tensor parallelism, decoding wants pipeline parallelism. When they share GPUs, you pick one strategy and the other phase loses.

Third, over-provisioning. A 13B model on one A100 tops out at 1.6 requests per second colocated. Separated, you get 3.3. More than double.

Both papers arrived at the same conclusion: put them on separate hardware.

---

## SLIDE 6: Interference Figure (15 sec)

Here's the actual data. Left panel, short inputs: one prefill job almost triples decode latency. Right panel, 1024 tokens: even worse. That gap is why colocation doesn't work.

---

## SLIDE 7: Splitwise Section Title (transition)

---

## SLIDE 8: Production Trace Insights (1 min)

What makes Splitwise unique is real production data from two Azure LLM services at Microsoft: a coding assistant and a conversation service.

They found these workloads look completely different. Coding has massive prompts, median 1500 tokens, but only generates 13 tokens. Conversation is more balanced, 1020 input and 129 output tokens.

With mixed continuous batching, the machines spend 60 to 70 percent of their time running 20 or fewer tokens in the batch. GPU sitting mostly idle. And even for coding with its huge prompts, most wall-clock time is still in token generation.

---

## SLIDE 9: Trace Distribution Figure (10 sec)

Here are the actual distributions. Coding has massive prompts but tiny outputs. Conversation is more spread out on both sides. These shapes drove the Splitwise design.

---

## SLIDE 10: Hardware Insight (1 min)

Here's where Splitwise gets really interesting. They compared A100 and H100 for each phase separately.

H100 has 3.43x the compute. For prefill, TTFT drops to 0.51x. But token generation only improves to 0.70x. You're paying 2.16x more per hour and the decode phase barely benefits because it's bottlenecked on memory bandwidth, not compute.

This is the main insight: you don't need expensive GPUs for token generation. An A100 does the job at much better cost per token. And if you power-cap token machines to 70%, there's no latency impact. Free savings.

---

## SLIDE 11: Splitwise Architecture (45 sec)

Splitwise has three pools of machines. The Prompt Pool runs compute-heavy GPUs doing prefill. The Token Pool runs cheaper GPUs doing generation. The Mixed Pool is flexible, it handles overflow from either side.

A cluster-level scheduler routes requests, assigning a prompt and token machine for each one. The mixed pool absorbs traffic spikes in either direction.

---

## SLIDE 12: Architecture Figure (10 sec)

Here's the paper's diagram. Cluster-level scheduler on top, prompt pool left, token pool right, InfiniBand for KV-cache transfer, and the mixed pool for overflow.

---

## SLIDE 13: KV-Cache Transfer (45 sec)

The obvious question: doesn't transferring the KV-cache between machines add overhead?

Naively, yes. Wait for full prefill, transfer everything at once: 64% overhead on the second token.

Splitwise does per-layer transfer instead. Each transformer layer ships its KV-cache immediately after computing, overlapping with the next layer's computation. By the time prefill finishes, most of the cache is already there.

End result: 5 to 8 milliseconds of non-overlapped transfer, 0.8% of end-to-end latency. Both papers confirm: KV-cache transfer is not the bottleneck.

---

## SLIDE 14: Cluster Configurations (20 sec)

They evaluate four configurations: all A100s, all H100s, H100 prompt with A100 token, and all H100s with token machines power-capped. An open-source simulator searches the design space.

---

## SLIDE 15: Splitwise Results (20 sec)

Splitwise-AA gets 2.15x more throughput than baseline A100. The headline: up to 1.4x throughput at 20% lower cost, or 2.35x throughput at the same budget. HHcap matches baseline at 25% less power. And it's robust, only 7% throughput drop with the wrong workload.

---

## SLIDE 16: Results Figure (10 sec)

These plots show latency across request rates. Dashed red lines are SLO targets. Splitwise designs stay under those lines at much higher rates than the baselines.

---

## SLIDE 17: Splitwise Summary (20 sec)

To recap: real production traces revealed two fundamentally different workloads. Three-pool architecture with optimized KV-cache transfer. Cheaper GPUs work fine for token generation. Matching hardware to each phase saves money and power.

I'll hand it over to Ethan for DistServe.

---

## TOTAL: ~11 minutes


\newpage


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
