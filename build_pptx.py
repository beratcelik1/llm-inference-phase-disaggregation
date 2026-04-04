"""Build the presentation PPTX from structured slide data."""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Color palette
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)
ACCENT_TEAL = RGBColor(0x00, 0xD2, 0xD3)
ACCENT_ORANGE = RGBColor(0xFF, 0x9F, 0x43)
ACCENT_GREEN = RGBColor(0x10, 0xAC, 0x84)
ACCENT_RED = RGBColor(0xEE, 0x55, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xCC, 0xCC, 0xCC)
MED_GRAY = RGBColor(0x99, 0x99, 0x99)
DARK_TEXT = RGBColor(0x2D, 0x3A, 0x4A)
LIGHT_BG = RGBColor(0xF5, 0xF6, 0xFA)
SECTION_BG = RGBColor(0x0A, 0x3D, 0x62)


def add_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_shape_bg(slide, x, y, w, h, color, alpha=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_text_box(slide, left, top, width, height):
    return slide.shapes.add_textbox(left, top, width, height)


def set_text(
    tf,
    text,
    size=18,
    bold=False,
    color=WHITE,
    alignment=PP_ALIGN.LEFT,
    font_name="Calibri",
):
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    return p


def add_para(
    tf,
    text,
    size=18,
    bold=False,
    color=WHITE,
    alignment=PP_ALIGN.LEFT,
    space_before=Pt(6),
    font_name="Calibri",
):
    p = tf.add_paragraph()
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    p.space_before = space_before
    return p


def add_bullet(tf, text, size=16, color=WHITE, level=0, bold=False):
    p = tf.add_paragraph()
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = "Calibri"
    p.level = level
    p.space_before = Pt(4)
    return p


def make_table(slide, rows, cols, left, top, width, height):
    table_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    return table


def style_table_cell(cell, text, size=14, bold=False, color=WHITE, bg_color=None):
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = "Calibri"
    if bg_color:
        cell.fill.solid()
        cell.fill.fore_color.rgb = bg_color


# =============================================
# SLIDE 1: Title
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

# Accent line
add_shape_bg(slide, Inches(0), Inches(2.8), Inches(13.333), Pt(4), ACCENT_TEAL)

tb = add_text_box(slide, Inches(1), Inches(1.2), Inches(11.333), Inches(1.5))
set_text(
    tb.text_frame,
    "Phase Disaggregation for",
    size=44,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
)
add_para(
    tb.text_frame,
    "LLM Inference",
    size=44,
    bold=True,
    color=ACCENT_TEAL,
    alignment=PP_ALIGN.CENTER,
)

tb2 = add_text_box(slide, Inches(1), Inches(3.3), Inches(11.333), Inches(0.8))
set_text(
    tb2.text_frame,
    "Splitwise  |  DistServe",
    size=28,
    color=ACCENT_ORANGE,
    alignment=PP_ALIGN.CENTER,
)

tb3 = add_text_box(slide, Inches(1), Inches(4.5), Inches(11.333), Inches(1.5))
set_text(
    tb3.text_frame,
    "ECE 5545: Machine Learning Hardware & Systems",
    size=20,
    color=LIGHT_GRAY,
    alignment=PP_ALIGN.CENTER,
)
add_para(
    tb3.text_frame,
    "Berat Celik  &  Jiayang (Ethan) Chen",
    size=22,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
    space_before=Pt(12),
)
add_para(
    tb3.text_frame,
    "Spring 2026",
    size=18,
    color=MED_GRAY,
    alignment=PP_ALIGN.CENTER,
    space_before=Pt(8),
)


# =============================================
# SLIDE 2: Outline
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(tb.text_frame, "Presentation Outline", size=36, bold=True, color=WHITE)

# Part 1 box
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.6),
    Inches(5.6),
    Inches(4.8),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.1), Inches(1.8), Inches(5), Inches(4.4))
set_text(tb.text_frame, "Part 1 — Berat Celik", size=24, bold=True, color=ACCENT_TEAL)
add_bullet(
    tb.text_frame, "Background: LLM Inference & Two Phases", size=18, color=WHITE
)
add_bullet(tb.text_frame, "The Problem: Why Colocation Fails", size=18, color=WHITE)
add_bullet(tb.text_frame, "Splitwise: Production Trace Insights", size=18, color=WHITE)
add_bullet(tb.text_frame, "Splitwise: Architecture & Design", size=18, color=WHITE)
add_bullet(tb.text_frame, "KV-Cache Transfer Optimization", size=18, color=WHITE)
add_bullet(tb.text_frame, "Heterogeneous Cluster Designs", size=18, color=WHITE)
add_bullet(tb.text_frame, "Evaluation & Results", size=18, color=WHITE)

# Part 2 box
add_shape_bg(
    slide,
    Inches(6.9),
    Inches(1.6),
    Inches(5.6),
    Inches(4.8),
    RGBColor(0x3D, 0x0A, 0x2E),
)
tb = add_text_box(slide, Inches(7.2), Inches(1.8), Inches(5), Inches(4.4))
set_text(tb.text_frame, "Part 2 — Ethan Chen", size=24, bold=True, color=ACCENT_ORANGE)
add_bullet(tb.text_frame, "DistServe: Goodput Optimization", size=18, color=WHITE)
add_bullet(tb.text_frame, "Tradeoff Analysis", size=18, color=WHITE)
add_bullet(tb.text_frame, "Placement Algorithms", size=18, color=WHITE)
add_bullet(tb.text_frame, "Online Scheduling", size=18, color=WHITE)
add_bullet(tb.text_frame, "Evaluation & Results", size=18, color=WHITE)
add_bullet(tb.text_frame, "Comparison & Discussion", size=18, color=WHITE)
add_bullet(tb.text_frame, "Future Directions", size=18, color=WHITE)


# =============================================
# SLIDE 3: How LLM Inference Works
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "Background: How LLM Inference Works",
    size=36,
    bold=True,
    color=WHITE,
)

# Phase 1 box
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x15, 0x50, 0x70),
)
tb = add_text_box(slide, Inches(1.1), Inches(1.6), Inches(5), Inches(2.3))
set_text(
    tb.text_frame,
    "Phase 1: Prefill (Prompt Computation)",
    size=22,
    bold=True,
    color=ACCENT_TEAL,
)
add_bullet(tb.text_frame, "Process ALL input tokens in parallel", size=16, color=WHITE)
add_bullet(
    tb.text_frame, "Single forward pass → first output token", size=16, color=WHITE
)
add_bullet(
    tb.text_frame, "Generates KV-cache for all input tokens", size=16, color=WHITE
)
add_bullet(
    tb.text_frame,
    "Compute-bound: high arithmetic intensity",
    size=16,
    color=ACCENT_GREEN,
)

# Phase 2 box
add_shape_bg(
    slide,
    Inches(6.9),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x50, 0x15, 0x40),
)
tb = add_text_box(slide, Inches(7.2), Inches(1.6), Inches(5), Inches(2.3))
set_text(
    tb.text_frame,
    "Phase 2: Decoding (Token Generation)",
    size=22,
    bold=True,
    color=ACCENT_ORANGE,
)
add_bullet(tb.text_frame, "Generate tokens ONE at a time", size=16, color=WHITE)
add_bullet(
    tb.text_frame,
    "Each step attends to all prior tokens via KV-cache",
    size=16,
    color=WHITE,
)
add_bullet(tb.text_frame, "Repeat until end-of-sequence", size=16, color=WHITE)
add_bullet(
    tb.text_frame,
    "Memory-bandwidth-bound: low arithmetic intensity",
    size=16,
    color=ACCENT_RED,
)

