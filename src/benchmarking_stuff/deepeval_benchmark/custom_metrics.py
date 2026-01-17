"""
Custom G-Eval Metrics for Daedalus Agent Evaluation

These metrics evaluate aspects specific to PhD-level biomedical research
that built-in DeepEval metrics don't cover.
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

import config


# =============================================================================
# HELPER: Create GEval with configured model
# =============================================================================

def create_geval(
    name: str,
    criteria: str,
    evaluation_params: list,
    threshold: float = None
) -> GEval:
    """Create a GEval metric with configured model settings"""
    return GEval(
        name=name,
        criteria=criteria,
        evaluation_params=evaluation_params,
        threshold=threshold or config.THRESHOLDS.get(name, config.DEFAULT_THRESHOLD),
        model=config.JUDGE_MODEL,
    )


# =============================================================================
# CUSTOM METRIC 1: Scientific Precision
# =============================================================================

SCIENTIFIC_PRECISION_CRITERIA = """
Evaluate the scientific rigor and quantitative depth in this research report.

IMPORTANT: Score based on what is APPROPRIATE for the research domain. 
Not all fields require genetics data (SNPs, genes) or exact p-values.
Evaluate whether the report provides sufficient quantitative evidence for its claims.

SCORING DIMENSIONS:

1. QUANTITATIVE EVIDENCE (35% weight):
   - Are numerical values provided to support claims?
   - This could include: effect sizes, percentages, sample sizes, odds ratios, 
     correlation coefficients, confidence intervals, or other domain-appropriate metrics
   - Are ranges and precision indicated where appropriate?
   - Score based on presence of numbers, not specific statistical formats

2. METHODOLOGICAL CLARITY (25% weight):
   - Are research methods clearly described?
   - Are data sources and study designs mentioned?
   - Are analytical approaches specified?
   - For reviews: Is the review methodology explained (databases, search terms)?

3. EVIDENCE SOURCING (25% weight):
   - Are claims attributed to specific studies/sources via citations?
   - Are multiple sources synthesized?
   - Is there differentiation between strong and weak evidence?

4. SCIENTIFIC NUANCE (15% weight):
   - Are limitations acknowledged?
   - Are conflicting findings discussed?
   - Are caveats and conditions noted?
   - Is appropriate hedging used for uncertain claims?

SCORING SCALE:
- 1-3: Mostly qualitative claims without supporting data
- 4-6: Some quantitative evidence but gaps in rigor
- 7-8: Good quantitative support with minor omissions
- 9-10: Comprehensive quantitative evidence appropriate to the domain

Provide a score from 1-10.
"""


def get_scientific_precision_metric() -> GEval:
    """Create Scientific Precision metric"""
    return create_geval(
        name="scientific_precision",
        criteria=SCIENTIFIC_PRECISION_CRITERIA,
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    )


# =============================================================================
# CUSTOM METRIC 2: Section Coherence
# =============================================================================

SECTION_COHERENCE_CRITERIA = """
Evaluate the logical structure and narrative flow of this research report.

SCORING DIMENSIONS:

1. STRUCTURAL COMPLETENESS (25% weight):
   - Does the report have recognizable sections (Introduction, Methods, Results, Discussion)?
   - Are sections appropriately proportioned (not 90% intro, 10% results)?
   - Is there a clear abstract, summary, or executive overview?
   - Is there a references/bibliography section?

2. LOGICAL FLOW (35% weight):
   - Does each section naturally build on the previous one?
   - Are there smooth, explicit transitions between sections?
   - Is there a clear narrative arc (question → method → findings → implications)?
   - Does the report avoid unnecessary repetition or backtracking?

3. INTERNAL CONSISTENCY (25% weight):
   - Do Results accurately reflect what Methods described?
   - Does Discussion properly interpret the Results shown?
   - Are there any contradictions between sections?
   - Do citations remain consistent throughout?

4. QUERY ALIGNMENT (15% weight):
   - Does the Introduction properly frame the research question?
   - Does every section contribute to answering the original query?
   - Does the Conclusion directly address what was asked?
   - Is there scope creep (wandering into unrelated topics)?

