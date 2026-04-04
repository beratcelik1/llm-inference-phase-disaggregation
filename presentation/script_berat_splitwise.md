# Speaker Script — Berat Celik (Splitwise)
## Target Time: ~11 minutes (including shared intro/conclusion sections)

---

## SLIDE: Title Slide (~15 seconds)

"Hi everyone. I'm Berat, and together with Ethan, we'll be presenting on Phase Disaggregation for LLM Inference, covering two papers: Splitwise and DistServe. I'll be covering the background and Splitwise, then Ethan will take over for DistServe and the comparison."

---

## SLIDE: Presentation Outline (~15 seconds)

"Here's our roadmap. I'll start with the background on LLM inference, explain the core problem that motivates both papers, and then do a deep dive into Splitwise. Ethan will then cover DistServe and wrap up with a comparison."

---

## SLIDE: Background: How LLM Inference Works (~1.5 minutes)

"Let's start with how LLM inference actually works. When you send a prompt to a model like GPT-4 or LLaMA, the inference happens in two distinct phases.

The first phase is called **prefill** or prompt computation. Here, the model processes ALL of your input tokens in parallel in a single forward pass. This is just matrix multiplications through every transformer layer — attention, feed-forward network, layer norm — producing the first output token. Importantly, during this forward pass, the model generates what's called the **KV-cache** — the key and value tensors from the attention mechanism for every layer. This KV-cache stores the context and is essential for the second phase.

The second phase is **decoding** or token generation. Now the model generates tokens one at a time, autoregressively. Each step, it takes the previous token, attends to ALL previous tokens through the KV-cache, and produces the next token. This repeats until we hit an end-of-sequence token or the maximum length.

So for a simple query like 'Is tomato a fruit?', the prefill phase processes all 5 input tokens at once and outputs 'Yes', then decoding generates 'comma', 'it', 'is', 'a', 'fruit', 'period', one by one."

---

## SLIDE: The Two Phases Have Fundamentally Different Characteristics (~1.5 minutes)

"Now, here's what makes this really interesting for systems design. These two phases have **completely different computational characteristics**.

The prefill phase is **compute-bound**. You're doing large matrix multiplications — shapes like t-by-h times h-by-3h where t could be hundreds or thousands of tokens. The arithmetic intensity is extremely high — over 156 on an A100 for 512 tokens. The GPU is saturated, utilization is high, and power draw is near the thermal design power.

The decoding phase is the opposite — it's **memory-bandwidth-bound**. You're processing just one new token per request per step, so your matrix multiplications are tiny — batch-size-by-h times h-by-3h. The arithmetic intensity is much lower. GPU utilization is low without aggressive batching. And power draw is well below TDP.

Look at the key metrics column — prefill is measured by **TTFT**, time to first token, which is the user's perceived responsiveness. Decoding is measured by **TPOT** or **TBT**, the streaming speed of each subsequent token. Different phases, different bottlenecks, different hardware preferences, different metrics. This asymmetry is the fundamental insight behind both papers."

---

## SLIDE: Key Performance Metrics (~30 seconds)

"Quick overview of the metrics. TTFT is how long until the user sees the first token — critical for chatbots. TBT is the streaming speed — has to be at least as fast as human reading speed, about 250 words per minute. End-to-end latency is TTFT plus TPOT times the number of output tokens.

The most important concept here is **goodput** — throughput measured under SLO constraints. It's not about how many requests you can blast through; it's about how many you can serve while keeping 90% of users happy. This is the metric that matters for production LLM services."

---

## SLIDE: The Problem: Why Colocating Phases Fails (~1 minute)

"So what happens when we run both phases on the same GPU, as every existing system does?

The first problem is **prefill-decoding interference**. This is DistServe's Figure 2. When you add even ONE prefill job to a batch of decoding requests, decoding latency jumps from 5 milliseconds to 15 milliseconds — a 3x slowdown. With longer inputs like 1024 tokens, it's even worse. And it goes both ways — adding decode jobs to a prefill batch also increases TTFT.

Why? Because a prefill step takes much longer and has much higher compute requirements than a decode step. When they share the GPU, they compete for the same compute and memory bandwidth resources."

---

