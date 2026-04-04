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

## SLIDE: Production Trace Insights (1.5 min)

So what makes Splitwise different from DistServe is that the authors had access to real production data. They pulled traces from two Azure LLM services at Microsoft, a coding assistant and a conversation service.

And they found some really interesting things. First, these workloads look totally different. The coding service has massive prompts, median 1500 tokens, but it only generates like 13 tokens of output. The conversation service is more balanced, about 1020 input tokens and 129 output tokens.

Second, and this was surprising to me, with mixed continuous batching, the machines spend 60 to 70 percent of their time running 20 tokens or fewer in the batch. That's the GPU sitting mostly idle during token generation.

Third, even for the coding workload where you have these huge prompts and tiny outputs, most of the wall-clock time is still spent on token generation. A prompt with 1500 tokens on BLOOM-176B takes about the same time as generating just 6 output tokens. Token generation dominates the end-to-end time.

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

## SLIDE: Splitwise Summary (30 sec)

So to recap Splitwise: they started with real production traces and found that these two phases are fundamentally different workloads that shouldn't share hardware. They built a three-pool architecture with optimized KV-cache transfer. And they showed you can use cheaper or power-capped GPUs for token generation without losing performance.

The big takeaway is that matching hardware to the actual computational needs of each phase saves serious money and power.

Alright, I'll hand it over to Ethan for DistServe.

---

## TOTAL: ~12 minutes