SCORING SCALE:
- 1-3: Disorganized, sections disconnected or missing
- 4-6: Recognizable structure but flow issues
- 7-8: Good structure with minor transition gaps
- 9-10: Perfectly structured, reads like a published paper

Provide a score from 1-10.
"""


def get_section_coherence_metric() -> GEval:
    """Create Section Coherence metric"""
    return create_geval(
        name="section_coherence",
        criteria=SECTION_COHERENCE_CRITERIA,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT
        ],
    )


# =============================================================================
# CUSTOM METRIC 3: Citation Quality
# =============================================================================

CITATION_QUALITY_CRITERIA = """
Evaluate citation practices in this research report.

SCORING DIMENSIONS:

1. COVERAGE (30% weight):
   - Are major factual claims supported by citations?
   - Are statistical values (p-values, effect sizes) attributed to sources?
   - Is there a numbered references or bibliography section at the end?
   - Are key concepts properly attributed (not presented as common knowledge)?

2. FORMAT CONSISTENCY (25% weight):
   - Are citations numbered consistently [1], [2], [3] throughout?
   - Do reference entries include: Author(s), Title, Source/Journal, Year?
   - Are URLs complete and not truncated (...)?
   - Is the numbering sequential (first appearance order)?

3. SOURCE QUALITY (25% weight):
   - Are sources primarily peer-reviewed journals?
   - Are sources authoritative (Nature, Science, JAMA, not random blogs)?
   - Is there a good mix of primary sources (original papers) and reviews?
   - Are sources recent/relevant to current understanding?

4. INTEGRATION (20% weight):
   - Are citations naturally integrated into the text?
   - Is there appropriate citation density (not over/under-cited)?
   - Are contradictory findings from different sources acknowledged?
   - Are direct quotes properly attributed?

SCORING SCALE:
- 1-3: Few/no citations, no reference list, or broken citations
- 4-6: Some citations present but incomplete or inconsistent
- 7-8: Good citations with minor formatting issues
- 9-10: Publication-ready citations with complete references

Provide a score from 1-10.
"""


def get_citation_quality_metric() -> GEval:
    """Create Citation Quality metric"""
    return create_geval(
        name="citation_quality",
        criteria=CITATION_QUALITY_CRITERIA,
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    )


# =============================================================================
# CUSTOM METRIC 4: Isolation Effectiveness
# =============================================================================

ISOLATION_EFFECTIVENESS_CRITERIA = """
Evaluate sub-agent isolation quality in this research report.

CONTEXT: This report was generated by a multi-agent system where:
- A main agent orchestrates the research
- Sub-agents (biomedical researcher, internet researcher) handle specific tasks
- Sub-agent outputs are integrated into the final report

SCORING DIMENSIONS:

1. CLEAN INTEGRATION (40% weight):
   - Are sub-agent findings seamlessly woven into the narrative?
   - Is there NO visible "The sub-agent said..." or meta-commentary?
   - Is there NO raw tool output or structured data visible?
   - Does the report read as unified prose, not copy-pasted results?

2. CONTEXT SEPARATION (30% weight):
   - Is each section focused on its intended topic?
   - Is there evidence of "context pollution" (irrelevant tangents)?
   - Are there sudden topic shifts that suggest sub-agent boundaries?
   - Is there repetition that suggests context confusion?

3. ATTRIBUTION INTEGRITY (30% weight):
   - Are citations from different sub-agents properly merged?
   - Is there a unified references section (not separate per source)?
   - Are source attributions preserved (not lost in integration)?
   - Is the numbering consistent across all sources?

WHAT TO LOOK FOR:
- Bad: "According to the research agent, the findings show..."
- Bad: "[Tool output]: JSON data here..."
- Bad: Duplicate references with different numbers
- Good: Smooth prose with integrated citations [1], [2]

SCORING SCALE:
- 1-3: Raw sub-agent output visible, poor integration
- 4-6: Mostly integrated but visible seams or artifacts
- 7-8: Good integration with minor artifacts
- 9-10: Seamless, indistinguishable from single-author work

