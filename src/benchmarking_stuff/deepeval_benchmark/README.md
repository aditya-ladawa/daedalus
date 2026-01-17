# DeepEval Benchmark for Daedalus Agent

Comprehensive evaluation framework for the Daedalus deep research agent using DeepEval metrics.

## Metrics Overview

### Built-in Metrics (7 active)

| Category      | Metric                    | Status | What It Measures                        |
| ------------- | ------------------------- | ------ | --------------------------------------- |
| **Core**      | AnswerRelevancyMetric     | ✅     | Is response on-topic?                   |
| **Core**      | HallucinationMetric       | ✅     | Does output contradict context?         |
| **Action**    | TaskCompletionMetric      | ✅     | Did agent complete the research report? |
| **Action**    | ToolCorrectnessMetric     | ⏸️     | Disabled (requires expected_tools)      |
| **Action**    | ArgumentCorrectnessMetric | ⏸️     | Disabled (DeepEval library bug)         |
| **Action**    | StepEfficiencyMetric      | ⏸️     | Disabled (DeepEval library bug)         |
| **Reasoning** | PlanQualityMetric         | ⏸️     | Disabled (DeepEval library bug)         |
| **Reasoning** | PlanAdherenceMetric       | ⏸️     | Disabled (DeepEval library bug)         |
| **RAG**       | FaithfulnessMetric        | ✅     | Is output grounded in sources?          |
| **RAG**       | ContextualRelevancyMetric | ✅     | Is retrieved context relevant?          |

### Custom G-Eval Metrics (5 active)

| Metric                  | What It Measures                                             |
| ----------------------- | ------------------------------------------------------------ |
| scientific_precision    | Quantitative rigor (domain-appropriate metrics, evidence)    |
| section_coherence       | Logical structure (Abstract, Intro, Methods, Results, etc.)  |
| citation_quality        | Proper citation coverage and References section              |
| isolation_effectiveness | Clean sub-agent integration (no artifacts)                   |
| research_depth          | PhD-level analysis (mechanisms, multi-dimensional synthesis) |

## Key Features

✅ **Smart File Extraction** - Automatically reads full reports from `agent_workspace/` disk  
✅ **Domain-Agnostic** - Scientific precision adapts to research domain (not just genetics)  
✅ **Full Judge Reasoning** - Complete explanations, no truncation  
✅ **References Validation** - Ensures References section is in the report file

## Installation

```bash
pip install deepeval
```

## Configuration

Edit `config.py` to change settings:

```python
# Change judge model
JUDGE_MODEL = "gemini-2.5-pro"  # Current (best quality)
JUDGE_MODEL = "gemini-2.5-flash"  # Alternative (faster, cheaper)

# Adjust thresholds
THRESHOLDS = {
    "task_completion": 0.7,
    "scientific_precision": 0.7,
    "citation_quality": 0.7,
    # ...
}
```

## Usage

### Run Evaluation

```bash
# Single query evaluation (most common)
python evaluate_agent.py --query "Write a comprehensive review of the relationship between sleep quality and cognitive performance in adults"

# Quick test (3 queries from config.py)
python evaluate_agent.py --quick

# Full evaluation (all queries from config.py)
python evaluate_agent.py

# Specific metric categories
python evaluate_agent.py --query "..." --metrics core action rag custom
```

### View Results

Results are automatically saved to `results/`:

- `evaluation_YYYYMMDD_HHMMSS.json` - Full scores, reasons, and metadata
- `report_YYYYMMDD_HHMMSS.md` - Human-readable markdown report with full judge reasoning

```bash
# View latest report
cat results/report_*.md | tail -n 100

# Parse JSON results
cat results/evaluation_*.json | jq '.scores'
```

## Custom Metric Details

### Scientific Precision (Domain-Agnostic)

Evaluates quantitative rigor appropriate to the research domain:

- **Quantitative Evidence** (35%): Numerical values, effect sizes, sample sizes, correlation coefficients
- **Methodological Clarity** (25%): Data sources, study designs, analytical approaches
- **Evidence Sourcing** (25%): Citations, source quality, synthesis
- **Scientific Nuance** (15%): Limitations, conflicting findings, caveats

**Not domain-specific** - Works for genetics, neuroscience, social science, etc.

### Section Coherence

Evaluates structural completeness and logical flow:

- Required sections: Title, Abstract, Introduction, Methods, Results, Discussion, Limitations, Conclusions, References
- Logical progression from research question to conclusion
- Internal consistency across sections

### Citation Quality

Evaluates proper academic referencing:

- **Inline citations**: Consistent numbering `[1]`, `[2]`, `[3]`
- **References section**: Must be present at end of report
- **Completeness**: All inline citations have corresponding References entries
- **Source quality**: Peer-reviewed publications, recent sources

### Isolation Effectiveness

Evaluates clean integration of sub-agent outputs:

- No visible "sub-agent said..." artifacts
- Unified voice throughout report
- No raw tool output dumps
- Properly merged and re-indexed citations

### Research Depth

Evaluates PhD-level analysis quality:

- Multi-dimensional analysis (mechanisms, implications, context)
- Critical synthesis (not just summary)
- Gap identification in literature
- Broader scientific context

## Output Example

```markdown
# Evaluation Report

Query: Write a comprehensive review of sleep quality and cognitive performance

## Metric Scores

| Metric           | Score | Passed | Reason                                                                                                                                                                                                                                                                                       |
| ---------------- | ----- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Answer Relevancy | 1.00  | ✅     | The response is perfectly on-topic and directly addresses all parts of the request. It provides a comprehensive review including abstract, introduction, methods, results, discussion, and references sections that thoroughly cover sleep quality and cognitive performance.                |
| citation_quality | 1.00  | ✅     | The output demonstrates exceptional alignment with all evaluation steps. It provides comprehensive citations with complete bibliographic information including authors, titles, journals, years, and DOIs. Citations are consistently formatted and properly integrated throughout the text. |
| research_depth   | 0.90  | ✅     | The output provides a highly structured and comprehensive plan for a PhD-level review paper demonstrating multi-dimensional analysis by examining neurobiological mechanisms, different research levels, and clinical implications. Shows intent to synthesize information critically.       |
```

## File Extraction Logic

The evaluation automatically finds and reads the agent's report:

1. **Primary**: Scans `agent_workspace/` for recently modified `.md` files
2. **Priority**: Mentioned files > `report.md` files > largest files > most recent
3. **Exclusions**: Skips `references.md` (citation tracking only)
4. **Time window**: Files modified in last 30 minutes

This ensures the full report content is evaluated, not truncated agent responses.

## Cost Estimate

Using Gemini 2.5 Pro as judge:

- Single query evaluation: ~15-20 metrics × ~2,000 tokens each = ~40,000 tokens
- Gemini 2.5 Pro: Free tier up to usage limits
- **Estimated cost per evaluation: $0** (within free tier)

## Troubleshooting

### Low Citation Quality Scores

**Problem**: Report has inline citations `[1], [2]` but no References section  
**Solution**: Agent must copy `references.md` to end of `report.md`  
**Check**: Search for `## References` at end of report file

### Low Scientific Precision

**Problem**: Report lacks quantitative evidence  
**Solution**: Include specific numbers, effect sizes, sample sizes, percentages  
**Not required**: p-values, SNPs (domain-specific)

### Low Section Coherence

**Problem**: Missing required sections  
**Solution**: Ensure report has: Abstract, Introduction, Methods, Results, Discussion, Limitations, Conclusions, References

## Future Enhancements

- ✅ File extraction from disk (implemented)
- ✅ Domain-agnostic precision metric (implemented)
- ✅ Full judge reasoning (implemented)
- ⏳ Fix DeepEval library bugs for agentic metrics
- ⏳ Add expected_tools parameter for ToolCorrectnessMetric
- ⏳ Cost tracking per evaluation