# Example
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(4.3),
    Inches(11.7),
    Inches(1.2),
    RGBColor(0x2A, 0x2A, 0x45),
)
tb = add_text_box(slide, Inches(1.1), Inches(4.4), Inches(11.1), Inches(1.0))
set_text(
    tb.text_frame,
    'Example:  "Is tomato a fruit?"',
    size=18,
    bold=True,
    color=LIGHT_GRAY,
)
add_para(
    tb.text_frame,
    '→ [Prefill: 5 tokens in parallel] → "Yes" → [Decode] → "," → "it" → "is" → "." → [EOS]',
    size=16,
    color=WHITE,
    space_before=Pt(4),
)

# KV-cache note
tb = add_text_box(slide, Inches(0.8), Inches(5.7), Inches(11.7), Inches(1.2))
set_text(
    tb.text_frame,
    "KV-Cache: Key-Value tensors stored during prefill, read during every decode step.",
    size=16,
    bold=False,
    color=MED_GRAY,
)
add_para(
    tb.text_frame,
    "Size grows with sequence length — this is what must transfer when phases are on different machines.",
    size=16,
    color=MED_GRAY,
)


# =============================================
# SLIDE 4: Phase Characteristics Comparison
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "Two Phases, Fundamentally Different Characteristics",
    size=34,
    bold=True,
    color=WHITE,
)

table = make_table(slide, 8, 3, Inches(1.5), Inches(1.5), Inches(10.3), Inches(4.8))
headers = ["Property", "Prefill (Prompt)", "Decoding (Token Gen)"]
data = [
    ["Bottleneck", "Compute-bound", "Memory bandwidth-bound"],
    ["Tokens processed", "All input (parallel)", "1 per step (sequential)"],
    ["GPU utilization", "HIGH", "LOW (without batching)"],
    ["Power draw", "Near TDP (~700W H100)", "Well below TDP"],
    ["Key metric", "TTFT", "TPOT / TBT"],
    ["Batching benefit", "Limited (already saturated)", "Large (improves utilization)"],
    ["Ideal parallelism", "Tensor (intra-op)", "Pipeline (inter-op)"],
]

for i, h in enumerate(headers):
    style_table_cell(
        table.cell(0, i),
        h,
        size=16,
        bold=True,
        color=WHITE,
        bg_color=RGBColor(0x0A, 0x3D, 0x62),
    )

for r, row in enumerate(data):
    for c, val in enumerate(row):
        bg = RGBColor(0x22, 0x22, 0x3A) if r % 2 == 0 else RGBColor(0x1A, 0x1A, 0x2E)
        clr = ACCENT_TEAL if c == 1 else (ACCENT_ORANGE if c == 2 else LIGHT_GRAY)
        style_table_cell(table.cell(r + 1, c), val, size=14, color=clr, bg_color=bg)

tb = add_text_box(slide, Inches(1.5), Inches(6.5), Inches(10), Inches(0.6))
set_text(
    tb.text_frame,
    "This asymmetry is the key insight behind both papers.",
    size=20,
    bold=True,
    color=ACCENT_GREEN,
    alignment=PP_ALIGN.CENTER,
)


# =============================================
# SLIDE 5: Key Metrics
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(tb.text_frame, "Key Performance Metrics", size=36, bold=True, color=WHITE)

table = make_table(slide, 7, 3, Inches(1.2), Inches(1.5), Inches(10.9), Inches(4.2))
headers = ["Metric", "What It Measures", "Why It Matters"]
data = [
    ["TTFT", "Time to First Token (prefill latency)", "User-perceived responsiveness"],
    [
        "TBT / TPOT",
        "Time Between Tokens / Per Output Token",
        "Streaming reading experience",
    ],
    ["E2E Latency", "TTFT + TPOT \u00d7 output_length", "Total wait time"],
    ["Throughput", "Requests per second", "System capacity"],
    [
        "Goodput",
        "Throughput under SLO constraints",
        "Cost efficiency (DistServe's key metric)",
    ],
    [
        "SLO Attainment",
        "% requests meeting latency targets",
        "Service quality guarantee",
    ],
]
for i, h in enumerate(headers):
    style_table_cell(
        table.cell(0, i),
        h,
        size=15,
        bold=True,
        color=WHITE,
        bg_color=RGBColor(0x0A, 0x3D, 0x62),
    )
for r, row in enumerate(data):
    bg = RGBColor(0x22, 0x22, 0x3A) if r % 2 == 0 else RGBColor(0x1A, 0x1A, 0x2E)
    for c, val in enumerate(row):
        clr = ACCENT_TEAL if c == 0 else WHITE
        style_table_cell(
            table.cell(r + 1, c), val, size=14, color=clr, bg_color=bg, bold=(c == 0)
        )

# SLO example
add_shape_bg(
    slide,
    Inches(1.2),
    Inches(5.9),
    Inches(10.9),
    Inches(1.0),
    RGBColor(0x2A, 0x2A, 0x45),
)
tb = add_text_box(slide, Inches(1.5), Inches(6.0), Inches(10.3), Inches(0.8))
set_text(
    tb.text_frame,
    'SLO Example: "90% of chatbot requests must have TTFT < 0.25s AND TPOT < 0.1s"',
    size=17,
    bold=False,
    color=ACCENT_ORANGE,
    alignment=PP_ALIGN.CENTER,
)


# =============================================
# SLIDE 6: The Problem
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "The Problem: Why Colocating Phases Fails",
    size=34,
    bold=True,
    color=ACCENT_RED,
)

# Problem 1
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(3.7),
    Inches(4.2),
    RGBColor(0x50, 0x15, 0x15),
)
tb = add_text_box(slide, Inches(1.0), Inches(1.6), Inches(3.3), Inches(4.0))
set_text(
    tb.text_frame,
    "1. Prefill-Decode Interference",
    size=18,
    bold=True,
    color=ACCENT_RED,
)
add_bullet(tb.text_frame, "Adding 1 prefill to decode batch:", size=14, color=WHITE)
add_bullet(
    tb.text_frame, "Up to 3x slower (input=128)", size=14, color=ACCENT_ORANGE, level=1
)
add_bullet(
    tb.text_frame, "Up to 5x slower (input=1024)", size=14, color=ACCENT_ORANGE, level=1
)
add_bullet(tb.text_frame, "Interference in both directions", size=14, color=WHITE)
add_para(
    tb.text_frame, "[DistServe Figure 2]", size=12, color=MED_GRAY, space_before=Pt(8)
)

# Problem 2
add_shape_bg(
    slide,
    Inches(4.8),
    Inches(1.5),
    Inches(3.7),
    Inches(4.2),
    RGBColor(0x50, 0x35, 0x05),
)
tb = add_text_box(slide, Inches(5.0), Inches(1.6), Inches(3.3), Inches(4.0))
set_text(
    tb.text_frame,
    "2. Resource & Parallelism Coupling",
    size=18,
    bold=True,
    color=ACCENT_ORANGE,
)
add_bullet(tb.text_frame, "Prefill wants tensor parallelism", size=14, color=WHITE)
add_bullet(tb.text_frame, "Decode wants pipeline parallelism", size=14, color=WHITE)
add_bullet(tb.text_frame, "Colocated = must pick ONE", size=14, color=WHITE)
add_bullet(
    tb.text_frame, "Suboptimal for at least one phase", size=14, color=ACCENT_ORANGE
)

