# Knowledge Base: Phase Disaggregation for LLM Inference

## Papers Covered
- **Splitwise** (Patel et al., 2023) - UW + Microsoft - arXiv:2311.18677
- **DistServe** (Zhong et al., 2024) - Peking Univ + StepFun + UCSD - arXiv:2401.09670

## Wiki Articles
1. [LLM Inference Background](01_llm_inference_background.md) - Transformer inference, two phases, KV-cache
2. [The Problem: Phase Interference](02_problem_phase_interference.md) - Why colocating prefill/decode hurts
3. [Splitwise Deep Dive](03_splitwise_deep_dive.md) - Characterization, design, heterogeneous hardware
4. [DistServe Deep Dive](04_distserve_deep_dive.md) - Goodput optimization, placement algorithms
5. [Paper Comparison](05_comparison.md) - Side-by-side analysis, strengths, limitations
6. [Related Systems & Landscape](06_related_systems.md) - vLLM, Sarathi, DejaVu, TetriInfer, etc.
7. [Key Metrics & Concepts](07_metrics_concepts.md) - TTFT, TPOT, TBT, goodput, SLO attainment

## Presentation
- [Full Slide Deck](../presentation/slides.md)
- [Script: Berat - Splitwise](../presentation/script_berat_splitwise.md)
- [Script: Ethan - DistServe](../presentation/script_ethan_distserve.md)
- [Q&A Prep: Splitwise](../presentation/qa_prep_splitwise.md)