## SLIDE: The Problem (continued) (~45 seconds)

"Second, there's **resource and parallelism coupling**. Prefill works best with tensor parallelism to reduce execution time, but decoding works best with pipeline parallelism to scale throughput. When they share GPUs, you can only pick one strategy, and it'll be suboptimal for at least one phase.

Third, this forces **over-provisioning**. To meet both latency targets on a colocated system, you need way more GPUs than you should. For a 13B model on a single A100, colocation gives you only 1.6 requests per second. With disaggregation, you can get 3.3 requests per second per GPU — more than double. At $17 to $38 per hour per machine, this directly translates to money saved.

The solution both papers arrive at independently: **separate the phases onto different hardware entirely**."

---

## SLIDE: Splitwise: Production Trace Characterization (~1 minute)

"Now let's dive into Splitwise specifically. What makes Splitwise unique is that they start with **real production data** — traces from two Azure LLM inference services at Microsoft.

Three key findings from these traces. First, different services have wildly different workload distributions. A coding service has huge prompts — median 1500 tokens — but generates very few output tokens, median only 13. A conversation service is more balanced — median 1020 prompt tokens, 129 output tokens.

Second, and this is striking — with mixed continuous batching, token generation machines spend 60 to 70 percent of their time running 20 tokens or fewer. That's severe GPU underutilization.

Third, for most requests, the majority of end-to-end time is actually spent in token generation. Even for a coding request where you have 1500 prompt tokens and only 6 output tokens, on BLOOM-176B, the prompt phase takes about the same time as the token phase. Token generation dominates wall-clock time."

---

## SLIDE: Splitwise: Hardware Insights (~1.5 minutes)

"Here's where Splitwise really differentiates itself. They compare performance on A100 versus H100 GPUs across the two phases.

The H100 has 3.43x more compute than the A100. And for the prompt phase, you see that benefit — TTFT improves to 0.51x. The compute-heavy phase clearly benefits from more compute.

But look at token generation: TBT only improves to 0.70x. The token phase barely benefits from H100's massive compute advantage, because it's memory-bandwidth-bound, not compute-bound. And the H100 costs 2.16x more per hour.

This leads to Splitwise's central insight, Insight VII: **token generation can run on less compute-capable, cheaper hardware for better cost and power efficiency.** You don't need an H100 to generate tokens. An A100 does the job at better cost-efficiency.

And there's the power story too — the prompt phase draws power near TDP and scales with batch size. Token generation draws power well below TDP regardless of batch size. If you power-cap a token generation H100 to 70% power, there's virtually no latency impact. That's 30% power savings for free."

---

## SLIDE: Splitwise Design: Three Machine Pools (~1 minute)

"So here's the Splitwise architecture. They maintain three separate pools of machines.

The **Prompt Pool** has compute-optimized GPUs — H100s ideally — dedicated to processing prompts. High compute utilization, high power draw, doing what expensive GPUs are built for.

The **Token Pool** has cost-efficient GPUs — A100s or even power-capped H100s — dedicated to token generation. Memory-bandwidth utilization is high, but compute requirements are modest.

The **Mixed Pool** is the clever part — these are flexible machines that can handle either phase, used for overflow. When the prompt queue gets too long, a mixed machine picks up prompts. When there's a burst of tokens, it helps there. When idle, it goes back to its original pool.

A Cluster-Level Scheduler sits on top, routing requests, while each machine has its own Machine-Level Scheduler managing local batching and memory."

---

## SLIDE: Splitwise: Two-Level Scheduling (~30 seconds)

"The CLS uses Join-the-Shortest-Queue routing, and it simultaneously assigns both a prompt machine and a token machine for each request. This lets it overlap the KV-cache transfer with the prompt computation — so by the time the prompt finishes, the KV-cache is already largely on the token machine.

At the machine level, prompt machines use FCFS with a batch limit of 2048 tokens. Token machines use continuous batching until memory is full. Mixed machines prioritize prompts for TTFT but use age-based priority for tokens to prevent starvation."

---

## SLIDE: Splitwise: KV-Cache Transfer Optimization (~1 minute)

"The biggest engineering challenge in disaggregation is transferring the KV-cache between machines. After prefill computes the KV-cache, it needs to get to the token machine.