# Problem 3
add_shape_bg(
    slide,
    Inches(8.8),
    Inches(1.5),
    Inches(3.7),
    Inches(4.2),
    RGBColor(0x15, 0x15, 0x50),
)
tb = add_text_box(slide, Inches(9.0), Inches(1.6), Inches(3.3), Inches(4.0))
set_text(
    tb.text_frame,
    "3. Over-Provisioning",
    size=18,
    bold=True,
    color=RGBColor(0x74, 0xB9, 0xFF),
)
add_bullet(tb.text_frame, "Must over-provision to meet both SLOs", size=14, color=WHITE)
add_bullet(tb.text_frame, "Colocated: ~1.6 req/s (OPT-13B)", size=14, color=WHITE)
add_bullet(tb.text_frame, "Disaggregated: 3.3 req/s", size=14, color=ACCENT_GREEN)
add_bullet(tb.text_frame, "= 2.1x improvement", size=14, color=ACCENT_GREEN, level=1)

# Solution bar
add_shape_bg(slide, Inches(0.8), Inches(6.0), Inches(11.7), Inches(1.0), ACCENT_GREEN)
tb = add_text_box(slide, Inches(1.0), Inches(6.1), Inches(11.3), Inches(0.8))
set_text(
    tb.text_frame,
    "The Solution: Separate the phases onto different hardware entirely.",
    size=22,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
)


# =============================================
# SLIDE 7: SECTION DIVIDER — SPLITWISE
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, SECTION_BG)
add_shape_bg(slide, Inches(0), Inches(3.2), Inches(13.333), Pt(4), ACCENT_TEAL)

tb = add_text_box(slide, Inches(1), Inches(2.0), Inches(11.333), Inches(1.5))
set_text(
    tb.text_frame,
    "Splitwise",
    size=52,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
)

tb2 = add_text_box(slide, Inches(1), Inches(3.7), Inches(11.333), Inches(1.5))
set_text(
    tb2.text_frame,
    "Efficient Generative LLM Inference Using Phase Splitting",
    size=24,
    color=ACCENT_TEAL,
    alignment=PP_ALIGN.CENTER,
)
add_para(
    tb2.text_frame,
    "Patel et al., ISCA 2024  |  University of Washington + Microsoft",
    size=18,
    color=LIGHT_GRAY,
    alignment=PP_ALIGN.CENTER,
    space_before=Pt(12),
)


# =============================================
# SLIDE 8: Splitwise Production Traces
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "Splitwise: Production Trace Characterization",
    size=34,
    bold=True,
    color=WHITE,
)

tb = add_text_box(slide, Inches(0.8), Inches(1.3), Inches(11.7), Inches(0.6))
set_text(
    tb.text_frame,
    "Real Azure production traces from two LLM inference services (Nov 2023)",
    size=18,
    color=ACCENT_TEAL,
)

# Insight boxes
insights = [
    (
        "Insight I",
        "Workloads vary widely",
        "Coding: 1500 prompt, 13 output tokens\nConversation: 1020 prompt, 129 output",
    ),
    (
        "Insight II",
        "Token gen machines underutilized",
        "60-70% of time running \u226420 active tokens\nGPU resources wasted",
    ),
    (
        "Insight III",
        "Most E2E time in token gen",
        "Even coding (1500 prompt, 6 output):\nprompt \u2248 token time on BLOOM-176B",
    ),
]
for i, (title, subtitle, body) in enumerate(insights):
    x = Inches(0.8 + i * 4.1)
    add_shape_bg(
        slide, x, Inches(2.2), Inches(3.8), Inches(3.5), RGBColor(0x22, 0x22, 0x3A)
    )
    tb = add_text_box(slide, x + Inches(0.2), Inches(2.3), Inches(3.4), Inches(3.3))
    set_text(tb.text_frame, title, size=20, bold=True, color=ACCENT_TEAL)
    add_para(
        tb.text_frame, subtitle, size=16, bold=True, color=WHITE, space_before=Pt(8)
    )
    for line in body.split("\n"):
        add_para(tb.text_frame, line, size=14, color=LIGHT_GRAY, space_before=Pt(4))

tb = add_text_box(slide, Inches(0.8), Inches(6.0), Inches(11.7), Inches(1.0))
set_text(
    tb.text_frame,
    "[Reference: Splitwise Figures 3, 4 — Token distributions and batch utilization]",
    size=14,
    color=MED_GRAY,
)


# =============================================
# SLIDE 9: Hardware Insights
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame, "Splitwise: The Hardware Insight", size=34, bold=True, color=WHITE
)

# A100 vs H100 table
table = make_table(slide, 5, 4, Inches(1.5), Inches(1.4), Inches(7), Inches(3.0))
h = ["Metric", "A100", "H100", "Ratio"]
d = [
    ["TTFT (Coding)", "185 ms", "95 ms", "0.51\u00d7"],
    ["TBT (Coding)", "52 ms", "31 ms", "0.70\u00d7"],
    ["Cost per request", "$0.42", "$0.52", "1.24\u00d7"],
    ["Energy", "1.37 Whr", "1.37 Whr", "1\u00d7"],
]
for i, v in enumerate(h):
    style_table_cell(
        table.cell(0, i),
        v,
        size=15,
        bold=True,
        color=WHITE,
        bg_color=RGBColor(0x0A, 0x3D, 0x62),
    )
for r, row in enumerate(d):
    bg = RGBColor(0x22, 0x22, 0x3A) if r % 2 == 0 else RGBColor(0x1A, 0x1A, 0x2E)
    for c, v in enumerate(row):
        clr = (
            ACCENT_GREEN
            if (r == 1 and c == 3)
            else (ACCENT_RED if (r == 2 and c == 3) else WHITE)
        )
        style_table_cell(table.cell(r + 1, c), v, size=14, color=clr, bg_color=bg)

# Key insight box
add_shape_bg(
    slide,
    Inches(1.5),
    Inches(4.6),
    Inches(10.3),
    Inches(1.5),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.8), Inches(4.7), Inches(9.7), Inches(1.3))
set_text(
    tb.text_frame,
    "Insight VII — The Key Insight:",
    size=20,
    bold=True,
    color=ACCENT_TEAL,
)
add_para(
    tb.text_frame,
    "Token generation barely benefits from H100's 3.43\u00d7 compute advantage.",
    size=18,
    color=WHITE,
    space_before=Pt(8),
)
add_para(
    tb.text_frame,
    "A100 is more cost-efficient for token generation!",
    size=18,
    bold=True,
    color=ACCENT_ORANGE,
    space_before=Pt(4),
)

tb = add_text_box(slide, Inches(0.8), Inches(6.3), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "H100: 3.43\u00d7 more compute, but memory bandwidth only 1.64\u00d7 and capacity 1.0\u00d7 (both 80GB)",
    size=16,
    color=MED_GRAY,
)
add_para(
    tb.text_frame,
    "[Reference: Splitwise Table I & Table IV — A100 vs H100 specs and performance on Llama-70B]",
    size=14,
    color=MED_GRAY,
)


