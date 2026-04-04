# Full Presentation Script
# Phase Disaggregation for LLM Inference
# Berat Celik & Jiayang (Ethan) Chen
# ECE 5545 — Spring 2026
# Total: ~22 minutes

---

# Speaker Script: Berat Celik (Splitwise)
# Target: ~12 minutes

---

## SLIDE: Title (20 sec)

Hey everyone, I'm Berat. Me and Ethan are going to talk about phase disaggregation in LLM inference. We're covering two papers that came out around the same time, Splitwise and DistServe. I'll go through the background, the motivation, and then do a deep dive on Splitwise. After that Ethan will take over for DistServe and we'll wrap up with a comparison.

---

## SLIDE: Outline (15 sec)

So here's the plan. I'll start by explaining how LLM inference works, why the current approach has problems, and then get into how Splitwise solves them. Ethan picks it up from there with DistServe and the broader discussion.

---

## SLIDE: How LLM Inference Works (2 min)

Alright so when you send a query to something like ChatGPT or LLaMA, the model doesn't just spit out the whole answer at once. It actually goes through two separate phases.

The first one is called prefill, or prompt computation. This is where the model takes your entire input, all the tokens, and processes them in parallel through the transformer layers. At the end of this, you get your first output token. And something important happens here: as the model runs through each layer, it computes these Key and Value tensors for the attention mechanism. These get saved as what's called the KV-cache. This cache is critical because the second phase depends on it.

The second phase is decoding, or token generation. Now the model is generating tokens one by one. Each time it produces a token, it needs to look back at everything that came before using that KV-cache. So it generates one token, reads the cache, generates the next one, reads the cache again, and so on until it's done.

Think of it like this: if you ask "Is tomato a fruit?", the prefill phase crunches all 5 of those tokens at once and gives you "Yes." Then decoding kicks in and generates "comma, it, is, a, fruit, period" one at a time.

---

## SLIDE: Phase Characteristics (2 min)

Now here's the thing that makes all of this interesting from a systems perspective. These two phases look completely different computationally.

Prefill is compute-bound. You're running big matrix multiplies, processing hundreds or thousands of tokens at once. The GPU is fully saturated, power draw is maxed out near TDP. It's doing heavy work.

Decoding is the opposite. It's memory-bandwidth-bound. You're only processing one new token at a time per request, so the actual computation is tiny. The bottleneck is reading the model weights and KV-cache from memory. GPU utilization is low, power draw is low, and most of the time the compute units are just waiting around.

And they have different latency targets too. Users care about TTFT, time to first token, for the prefill phase. That's how responsive the system feels. For decoding, what matters is TPOT or TBT, time per output token, that's the streaming speed as you watch tokens appear.

So you've got two phases with different compute profiles, different bottlenecks, different metrics, and ideally they'd want different hardware and different parallelism strategies. That mismatch is what both papers are trying to address.

---

## SLIDE: Performance Metrics (40 sec)

Quick rundown on the metrics we'll reference. TTFT, time to first token, that's prefill latency. TBT, time between tokens, that's streaming speed. The TBT has to be faster than reading speed, roughly 250 words per minute, otherwise the user notices lag.

The really important one for this talk is goodput. It's not just raw throughput. Goodput is the maximum request rate you can sustain while actually meeting your latency targets. So if your SLO says 90% of chatbot requests need TTFT under 250 milliseconds and TPOT under 100 milliseconds, goodput tells you how many requests per second you can handle while hitting that bar. This is what matters in production.

---

## SLIDE: The Problem (1.5 min)

So why is any of this a problem? Because every serving system out there right now runs both phases on the same GPU. And that causes real issues.

The biggest one is interference. If you look at DistServe's Figure 2, when you add just one prefill job into a batch of decoding requests, decoding latency jumps from about 5 milliseconds to 15 milliseconds. That's a 3x hit. With longer inputs it gets even worse. And it goes both ways: decode jobs slow down prefill too.

Then there's the parallelism problem. Prefill works best with tensor parallelism because you want to reduce execution time. Decoding benefits more from pipeline parallelism for better throughput scaling. But if they're on the same GPUs, you have to pick one strategy. So one phase is always getting a raw deal.

And the result of all this is over-provisioning. Take a 13B model on one A100. With colocation you max out at about 1.6 requests per second. If you separate the phases, you can get 3.3 requests per GPU. That's more than double. And at these GPU prices, that difference is real money.

Both papers independently came to the same conclusion: just put them on separate hardware.

---

## SLIDE: Interference Figure (15 sec)

And this is the actual data from DistServe. On the left with short inputs, one prefill job almost triples decode latency. On the right with longer inputs at 1024 tokens, it gets even worse. The dotted line is decode-only, the solid line is with one prefill mixed in. That gap is why colocation is the problem.

---

## SLIDE: Production Trace Insights (1.5 min)

So what makes Splitwise different from DistServe is that the authors had access to real production data. They pulled traces from two Azure LLM services at Microsoft, a coding assistant and a conversation service.