The naive approach is serialized transfer — wait for the entire prompt to finish, then ship the whole KV-cache. This adds up to 64% overhead to the second token's latency.

Splitwise's optimization is **per-layer transfer**. As each transformer layer finishes computing during prefill, they immediately send that layer's KV-cache using MSCCL++ zero-copy operations over InfiniBand. The transfer happens in parallel with the next layer's computation. The result is a constant 5 to 8 milliseconds of non-overlapped transfer time, regardless of prompt size. That's only 0.8% of end-to-end latency. For the user, the only visible impact is about 16% added to the second token latency, compared to 64% with naive transfer.

The key takeaway: **KV-cache transfer is NOT the bottleneck.** Both papers confirm this independently."

---

## SLIDE: Splitwise: Heterogeneous Cluster Designs (~45 seconds)

"Splitwise explores four cluster designs. Splitwise-AA uses A100s for both pools — cheapest option. Splitwise-HH uses H100s for both. Splitwise-HA, the heterogeneous design, uses H100s for prompts and A100s for tokens — getting the compute where it matters while saving cost on tokens. And Splitwise-HHcap uses H100s everywhere but power-caps the token machines to 70%.

They built an open-source event-driven simulator called SplitwiseSim to search this design space. You give it hardware profiles, SLO requirements, and request traces, and it finds the optimal mix of prompt and token machines."

---

## SLIDE: Splitwise: Evaluation Results (~45 seconds)

"The results are impressive across multiple optimization axes.

Under the same power and cost budget, Splitwise-AA delivers 2.15x more throughput than a baseline A100 cluster. Across different configurations, the paper's headline result is up to 2.35x throughput at the same cost and power. At the same cost, Splitwise-AA achieves 1.4x more throughput than a Baseline-H100 cluster — by using cheaper A100s more efficiently.

For power optimization, Splitwise-HHcap matches baseline throughput at 25% lower power. For cost optimization, Splitwise-AA matches baseline throughput at 25% lower cost.

The headline: you can either get much more throughput for the same money, or the same throughput for much less money. Either way, disaggregation with the right hardware wins."

---

## SLIDE: Splitwise: Robustness (~30 seconds)

"And the system is robust. Running a conversation workload on a cluster optimized for coding — wrong workload — only causes a 7% throughput drop. The mixed pool absorbs the mismatch. Running a different model — LLaMA-70B on a cluster designed for BLOOM-176B — all Splitwise designs still outperform the baselines."

---

## SLIDE: Splitwise: Summary (~30 seconds)

"To summarize Splitwise: they characterized real production workloads and found seven key insights about the asymmetry between inference phases. They designed a three-pool architecture that splits phases onto appropriate hardware. They optimized KV-cache transfer to under 1% overhead. And they explored heterogeneous cluster designs achieving 1.4x throughput at 20% lower cost, or 2.35x throughput at the same power.

The limitations are: it requires careful provisioning, less benefit with few GPUs, and basic fault tolerance. But the insight that token generation doesn't need expensive compute is powerful and has already influenced the industry.

Now I'll hand it over to Ethan for DistServe."

---

## SLIDE: Comparison & Both Papers Agree On (when Ethan reaches this section, Berat may co-present)

*[If Berat co-presents the comparison slides, add ~1 minute here]*

"Looking at these papers side by side — Splitwise says 'use the right hardware' while DistServe says 'use the right software configuration.' They're complementary, not competing. The ideal system would combine both: heterogeneous hardware with optimized per-phase parallelism.

Both papers independently confirm: colocation is broken, KV-cache transfer is cheap, and disaggregation delivers 2-7x improvements. This has already become the standard — SGLang, vLLM, and Mooncake have all adopted disaggregated architectures."

---

## TOTAL ESTIMATED TIME: ~11 minutes

### Pacing Notes:
- Background + Problem: ~5.5 minutes (sets up the "why" thoroughly)
- Splitwise deep dive: ~5.5 minutes (design, transfer, evaluation)
- Speak slowly during the "Two Phases" and "Problem" slides — these are the foundation
- Speed up slightly on evaluation numbers — highlight the key comparisons
- The comparison slide is optional for Berat depending on how Ethan structures his section