# =============================================
# SLIDE 10: Splitwise Architecture
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame, "Splitwise: Three Machine Pools", size=34, bold=True, color=WHITE
)

# CLS box
add_shape_bg(
    slide, Inches(4.2), Inches(1.3), Inches(5), Inches(0.8), RGBColor(0x0A, 0x3D, 0x62)
)
tb = add_text_box(slide, Inches(4.4), Inches(1.35), Inches(4.6), Inches(0.7))
set_text(
    tb.text_frame,
    "Cluster-Level Scheduler (CLS)",
    size=18,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
)

# Prompt Pool
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(2.6),
    Inches(3.8),
    Inches(2.5),
    RGBColor(0x15, 0x50, 0x70),
)
tb = add_text_box(slide, Inches(1.0), Inches(2.7), Inches(3.4), Inches(2.3))
set_text(tb.text_frame, "Prompt Pool", size=22, bold=True, color=ACCENT_TEAL)
add_bullet(tb.text_frame, "Compute-optimized GPUs (H100s)", size=14, color=WHITE)
add_bullet(tb.text_frame, "Dedicated to prefill", size=14, color=WHITE)
add_bullet(tb.text_frame, "FCFS, batch \u2264 2048 tokens", size=14, color=LIGHT_GRAY)
add_bullet(tb.text_frame, "High compute utilization", size=14, color=ACCENT_GREEN)

# Arrow (KV Cache)
add_shape_bg(
    slide,
    Inches(4.8),
    Inches(3.2),
    Inches(3.7),
    Inches(0.6),
    RGBColor(0x2A, 0x2A, 0x45),
)
tb = add_text_box(slide, Inches(4.9), Inches(3.25), Inches(3.5), Inches(0.5))
set_text(
    tb.text_frame,
    "KV-Cache Transfer  \u2192",
    size=16,
    bold=True,
    color=ACCENT_ORANGE,
    alignment=PP_ALIGN.CENTER,
)

# Token Pool
add_shape_bg(
    slide,
    Inches(8.8),
    Inches(2.6),
    Inches(3.8),
    Inches(2.5),
    RGBColor(0x50, 0x15, 0x40),
)
tb = add_text_box(slide, Inches(9.0), Inches(2.7), Inches(3.4), Inches(2.3))
set_text(tb.text_frame, "Token Pool", size=22, bold=True, color=ACCENT_ORANGE)
add_bullet(tb.text_frame, "Cost-efficient GPUs (A100s)", size=14, color=WHITE)
add_bullet(tb.text_frame, "Dedicated to token generation", size=14, color=WHITE)
add_bullet(tb.text_frame, "Continuous batching", size=14, color=LIGHT_GRAY)
add_bullet(tb.text_frame, "Memory-bandwidth focus", size=14, color=ACCENT_GREEN)

# Mixed Pool
add_shape_bg(
    slide,
    Inches(2.8),
    Inches(5.5),
    Inches(7.7),
    Inches(1.3),
    RGBColor(0x2A, 0x35, 0x15),
)
tb = add_text_box(slide, Inches(3.0), Inches(5.55), Inches(7.3), Inches(1.2))
set_text(tb.text_frame, "Mixed Pool", size=20, bold=True, color=ACCENT_GREEN)
add_para(
    tb.text_frame,
    "Flexible machines handling overflow from either pool  |  Dynamically repurposed  |  Mixed continuous batching",
    size=14,
    color=WHITE,
    space_before=Pt(4),
)


# =============================================
# SLIDE 11: KV-Cache Transfer
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "Splitwise: KV-Cache Transfer Optimization",
    size=34,
    bold=True,
    color=WHITE,
)

# Naive vs Optimized
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(5.6),
    Inches(3.0),
    RGBColor(0x50, 0x15, 0x15),
)
tb = add_text_box(slide, Inches(1.0), Inches(1.6), Inches(5.2), Inches(2.8))
set_text(
    tb.text_frame, "Naive: Serialized Transfer", size=20, bold=True, color=ACCENT_RED
)
add_bullet(tb.text_frame, "Wait for full prefill to complete", size=15, color=WHITE)
add_bullet(tb.text_frame, "Transfer entire KV-cache at once", size=15, color=WHITE)
add_bullet(tb.text_frame, "Then start decoding", size=15, color=WHITE)
add_bullet(
    tb.text_frame, "64% overhead to 2nd token latency", size=15, color=ACCENT_RED
)

add_shape_bg(
    slide,
    Inches(6.9),
    Inches(1.5),
    Inches(5.6),
    Inches(3.0),
    RGBColor(0x0A, 0x3D, 0x20),
)
tb = add_text_box(slide, Inches(7.1), Inches(1.6), Inches(5.2), Inches(2.8))
set_text(
    tb.text_frame,
    "Optimized: Per-Layer Transfer",
    size=20,
    bold=True,
    color=ACCENT_GREEN,
)
add_bullet(
    tb.text_frame, "Send each layer's KV-cache immediately", size=15, color=WHITE
)
add_bullet(
    tb.text_frame, "Transfer overlaps with next layer computation", size=15, color=WHITE
)
add_bullet(tb.text_frame, "MSCCL++ zero-copy over InfiniBand", size=15, color=WHITE)
add_bullet(
    tb.text_frame, "Only 16.5% overhead to 2nd token", size=15, color=ACCENT_GREEN
)

# Result box
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(4.8),
    Inches(11.7),
    Inches(1.8),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.0), Inches(4.9), Inches(11.3), Inches(1.6))
set_text(tb.text_frame, "Result", size=22, bold=True, color=ACCENT_TEAL)
add_bullet(
    tb.text_frame,
    "Per-layer: only 0.8% of E2E latency (constant ~5-8ms regardless of prompt size)",
    size=16,
    color=WHITE,
)
add_bullet(
    tb.text_frame,
    "Serialized: up to 3% of E2E for large prompts",
    size=16,
    color=LIGHT_GRAY,
)
add_para(
    tb.text_frame,
    "KV-cache transfer is NOT the bottleneck on modern GPU clusters.",
    size=18,
    bold=True,
    color=ACCENT_GREEN,
    space_before=Pt(12),
)


# =============================================
# SLIDE 12: Cluster Designs
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "Splitwise: Heterogeneous Cluster Designs",
    size=34,
    bold=True,
    color=WHITE,
)

table = make_table(slide, 5, 4, Inches(1.5), Inches(1.5), Inches(10.3), Inches(2.8))
h = ["Design", "Prompt Machine", "Token Machine", "Key Tradeoff"]
d = [
    ["Splitwise-AA", "DGX-A100", "DGX-A100", "Lowest cost, older GPUs"],
    ["Splitwise-HH", "DGX-H100", "DGX-H100", "Best raw performance"],
    ["Splitwise-HA", "DGX-H100", "DGX-A100", "Best of both worlds"],
    ["Splitwise-HHcap", "DGX-H100", "H100 @ 70% power", "Power optimization"],
]
for i, v in enumerate(h):
    style_table_cell(
        table.cell(0, i),
        v,
        size=15,
        bold=True,
        color=WHITE,
        bg_color=RGBColor(0x0A, 0x3D, 0x62),
    )