Provide a score from 1-10.
"""


def get_isolation_effectiveness_metric() -> GEval:
    """Create Isolation Effectiveness metric"""
    return create_geval(
        name="isolation_effectiveness",
        criteria=ISOLATION_EFFECTIVENESS_CRITERIA,
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    )


# =============================================================================
# CUSTOM METRIC 5: Research Depth
# =============================================================================

RESEARCH_DEPTH_CRITERIA = """
Evaluate the comprehensiveness and depth of this PhD-level research synthesis.

CONTEXT: This is a research synthesis report, not a summary. It should provide 
deep, multi-dimensional analysis that goes beyond surface-level overview.

SCORING DIMENSIONS:

1. MULTI-DIMENSIONAL COVERAGE (30% weight):
   - Does it cover genetic, molecular, cellular, and clinical levels where relevant?
   - Are both basic science and translational aspects addressed?
   - Are multiple research methodologies discussed (GWAS, functional studies, clinical trials)?
   - Does it integrate evidence from different types of studies?

2. MECHANISTIC DEPTH (30% weight):
   - Does it explain HOW things work, not just WHAT is observed?
   - Are biological pathways and mechanisms described?
   - Is there explanation of molecular/cellular processes?
   - Does it go beyond correlation to discuss causation where established?

3. CONTEXTUAL FRAMING (20% weight):
   - Is historical context or evolution of understanding provided?
   - Are current gaps in knowledge explicitly identified?
   - Are competing hypotheses or unresolved questions discussed?
   - Is the broader significance/implications discussed?

4. EVIDENCE INTEGRATION (20% weight):
   - Are findings from multiple studies synthesized (not just listed)?
   - Are contradictory findings acknowledged and reconciled?
   - Is there critical evaluation of evidence quality?
   - Are limitations of current evidence discussed?

WHAT DISTINGUISHES DEPTH LEVELS:
- Shallow (1-3): Lists facts, no mechanisms, single perspective
- Moderate (4-6): Some mechanistic detail, mostly descriptive
- Good (7-8): Multi-layered, mechanistic, integrates evidence
- Excellent (9-10): PhD-thesis level depth, critical synthesis, identifies frontiers

NOTE: This is NOT about length. A focused, deep 2-page analysis scores higher 
than a superficial 10-page list.

SCORING SCALE:
- 1-3: Surface-level overview, lacks mechanistic depth
- 4-6: Moderate depth but missing integration or mechanisms
- 7-8: Strong depth with good mechanistic detail and synthesis
- 9-10: Exceptional depth worthy of PhD-level publication

Provide a score from 1-10.
"""


def get_research_depth_metric() -> GEval:
    """Create Research Depth metric"""
    return create_geval(
        name="research_depth",
        criteria=RESEARCH_DEPTH_CRITERIA,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT
        ],
    )


# =============================================================================
# GET ALL CUSTOM METRICS
# =============================================================================

def get_all_custom_metrics() -> list:
    """Return all custom G-Eval metrics"""
    return [
        get_scientific_precision_metric(),
        get_section_coherence_metric(),
        get_citation_quality_metric(),
        get_isolation_effectiveness_metric(),
        get_research_depth_metric(),
    ]


# =============================================================================
# METRIC INFO
# =============================================================================

CUSTOM_METRICS_INFO = {
    "scientific_precision": {
        "name": "Scientific Precision",
        "description": "Evaluates PhD-level exactness: p-values, CIs, sample sizes, gene IDs",
        "category": "Custom - Research Quality",
    },
    "section_coherence": {
        "name": "Section Coherence",
        "description": "Evaluates logical structure and narrative flow between sections",
        "category": "Custom - Structure",
    },
    "citation_quality": {
        "name": "Citation Quality",
        "description": "Evaluates citation coverage, format, and source quality",
        "category": "Custom - Academic Standards",
    },
    "isolation_effectiveness": {
        "name": "Isolation Effectiveness",
        "description": "Evaluates clean integration of sub-agent outputs",
        "category": "Custom - Architecture Validation",
    },
    "research_depth": {
        "name": "Research Depth",
        "description": "Evaluates comprehensiveness, mechanistic depth, and multi-dimensional coverage",
        "category": "Custom - Research Quality",
    },
}
