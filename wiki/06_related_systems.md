# Related Systems & Landscape

## LLM Serving Frameworks

### vLLM (Kwon et al., 2023)
- Introduced **PagedAttention**: manages KV-cache like virtual memory pages
- Enables efficient memory management, reduces waste from fragmentation
- Uses continuous batching for throughput
- Colocates prefill and decoding → subject to interference
- Most widely used open-source LLM serving framework
- Has since integrated disaggregation support influenced by these papers

### TGI (Hugging Face Text Generation Inference)
- Production-grade inference server
- Supports continuous batching, tensor parallelism
- Optimized for Hugging Face model hub
- Colocated prefill/decode design

### NVIDIA Triton / TensorRT-LLM
- Enterprise-grade inference platform
- Supports in-flight batching (NVIDIA's term for continuous batching)
- Hardware-optimized kernels for NVIDIA GPUs
- Focus on single-machine optimization

### DeepSpeed-MII (Microsoft)
- Supports **chunked-prefill**: splits long prompts into chunks
- Piggybacks decode tokens with prefill chunks
- Mitigates interference but doesn't eliminate it
- Cannot serve OPT-175B with vocab_size=50272 and intra-op=8

## Disaggregation-Adjacent Work

### Sarathi (Agrawal et al., 2023)
- Proposes chunked-prefill with piggybacking
- Key idea: split long prefills, attach decode tokens to fill GPU
- **Limitations** identified by DistServe:
  - O(N^2) KV-cache reloading for N chunks
  - Chunk size dilemma (too small = underutilized, too large = no room for decode)
  - Fundamentally still colocated

### Orca (Yu et al., 2022)
- Introduced **continuous batching** for LLM serving
- Iteration-level scheduling (not request-level)
- Foundation for most modern serving systems
- Still colocates phases

### FastServe (Wu et al., 2023)
- Implements **iteration-level preemptive scheduling**
- Mitigates queuing delay from long jobs
- Complementary to disaggregation (DistServe notes this)
- Still colocated

### DejaVu (Strati et al., 2024)
- **KV-cache streaming** for fault-tolerant inference
- Streams KV-cache to remote storage during generation
- Enables fast recovery from failures
- Adopts similar disaggregation idea, confirms effectiveness

### TetriInfer (Hu et al., 2024)
- "Inference without interference" for mixed workloads
- Also disaggregates prefill and decode
- Further confirms the approach works

### AlpaServe (Li et al., 2023)
- Statistical multiplexing with model parallelism
- Improves GPU utilization by multiplexing multiple models
- Only targets non-autoregressive generation
- DistServe extends the goodput optimization idea to autoregressive LLMs

## Frameworks That Have Adopted Disaggregation

### SGLang
- Modern LLM serving framework
- Has adopted prefill-decode disaggregation
- Influenced by both Splitwise and DistServe

### Mooncake
- LLM serving system
- Implements disaggregated architecture
- Part of the trend these papers started

## Resource Disaggregation (Broader Context)

### LegoOS (Shan et al., 2018)
- Disaggregated OS: separate compute, memory, storage into resource pools
- Philosophical predecessor to LLM phase disaggregation
- Different scope but same principle: match resources to workload needs

### Dstmind (Jin et al., 2024)
- Efficient resource disaggregation for deep learning workloads
- Same group as DistServe (Peking University)
- Broader application of disaggregation beyond LLM inference

## Goodput-Optimized Systems

### Pollux (Qiao et al., 2021)
- Co-adaptive cluster scheduling for goodput-optimized deep learning
- Dynamically adjusts resources for training jobs
- DistServe brings goodput optimization to inference

### Sia (Subramanya et al., 2023)
- Heterogeneity-aware, goodput-optimized ML cluster scheduling
- Handles diverse hardware in training clusters
- Splitwise applies similar heterogeneity awareness to inference

## The Evolution of LLM Serving
```
2022: Orca → continuous batching (foundation)
      vLLM → PagedAttention (memory efficiency)
2023: Sarathi → chunked prefill (interference mitigation)
      FastServe → preemptive scheduling
      Splitwise → phase disaggregation + heterogeneous hardware (Nov 2023)
      AlpaServe → statistical multiplexing
2024: DistServe → goodput-optimized disaggregation (Jan 2024)
      TetriInfer, DejaVu → further confirmation
      SGLang, Mooncake → mainstream adoption
      PolyServe, DuetServe → next generation
```