for r, row in enumerate(d):
    bg = RGBColor(0x22, 0x22, 0x3A) if r % 2 == 0 else RGBColor(0x1A, 0x1A, 0x2E)
    for c, v in enumerate(row):
        clr = ACCENT_TEAL if c == 0 else WHITE
        style_table_cell(
            table.cell(r + 1, c), v, size=14, color=clr, bg_color=bg, bold=(c == 0)
        )


# =============================================
# SLIDE 13: Splitwise Results
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame, "Splitwise: Evaluation Results", size=34, bold=True, color=WHITE
)

results = [
    (
        "Iso-Power Throughput",
        "Same power budget",
        "Splitwise-AA: 2.15\u00d7 more throughput\nvs Baseline-A100",
        ACCENT_TEAL,
    ),
    (
        "Iso-Cost Throughput",
        "Same cost",
        "1.4\u00d7 more throughput at\n20% lower cost vs Baseline-H100",
        ACCENT_ORANGE,
    ),
    (
        "Iso-Throughput Power",
        "Same throughput target",
        "Splitwise-HHcap: 25% lower power\nvs Baseline-H100",
        ACCENT_GREEN,
    ),
    (
        "Iso-Throughput Cost",
        "Same throughput target",
        "Splitwise-AA: 25% lower cost\nvs Baseline-H100",
        RGBColor(0x74, 0xB9, 0xFF),
    ),
]
for i, (title, sub, body, clr) in enumerate(results):
    x = Inches(0.6 + (i % 2) * 6.3)
    y = Inches(1.5 + (i // 2) * 2.6)
    add_shape_bg(slide, x, y, Inches(6.0), Inches(2.2), RGBColor(0x22, 0x22, 0x3A))
    tb = add_text_box(slide, x + Inches(0.2), y + Inches(0.1), Inches(5.6), Inches(2.0))
    set_text(tb.text_frame, title, size=18, bold=True, color=clr)
    add_para(tb.text_frame, sub, size=13, color=MED_GRAY, space_before=Pt(2))
    for line in body.split("\n"):
        add_para(tb.text_frame, line, size=15, color=WHITE, space_before=Pt(4))

add_shape_bg(
    slide,
    Inches(0.6),
    Inches(6.2),
    Inches(12.1),
    Inches(0.8),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(0.8), Inches(6.25), Inches(11.7), Inches(0.7))
set_text(
    tb.text_frame,
    "Overall: up to 1.4\u00d7 throughput at 20% lower cost, or 2.35\u00d7 throughput at same cost & power",
    size=18,
    bold=True,
    color=ACCENT_GREEN,
    alignment=PP_ALIGN.CENTER,
)


# =============================================
# SLIDE 14: Splitwise Summary
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(tb.text_frame, "Splitwise: Summary", size=36, bold=True, color=WHITE)

tb = add_text_box(slide, Inches(0.8), Inches(1.5), Inches(11.7), Inches(4.5))
set_text(tb.text_frame, "", size=16, color=WHITE)
items = [
    (
        "1.",
        "Characterized real production LLM workloads \u2192 7 key insights about phase asymmetry",
    ),
    (
        "2.",
        "Designed phase splitting architecture with three machine pools (prompt, token, mixed)",
    ),
    (
        "3.",
        "Optimized KV-cache transfer with per-layer overlapping (<1% of E2E overhead)",
    ),
    ("4.", "Explored heterogeneous cluster designs (AA, HH, HA, HHcap)"),
    (
        "5.",
        "Achieved: 1.4\u00d7 throughput at 20% lower cost, OR 2.35\u00d7 throughput at same power",
    ),
]
for num, text in items:
    add_para(tb.text_frame, f"{num}  {text}", size=18, color=WHITE, space_before=Pt(16))

tb = add_text_box(slide, Inches(0.8), Inches(5.5), Inches(11.7), Inches(1.5))
set_text(tb.text_frame, "Limitations:", size=18, bold=True, color=ACCENT_ORANGE)
add_bullet(
    tb.text_frame,
    "Requires careful cluster provisioning (but provides simulator)",
    size=15,
    color=LIGHT_GRAY,
)
add_bullet(
    tb.text_frame,
    "Less beneficial with very few GPUs  |  Basic fault tolerance",
    size=15,
    color=LIGHT_GRAY,
)


# =============================================
# SLIDE 15: SECTION DIVIDER — DISTSERVE
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, RGBColor(0x3D, 0x0A, 0x2E))
add_shape_bg(slide, Inches(0), Inches(3.2), Inches(13.333), Pt(4), ACCENT_ORANGE)

tb = add_text_box(slide, Inches(1), Inches(2.0), Inches(11.333), Inches(1.5))
set_text(
    tb.text_frame,
    "DistServe",
    size=52,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
)

tb2 = add_text_box(slide, Inches(1), Inches(3.7), Inches(11.333), Inches(1.5))
set_text(
    tb2.text_frame,
    "Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving",
    size=22,
    color=ACCENT_ORANGE,
    alignment=PP_ALIGN.CENTER,
)
add_para(
    tb2.text_frame,
    "Zhong et al., OSDI 2024  |  Peking University + StepFun + UC San Diego",
    size=18,
    color=LIGHT_GRAY,
    alignment=PP_ALIGN.CENTER,
    space_before=Pt(12),
)


# =============================================
# SLIDE 16: DistServe Motivation
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "DistServe: Goodput as the Optimization Target",
    size=34,
    bold=True,
    color=WHITE,
)

add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(11.7),
    Inches(1.5),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.0), Inches(1.6), Inches(11.3), Inches(1.3))
set_text(
    tb.text_frame,
    "Per-GPU Goodput = Maximum request rate while meeting SLO attainment target",
    size=20,
    bold=True,
    color=ACCENT_ORANGE,
    alignment=PP_ALIGN.CENTER,
)
add_para(
    tb.text_frame,
    "Higher goodput = lower cost per query = what production LLM services actually optimize for",
    size=16,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
    space_before=Pt(8),
)

tb = add_text_box(slide, Inches(0.8), Inches(3.3), Inches(11.7), Inches(0.6))
set_text(tb.text_frame, "DistServe's Approach:", size=22, bold=True, color=ACCENT_TEAL)

tb = add_text_box(slide, Inches(0.8), Inches(4.0), Inches(11.7), Inches(2.5))
set_text(tb.text_frame, "", size=16, color=WHITE)
add_bullet(
    tb.text_frame,
    "Disaggregate prefill and decoding onto separate GPU instances",
    size=18,
    color=WHITE,
)
add_bullet(
    tb.text_frame,
    "Co-optimize resource allocation and parallelism for each phase independently",
    size=18,
    color=WHITE,
)
add_bullet(
    tb.text_frame,
    "Automatically find the best placement on the physical cluster",
    size=18,
    color=WHITE,
)
add_bullet(
    tb.text_frame,
    "Evaluate with SLO attainment as the primary metric",
    size=18,
    color=WHITE,
)

tb = add_text_box(slide, Inches(0.8), Inches(6.2), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "[DistServe Figure 1: disaggregated prefill-only and decode-only outperform colocated systems]",
    size=14,
    color=MED_GRAY,
)


# =============================================
# SLIDE 17: DistServe Tradeoff Analysis
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "DistServe: Tradeoff Analysis (Post-Disaggregation)",
    size=34,
    bold=True,
    color=WHITE,
)

