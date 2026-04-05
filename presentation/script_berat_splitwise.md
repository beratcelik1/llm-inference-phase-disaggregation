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