And they found some really interesting things. First, these workloads look totally different. The coding service has massive prompts, median 1500 tokens, but it only generates like 13 tokens of output. The conversation service is more balanced, about 1020 input tokens and 129 output tokens.

Second, and this was surprising to me, with mixed continuous batching, the machines spend 60 to 70 percent of their time running 20 tokens or fewer in the batch. That's the GPU sitting mostly idle during token generation.

Third, even for the coding workload where you have these huge prompts and tiny outputs, most of the wall-clock time is still spent on token generation. A prompt with 1500 tokens on BLOOM-176B takes about the same time as generating just 6 output tokens. Token generation dominates the end-to-end time.

---

## SLIDE: Trace Distribution Figure (15 sec)

Here are the actual distributions. Left panel is input tokens, right is output tokens. You can see how different these two services look. Coding has massive prompts but tiny outputs. Conversation is more spread out on both sides. These shapes are what drove the Splitwise design.

---

## SLIDE: Hardware Insight (1.5 min)

Now here's where Splitwise gets really interesting and diverges from DistServe. They looked at performance across A100 and H100 GPUs for each phase separately.

The H100 has 3.43 times the compute of an A100. And for prefill, that advantage shows up. TTFT drops to 0.51x. Makes sense, prefill is compute-bound, more compute helps.

But look at token generation. TBT only improves to 0.70x. So you're paying 2.16x more per hour for the H100, but the decode phase barely benefits because it's not bottlenecked on compute. It's bottlenecked on memory bandwidth, which only improved 1.64x.

This is Splitwise's main insight: you don't need expensive GPUs for token generation. An A100 does the job just fine at much better cost per token.

And there's a power angle too. The prompt phase draws power near TDP and actually uses those watts productively. Token generation? The power draw is basically flat no matter how many tokens you batch. The GPU is pulling hundreds of watts but barely using the compute. If you power-cap token machines to 70%, there's no latency impact at all. Free savings.

---

## SLIDE: Architecture (1 min)

So Splitwise's design has three pools of machines. The Prompt Pool runs the compute-heavy GPUs, H100s ideally, doing prefill. The Token Pool runs cheaper GPUs, A100s or power-capped H100s, doing generation. And there's a Mixed Pool that's flexible, it can handle either phase depending on what's needed.

A cluster-level scheduler sits on top and routes incoming requests. It assigns a prompt machine and a token machine for every request. Each machine also has its own local scheduler managing batching and memory.

The nice thing about the mixed pool is that it absorbs traffic spikes. If prompts are backing up, mixed machines help with prefill. If there's a burst of decode work, they shift over. And when things are quiet they go back to their home pool.

---

## SLIDE: Architecture Figure (10 sec)

This is the diagram from the paper. You can see the cluster-level scheduler at top routing requests, the prompt pool on the left, token pool on the right, InfiniBand connecting them for KV-cache transfer, and the mixed pool that can flex between both.

---

## SLIDE: KV-Cache Transfer (1 min)

The obvious question with disaggregation is: doesn't transferring the KV-cache between machines add a ton of overhead?

If you do it naively, yes. Wait for the whole prefill to finish, then ship the entire KV-cache over. That adds 64% overhead to the second token's latency. Not great.

Splitwise fixes this with per-layer transfer. As each transformer layer finishes its computation during prefill, it immediately ships that layer's KV-cache to the token machine using zero-copy RDMA over InfiniBand. The transfer runs in parallel with the computation of the next layer. By the time prefill is done, most of the cache is already there.

The end result: about 5 to 8 milliseconds of non-overlapped transfer, which is 0.8% of end-to-end latency. For the second token specifically, 16% overhead instead of 64%. Both papers confirm this independently: KV-cache transfer is not the bottleneck on modern hardware.

---

## SLIDE: Cluster Designs & Results (1 min)

Splitwise evaluates four cluster configurations. All A100s, all H100s, H100s for prompt with A100s for tokens, and all H100s with the token machines power-capped. They built an open-source simulator to search this design space.

The results: Splitwise-AA, which is the all-A100 configuration, gets 2.15x more throughput than a baseline A100 cluster. The paper's headline numbers are up to 1.4x throughput at 20% lower cost, or up to 2.35x throughput at the same cost and power. For power optimization, HHcap matches baseline throughput at 25% less power.

And it's robust. Running the wrong workload on a cluster only costs you about 7% throughput. The mixed pool absorbs the mismatch.

---

## SLIDE: Results Figure (15 sec)

These plots show the latency metrics at different request rates for all four cluster configurations. The dashed red lines are the SLO targets. Notice how the Splitwise designs stay below those lines at much higher request rates than the baselines. That's the throughput advantage playing out in practice.

---

## SLIDE: Splitwise Summary (30 sec)

So to recap Splitwise: they started with real production traces and found that these two phases are fundamentally different workloads that shouldn't share hardware. They built a three-pool architecture with optimized KV-cache transfer. And they showed you can use cheaper or power-capped GPUs for token generation without losing performance.

The big takeaway is that matching hardware to the actual computational needs of each phase saves serious money and power.

Alright, I'll hand it over to Ethan for DistServe.

---

## TOTAL: ~12 minutes


\newpage


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