# Prefill analysis
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(5.6),
    Inches(4.0),
    RGBColor(0x15, 0x50, 0x70),
)
tb = add_text_box(slide, Inches(1.0), Inches(1.6), Inches(5.2), Inches(3.8))
set_text(tb.text_frame, "Prefill Instance", size=22, bold=True, color=ACCENT_TEAL)
add_bullet(tb.text_frame, "Modeled as M/D/1 queue", size=15, color=WHITE)
add_bullet(tb.text_frame, "Avg TTFT = exec time + queuing delay", size=15, color=WHITE)
add_bullet(
    tb.text_frame,
    "Low arrival rates \u2192 intra-op parallelism",
    size=15,
    color=ACCENT_GREEN,
)
add_para(
    tb.text_frame,
    "  (reduces execution time)",
    size=13,
    color=LIGHT_GRAY,
    space_before=Pt(2),
)
add_bullet(
    tb.text_frame,
    "High arrival rates \u2192 inter-op parallelism",
    size=15,
    color=ACCENT_ORANGE,
)
add_para(
    tb.text_frame,
    "  (reduces queuing delay)",
    size=13,
    color=LIGHT_GRAY,
    space_before=Pt(2),
)
add_para(
    tb.text_frame,
    "[Figure 4a: crossover at different rates]",
    size=12,
    color=MED_GRAY,
    space_before=Pt(12),
)

# Decode analysis
add_shape_bg(
    slide,
    Inches(6.9),
    Inches(1.5),
    Inches(5.6),
    Inches(4.0),
    RGBColor(0x50, 0x15, 0x40),
)
tb = add_text_box(slide, Inches(7.1), Inches(1.6), Inches(5.2), Inches(3.8))
set_text(tb.text_frame, "Decoding Instance", size=22, bold=True, color=ACCENT_ORANGE)
add_bullet(tb.text_frame, "Memory-bandwidth-bound (single job)", size=15, color=WHITE)
add_bullet(tb.text_frame, "Batching is CRITICAL for utilization", size=15, color=WHITE)
add_bullet(
    tb.text_frame,
    "Disaggregation \u2192 naturally larger batches",
    size=15,
    color=ACCENT_GREEN,
)
add_para(
    tb.text_frame,
    "  (multiple prefill instances feed one decode)",
    size=13,
    color=LIGHT_GRAY,
    space_before=Pt(2),
)
add_bullet(
    tb.text_frame, "Large batches \u2192 approaches compute-bound", size=15, color=WHITE
)
add_bullet(
    tb.text_frame, "Then parallelism optimization matters", size=15, color=ACCENT_ORANGE
)
add_para(
    tb.text_frame,
    "[Figure 5: latency/throughput vs parallelism]",
    size=12,
    color=MED_GRAY,
    space_before=Pt(12),
)

# Key insight
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(5.8),
    Inches(11.7),
    Inches(1.0),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.0), Inches(5.9), Inches(11.3), Inches(0.8))
set_text(
    tb.text_frame,
    "Post-disaggregation: independent knobs per phase. Impossible when sharing GPUs.",
    size=20,
    bold=True,
    color=ACCENT_GREEN,
    alignment=PP_ALIGN.CENTER,
)


# =============================================
# SLIDE 18: DistServe Placement Algorithms
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame, "DistServe: Placement Algorithms", size=34, bold=True, color=WHITE
)

tb = add_text_box(slide, Inches(0.8), Inches(1.3), Inches(11.7), Inches(0.6))
set_text(
    tb.text_frame,
    "Given: model, workload, SLOs, cluster  \u2192  Find: parallelism + instance counts + placement  \u2192  Goal: maximize per-GPU goodput",
    size=16,
    color=ACCENT_TEAL,
)

# Alg 1
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(2.2),
    Inches(5.6),
    Inches(3.0),
    RGBColor(0x22, 0x22, 0x3A),
)
tb = add_text_box(slide, Inches(1.0), Inches(2.3), Inches(5.2), Inches(2.8))
set_text(
    tb.text_frame,
    "Algorithm 1: High Node-Affinity",
    size=18,
    bold=True,
    color=ACCENT_TEAL,
)
add_para(
    tb.text_frame, "(InfiniBand clusters)", size=14, color=MED_GRAY, space_before=Pt(2)
)
add_bullet(tb.text_frame, "Enumerate all parallelism configs", size=14, color=WHITE)
add_bullet(tb.text_frame, "Simulate each config's goodput", size=14, color=WHITE)
add_bullet(
    tb.text_frame, "Pick best for each phase independently", size=14, color=WHITE
)
add_bullet(tb.text_frame, "Calculate replication for target rate", size=14, color=WHITE)
add_bullet(
    tb.text_frame, "Complexity: O(NM\u00b2), < 1.3 minutes", size=14, color=ACCENT_GREEN
)

# Alg 2
add_shape_bg(
    slide,
    Inches(6.9),
    Inches(2.2),
    Inches(5.6),
    Inches(3.0),
    RGBColor(0x22, 0x22, 0x3A),
)
tb = add_text_box(slide, Inches(7.1), Inches(2.3), Inches(5.2), Inches(2.8))
set_text(
    tb.text_frame,
    "Algorithm 2: Low Node-Affinity",
    size=18,
    bold=True,
    color=ACCENT_ORANGE,
)
add_para(
    tb.text_frame,
    "(Limited cross-node bandwidth)",
    size=14,
    color=MED_GRAY,
    space_before=Pt(2),
)
add_bullet(
    tb.text_frame, "Constraint: prefill + decode same node", size=14, color=WHITE
)
add_bullet(tb.text_frame, "Use NVLINK for fast KV transfer", size=14, color=WHITE)
add_bullet(tb.text_frame, "Co-optimize within node GPU budget", size=14, color=WHITE)
add_bullet(tb.text_frame, "Group layers into co-located segments", size=14, color=WHITE)

# Simulator
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(5.5),
    Inches(11.7),
    Inches(1.3),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.0), Inches(5.6), Inches(11.3), Inches(1.1))
set_text(
    tb.text_frame,
    "Event-Driven Simulator: < 2% error vs real system",
    size=18,
    bold=True,
    color=ACCENT_GREEN,
)
add_para(
    tb.text_frame,
    "Models FLOPs + memory accesses per phase  |  Fits distributions from historical traces  |  Enables design space exploration without hardware",
    size=14,
    color=WHITE,
    space_before=Pt(4),
)


# =============================================
# SLIDE 19: DistServe Results
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame, "DistServe: Evaluation Results", size=34, bold=True, color=WHITE
)

tb = add_text_box(slide, Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.5))
set_text(
    tb.text_frame,
    "Setup: 4 nodes \u00d7 8 GPUs = 32 NVIDIA A100-80GB  |  Baselines: vLLM, DeepSpeed-MII",
    size=16,
    color=MED_GRAY,
)

table = make_table(slide, 4, 4, Inches(1.2), Inches(2.0), Inches(10.9), Inches(2.8))
h = ["Workload", "vs vLLM (Rate)", "vs vLLM (SLO)", "vs DeepSpeed-MII (Rate)"]
d = [
    [
        "Chatbot (ShareGPT)",
        "2.0\u00d7 \u2013 4.6\u00d7 higher",
        "1.8\u00d7 \u2013 3.2\u00d7 tighter",
        "1.6\u00d7 \u2013 7.4\u00d7 higher",
    ],
    [
        "Code Completion (HumanEval)",
        "5.7\u00d7 higher",
        "1.4\u00d7 tighter",
        "1.6\u00d7 higher",
    ],
    [
        "Summarization (LongBench)",
        "4.3\u00d7 higher",
        "12.6\u00d7 tighter",
        "1.8\u00d7 higher",
    ],
]
for i, v in enumerate(h):
    style_table_cell(
        table.cell(0, i),
        v,
        size=14,
        bold=True,
        color=WHITE,
        bg_color=RGBColor(0x3D, 0x0A, 0x2E),
    )
