# Speaker Script: Ethan Chen (DistServe)
# Target: ~10 minutes
# Ethan, feel free to rework any of this to match how you actually talk.

---

## SLIDE: DistServe Section Title (10 sec)

Thanks Berat. So now I'll go through DistServe, which tackles the same core problem but from a different angle.

---

## SLIDE: DistServe Motivation (1 min)

So Berat showed us why colocation fails. DistServe's approach is to formalize what we're actually optimizing for, and they introduce this concept of goodput.

Goodput is basically: what's the max request rate you can handle while keeping, say, 90% of your users within their latency targets? It's not just about raw throughput. A system that processes a ton of requests but violates SLOs left and right isn't useful.

What DistServe does is disaggregate prefill and decoding onto separate GPU instances, and then it runs an optimization to find the best parallelism strategy and resource allocation for each phase independently. And it does this automatically through a placement algorithm, you don't have to tune it by hand.

---

## SLIDE: Interference Deep Dive (1 min)

Berat already covered the interference problem at a high level. Let me show the specific numbers from DistServe.

In their experiments with a 13B model, a decode-only batch runs at about 5ms per step. You add one prefill job and it jumps to 15ms. With longer inputs at 1024 tokens, the picture gets much worse.

Now the common response is chunked prefill, from the Sarathi paper. The idea is to break up long prefills into smaller chunks and slot decode tokens in alongside them. But there are real problems with this. If your chunks are too small, you're not saturating the GPU. If they're too big, there's no room for decode work. And there's a hidden quadratic cost: the KV-cache has to be reloaded from HBM for every subsequent chunk, so for N chunks you're loading O(N-squared) data instead of O(N). It helps a little but it doesn't fix the underlying issue.

---

## SLIDE: Tradeoff Analysis (1.5 min)

What I think is really cool about DistServe is the formal analysis they do after disaggregation. Once you've separated the phases, each one becomes its own optimization problem and you can reason about them independently.

For prefill instances, they model it as an M/D/1 queue. Your average TTFT is execution time plus queuing delay. At low request rates, the execution time dominates, so tensor parallelism helps because it reduces per-request latency. But as the rate goes up, queuing starts to dominate, and pipeline parallelism becomes better because it increases the system's total throughput capacity.

For decoding, a single job barely uses the GPU because it's bandwidth-bound. So batching is essential. And here's where disaggregation really helps: you can have multiple prefill instances feeding work into one decoding instance, which naturally builds up bigger decode batches and much better utilization. If you batch enough, decoding actually starts to become compute-bound, and then parallelism choices matter there too.

The point is that after disaggregation, you have separate knobs for each phase. Different parallelism, different batch sizes, different numbers of GPUs. You simply cannot do this when both phases share the same hardware.

---

## SLIDE: DistServe Architecture Figure (10 sec)

Here's the system diagram. Requests come into the controller at top, get dispatched to prefill instances on the left, and then the KV-cache gets pulled by decode instances on the right. Each instance has its own set of GPUs managed by a parallel runtime.

---

## SLIDE: System Architecture (40 sec)

Here's how the system is structured. Requests come in to a central controller. It sends each request to whichever prefill instance has the shortest queue. After prefill finishes, the KV-cache gets pulled by the least loaded decode instance, and generation begins.

The whole thing is built on top of vLLM's architecture. About 6,500 lines of Python for the scheduling and orchestration, 8,100 lines of C++ and CUDA for the execution engine. It uses Ray for GPU worker management and has an OpenAI-compatible API.

---

## SLIDE: Placement Algorithms (1.5 min)

This is really the core contribution of DistServe. Given a model, a workload pattern, SLO requirements, and your cluster hardware, the algorithm automatically finds the best setup.

For clusters with fast cross-node networking like InfiniBand, they use Algorithm 1. It goes through all feasible parallelism configurations for prefill and decoding. For each one, it runs an event-driven simulator to estimate goodput. It picks the best config for each phase, then figures out how many replicas you need to hit your target traffic rate. The search space is manageable, O(NM-squared) where M is GPUs per node, and it finishes in under about a minute and a half even for large clusters.

If your cross-node bandwidth is limited, Algorithm 2 adds a constraint that prefill and decode have to live on the same physical node so they can use NVLINK for the KV-cache transfer.

A really important piece is their simulator. It models the compute and memory access patterns for each operation, and when they compared it against real system runs, the error was under 2%. So you can explore the design space in simulation instead of running expensive hardware experiments.

---

## SLIDE: Online Scheduling (40 sec)

Beyond the offline placement, there are some online optimizations worth mentioning.

For pipeline bubbles caused by different prompt lengths, they batch requests to hit the GPU saturation point. Short prompts get grouped together, long ones run alone.