for r, row in enumerate(d):
    bg = RGBColor(0x22, 0x22, 0x3A) if r % 2 == 0 else RGBColor(0x1A, 0x1A, 0x2E)
    for c, v in enumerate(row):
        clr = (
            ACCENT_ORANGE
            if c == 0
            else (ACCENT_GREEN if "12.6" in v or "5.7" in v or "7.4" in v else WHITE)
        )
        style_table_cell(
            table.cell(r + 1, c),
            v,
            size=14,
            color=clr,
            bg_color=bg,
            bold=("12.6" in v or "7.4" in v),
        )

# Parallelism chosen
tb = add_text_box(slide, Inches(0.8), Inches(5.0), Inches(11.7), Inches(0.5))
set_text(
    tb.text_frame,
    "Parallelism strategies chosen by DistServe (different per phase!):",
    size=16,
    bold=True,
    color=ACCENT_TEAL,
)

table2 = make_table(slide, 4, 3, Inches(3), Inches(5.5), Inches(7.3), Inches(1.7))
for i, v in enumerate(["Model", "Prefill (TP, PP)", "Decode (TP, PP)"]):
    style_table_cell(
        table2.cell(0, i),
        v,
        size=13,
        bold=True,
        color=WHITE,
        bg_color=RGBColor(0x0A, 0x3D, 0x62),
    )
for r, row in enumerate(
    [
        ["OPT-13B", "(2, 1)", "(1, 1)"],
        ["OPT-66B", "(4, 1)", "(2, 2)"],
        ["OPT-175B", "(3, 3)", "(4, 3)"],
    ]
):
    bg = RGBColor(0x22, 0x22, 0x3A) if r % 2 == 0 else RGBColor(0x1A, 0x1A, 0x2E)
    for c, v in enumerate(row):
        style_table_cell(
            table2.cell(r + 1, c),
            v,
            size=13,
            color=ACCENT_TEAL if c > 0 else WHITE,
            bg_color=bg,
        )


# =============================================
# SLIDE 20: DistServe Latency & Ablation
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "DistServe: Latency Breakdown & Ablation",
    size=34,
    bold=True,
    color=WHITE,
)

# KV-cache finding
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x0A, 0x3D, 0x20),
)
tb = add_text_box(slide, Inches(1.0), Inches(1.6), Inches(5.2), Inches(2.3))
set_text(tb.text_frame, "KV-Cache Transmission", size=20, bold=True, color=ACCENT_GREEN)
add_bullet(tb.text_frame, "OPT-175B: < 0.1% of total latency", size=16, color=WHITE)
add_bullet(tb.text_frame, "95% of requests: < 30ms delay", size=16, color=WHITE)
add_para(
    tb.text_frame,
    "Transmission is negligible.",
    size=18,
    bold=True,
    color=ACCENT_GREEN,
    space_before=Pt(12),
)
add_para(
    tb.text_frame,
    "Confirms Splitwise's findings independently.",
    size=14,
    color=LIGHT_GRAY,
    space_before=Pt(4),
)

# Ablation
add_shape_bg(
    slide,
    Inches(6.9),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x22, 0x22, 0x3A),
)
tb = add_text_box(slide, Inches(7.1), Inches(1.6), Inches(5.2), Inches(2.3))
set_text(tb.text_frame, "Ablation Study", size=20, bold=True, color=ACCENT_ORANGE)
add_bullet(tb.text_frame, "vLLM++ (+ best parallelism search)", size=16, color=WHITE)
add_bullet(
    tb.text_frame, "= same performance as default vLLM!", size=16, color=ACCENT_RED
)
add_para(
    tb.text_frame,
    "Interference prevents any parallelism gains when colocated.",
    size=14,
    color=LIGHT_GRAY,
    space_before=Pt(8),
)
add_para(
    tb.text_frame,
    "Only disaggregation unlocks the benefit.",
    size=16,
    bold=True,
    color=ACCENT_GREEN,
    space_before=Pt(8),
)


# =============================================
# SLIDE 21: Comparison
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame,
    "Splitwise vs DistServe: Complementary Approaches",
    size=34,
    bold=True,
    color=WHITE,
)

table = make_table(slide, 9, 3, Inches(1.0), Inches(1.3), Inches(11.3), Inches(5.0))
h = ["Dimension", "Splitwise", "DistServe"]
d = [
    ["Core focus", "Heterogeneous hardware", "Goodput optimization"],
    ["Cluster type", "Mixed GPU types (H100+A100)", "Homogeneous (same GPUs)"],
    ["Key innovation", "Right hardware per phase", "Right parallelism per phase"],
    ["Target audience", "Cloud providers (CSPs)", "LLM service operators"],
    ["KV-cache transfer", "Per-layer overlapped (MSCCL++)", "Pull-based on-demand"],
    ["Formal analysis", "Characterization-driven", "Queueing theory-driven"],
    ["Evaluation", "Real A100+H100 + simulator", "Real A100 + simulator"],
    ["Venue", "ISCA 2024", "OSDI 2024"],
]
for i, v in enumerate(h):
    style_table_cell(
        table.cell(0, i),
        v,
        size=14,
        bold=True,
        color=WHITE,
        bg_color=RGBColor(0x0A, 0x3D, 0x62),
    )
for r, row in enumerate(d):
    bg = RGBColor(0x22, 0x22, 0x3A) if r % 2 == 0 else RGBColor(0x1A, 0x1A, 0x2E)
    style_table_cell(
        table.cell(r + 1, 0), row[0], size=13, color=LIGHT_GRAY, bg_color=bg, bold=True
    )
    style_table_cell(
        table.cell(r + 1, 1), row[1], size=13, color=ACCENT_TEAL, bg_color=bg
    )
    style_table_cell(
        table.cell(r + 1, 2), row[2], size=13, color=ACCENT_ORANGE, bg_color=bg
    )

tb = add_text_box(slide, Inches(1.0), Inches(6.5), Inches(11.3), Inches(0.6))
set_text(
    tb.text_frame,
    'Splitwise: "Use the right hardware"  |  DistServe: "Use the right software config"  |  Best: combine both',
    size=16,
    bold=True,
    color=ACCENT_GREEN,
    alignment=PP_ALIGN.CENTER,
)


# =============================================
# SLIDE 22: Both Papers Agree
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(tb.text_frame, "Points of Consensus", size=36, bold=True, color=WHITE)

agreements = [
    "Colocation of prefill and decoding is fundamentally flawed for SLO-sensitive workloads",
    "KV-cache transfer overhead is negligible on modern GPU clusters (<0.1% of E2E)",
    "Each phase benefits from different resource allocation and parallelism strategies",
    "Disaggregation enables 2-7\u00d7 improvement in effective serving capacity",
    "Applicable to ALL modern transformer-based LLMs (including MoE)",
    "Long context windows make disaggregation even more valuable (growing phase asymmetry)",
]
tb = add_text_box(slide, Inches(1.0), Inches(1.5), Inches(11.3), Inches(5.0))
set_text(tb.text_frame, "", size=16, color=WHITE)
for a in agreements:
    add_bullet(tb.text_frame, a, size=18, color=WHITE)


# =============================================
# SLIDE 23: Future Directions
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(
    tb.text_frame, "Limitations & Future Directions", size=36, bold=True, color=WHITE
)

# Limitations
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x50, 0x15, 0x15),
)
tb = add_text_box(slide, Inches(1.0), Inches(1.6), Inches(5.2), Inches(2.3))
set_text(tb.text_frame, "Shared Limitations", size=20, bold=True, color=ACCENT_RED)
add_bullet(tb.text_frame, "Less beneficial with very few GPUs", size=15, color=WHITE)
add_bullet(
    tb.text_frame, "Basic fault tolerance (restart on failure)", size=15, color=WHITE
)
add_bullet(
    tb.text_frame, "FCFS \u2192 convoy effect with mixed sizes", size=15, color=WHITE
)
add_bullet(tb.text_frame, "Batch/offline may prefer colocation", size=15, color=WHITE)

# Future
add_shape_bg(
    slide,
    Inches(6.9),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x0A, 0x3D, 0x20),
)
tb = add_text_box(slide, Inches(7.1), Inches(1.6), Inches(5.2), Inches(2.3))
set_text(
    tb.text_frame, "Open Research Questions", size=20, bold=True, color=ACCENT_GREEN
)
add_bullet(
    tb.text_frame, "Preemptive scheduling + disaggregation", size=15, color=WHITE
)
add_bullet(
    tb.text_frame, "Heterogeneous HW + optimized placement", size=15, color=WHITE
)
add_bullet(tb.text_frame, "Long-context (1M+ tokens) inference", size=15, color=WHITE)
add_bullet(tb.text_frame, "MoE expert routing interaction", size=15, color=WHITE)

# Adoption bar
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(4.4),
    Inches(11.7),
    Inches(1.2),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.0), Inches(4.5), Inches(11.3), Inches(1.0))
set_text(tb.text_frame, "Industry Adoption", size=20, bold=True, color=ACCENT_TEAL)
add_para(
    tb.text_frame,
    "Already adopted by: SGLang, vLLM, Mooncake  |  Follow-up: PolyServe, DuetServe, NVIDIA Dynamo",
    size=16,
    color=WHITE,
    space_before=Pt(4),
)
add_para(
    tb.text_frame,
    "Phase disaggregation is becoming the standard architecture for LLM serving.",
    size=16,
    bold=True,
    color=ACCENT_GREEN,
    space_before=Pt(4),
)


# =============================================
# SLIDE 24: Summary
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)

tb = add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.8))
set_text(tb.text_frame, "Summary", size=40, bold=True, color=WHITE)

# Splitwise summary
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x15, 0x50, 0x70),
)
tb = add_text_box(slide, Inches(1.0), Inches(1.6), Inches(5.2), Inches(2.3))
set_text(tb.text_frame, "Splitwise (ISCA 2024)", size=22, bold=True, color=ACCENT_TEAL)
add_bullet(tb.text_frame, "7 insights from production workloads", size=15, color=WHITE)
add_bullet(tb.text_frame, "Heterogeneous hardware per phase", size=15, color=WHITE)
add_bullet(
    tb.text_frame, "1.4\u00d7 throughput at 20% lower cost", size=15, color=ACCENT_GREEN
)
add_bullet(
    tb.text_frame, "or 2.35\u00d7 throughput, same power", size=15, color=ACCENT_GREEN
)

# DistServe summary
add_shape_bg(
    slide,
    Inches(6.9),
    Inches(1.5),
    Inches(5.6),
    Inches(2.5),
    RGBColor(0x50, 0x15, 0x40),
)
tb = add_text_box(slide, Inches(7.1), Inches(1.6), Inches(5.2), Inches(2.3))
set_text(
    tb.text_frame, "DistServe (OSDI 2024)", size=22, bold=True, color=ACCENT_ORANGE
)
add_bullet(tb.text_frame, "Formalized goodput optimization", size=15, color=WHITE)
add_bullet(tb.text_frame, "Automatic parallelism + placement", size=15, color=WHITE)
add_bullet(
    tb.text_frame, "Up to 7.4\u00d7 higher request rate", size=15, color=ACCENT_GREEN
)
add_bullet(tb.text_frame, "Up to 12.6\u00d7 tighter SLO", size=15, color=ACCENT_GREEN)

# Big picture
add_shape_bg(
    slide,
    Inches(0.8),
    Inches(4.4),
    Inches(11.7),
    Inches(1.5),
    RGBColor(0x0A, 0x3D, 0x62),
)
tb = add_text_box(slide, Inches(1.0), Inches(4.5), Inches(11.3), Inches(1.3))
set_text(
    tb.text_frame,
    "The Big Picture",
    size=22,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
)
add_para(
    tb.text_frame,
    "Prefill and decoding are fundamentally different workloads.",
    size=20,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
    space_before=Pt(8),
)
add_para(
    tb.text_frame,
    "Treating them as one wastes hardware, power, and money. Disaggregation is the right abstraction.",
    size=20,
    bold=True,
    color=ACCENT_GREEN,
    alignment=PP_ALIGN.CENTER,
    space_before=Pt(4),
)


# =============================================
# SLIDE 25: Thank You
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BG)
add_shape_bg(slide, Inches(0), Inches(3.0), Inches(13.333), Pt(4), ACCENT_TEAL)

tb = add_text_box(slide, Inches(1), Inches(1.5), Inches(11.333), Inches(1.5))
set_text(
    tb.text_frame,
    "Thank You",
    size=52,
    bold=True,
    color=WHITE,
    alignment=PP_ALIGN.CENTER,
)

tb2 = add_text_box(slide, Inches(1), Inches(3.5), Inches(11.333), Inches(0.8))
set_text(
    tb2.text_frame, "Questions?", size=36, color=ACCENT_TEAL, alignment=PP_ALIGN.CENTER
)

tb3 = add_text_box(slide, Inches(2), Inches(4.8), Inches(9.333), Inches(2.5))
set_text(tb3.text_frame, "Papers", size=18, bold=True, color=ACCENT_ORANGE)
add_para(
    tb3.text_frame,
    "Splitwise: arXiv:2311.18677 (ISCA 2024)",
    size=16,
    color=LIGHT_GRAY,
    space_before=Pt(4),
)
add_para(
    tb3.text_frame,
    "DistServe: arXiv:2401.09670 (OSDI 2024)",
    size=16,
    color=LIGHT_GRAY,
    space_before=Pt(4),
)
add_para(tb3.text_frame, "", size=12, color=WHITE, space_before=Pt(16))
add_para(
    tb3.text_frame,
    "Berat Celik  &  Jiayang (Ethan) Chen",
    size=20,
    bold=True,
    color=WHITE,
    space_before=Pt(4),
)
add_para(
    tb3.text_frame,
    "ECE 5545: ML Hardware & Systems  |  Spring 2026",
    size=16,
    color=MED_GRAY,
    space_before=Pt(4),
)


# Save
prs.save(
    "/Users/beratcelik/Desktop/hml presentation/presentation/Phase_Disaggregation_LLM_Inference.pptx"
)
print("DONE: 25 slides created.")