For handling bursty traffic, decode instances pull KV-caches from prefill instances when they're ready, instead of getting flooded with pushes. The prefill machine holds onto the cache in GPU memory as a buffer.

And the system can replan. There's a profiler watching workload patterns, and if things shift significantly, it reruns the placement algorithm. That takes seconds, and reloading model weights takes a few minutes. Much faster than workloads typically change.

---

## SLIDE: Results (1.5 min)

They evaluated on 32 A100 GPUs across 4 nodes, testing OPT models from 13B to 175B against vLLM and DeepSpeed-MII.

On the chatbot workload with ShareGPT data, DistServe handles 2x to 4.6x the request rate of vLLM. Against DeepSpeed-MII it's 1.6x to 7.4x. And it can sustain 1.8x to 3.2x tighter SLO requirements than vLLM.

Code completion on HumanEval: 5.7x higher rate and 1.4x tighter SLO. This one is interesting because code completion needs really fast TTFT, and eliminating prefill interference makes a huge difference.

Summarization on LongBench is the most dramatic result: 4.3x higher rate and 12.6x tighter SLO. Long inputs create really bad interference when the phases are colocated. Disaggregation eliminates that completely.

---

## SLIDE: Chatbot Results Figure (15 sec)

Here's the chatbot evaluation across all three model sizes. Top row: SLO attainment drops as request rate increases. DistServe in blue stays high much longer than vLLM or DeepSpeed-MII. Bottom row: when you tighten the SLOs, DistServe still maintains good attainment while the baselines fall apart.

---

## SLIDE: Code and Summarization Figure (15 sec)

Same story for code completion and summarization. Code completion shows a big gap because it needs really fast TTFT and disaggregation eliminates the prefill interference. Summarization is even more dramatic because the long inputs cause severe interference when colocated.

---

## SLIDE: Ablation and Latency (1 min)

Two findings I want to highlight.

First, KV-cache transfer cost. Even on OPT-175B, the biggest model they tested, transmission is less than 0.1% of total latency. 95% of requests see under 30ms of transfer delay. So the worry that splitting phases across machines would create a big communication bottleneck just doesn't hold up on modern hardware. Splitwise found the same thing.

Second, the ablation. They took vLLM and gave it an exhaustive parallelism search, called vLLM++. Same performance as vanilla vLLM. Why? Because when the phases are colocated, interference cancels out whatever gains you get from better parallelism. You have to disaggregate first before parallelism optimization even matters.

And check out the actual configs DistServe chose. For OPT-66B, prefill gets tensor parallel 4 with no pipelining, decoding gets tensor parallel 2 with pipeline parallel 2. Totally different strategies. That's only possible when they're on separate instances.

---

## SLIDE: Latency Breakdown Figure (15 sec)

This figure really drives the point home. The bar chart on the left shows the latency breakdown: transmission is that tiny red sliver, less than 0.1% of total time. On the right, the CDF shows 95% of requests see under 30 milliseconds of transfer delay. The concern about splitting phases across machines adding overhead just doesn't hold up.

---

## SLIDE: Comparison (1 min)

So how do Splitwise and DistServe relate to each other? They were developed independently, came out around the same time, and arrived at the same fundamental conclusion: prefill and decoding should not share hardware.

But they approach it differently. Splitwise focuses on the hardware side. Its key finding is that token generation doesn't need expensive compute, so you can use older or cheaper GPUs and save money and power. It's most useful for cloud providers designing new clusters.

DistServe focuses on the software side. Given whatever hardware you have, it finds the best parallelism and placement for each phase automatically. It's more useful for people already running LLM services on existing clusters.

The ideal system would probably combine both: heterogeneous hardware from Splitwise with the optimization algorithms from DistServe.

---

## SLIDE: Consensus and Future (40 sec)

Both papers agree on the fundamentals. Colocation is the wrong approach for latency-sensitive workloads. Transfer overhead is negligible. Each phase wants different resources. And disaggregation consistently delivers 2x to 7x improvements.

The open questions are around preemptive scheduling, combining heterogeneous hardware with automated placement, handling million-token contexts where the asymmetry gets even worse, and how all of this interacts with mixture-of-experts models.

The industry has already moved on this. SGLang, vLLM, and Mooncake all support disaggregated architectures now. This isn't a research-only idea anymore.

---

## SLIDE: Summary (30 sec)

To wrap it up. Splitwise showed that matching hardware to each phase gets you 1.4x throughput at 20% lower cost, or 2.35x throughput at the same budget. DistServe showed that optimizing parallelism and placement per phase gets you up to 7.4x higher request rates.

The takeaway is simple: prefill and decoding are different workloads. Treating them as one wastes resources. Disaggregation fixes that.

Thanks, we're happy to take questions.

---

## TOTAL: ~10 minutes
