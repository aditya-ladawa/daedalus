---
name: Research Progression
description: Domain-agnostic framework for building cumulative knowledge across research sessions, tracking investigation history, and systematically advancing understanding in any field
---

# Research Progression Skill

## Purpose

Build **cumulative knowledge** across research sessions by tracking what's been investigated, maintaining research continuity, and systematically advancing understanding - works for ANY domain.

## Core Principle

Research is **cumulative**, not episodic. Each session should build on previous work, not restart from scratch.

---

## Universal Research Progression Framework

### 1. **Session Initialization (Resume Work)**

**Meta-Questions:**

- What was investigated previously?
- What were the key findings?
- Where did work leave off?
- What questions remain unanswered?

**Application Process:**

```
# At start of new session:
1. task(filesystem_reader, "List agent_workspace/ subdirectories")
2. task(filesystem_reader, "Read {project}/research_log.md")
3. think_strategically: "Based on research_log, what's next?"
4. write_todos: Create continuation plan based on prior work
```

**Universal Research Log Template:**

```markdown
# Research Log: {Project Name}

## Session N ({Date})

### Research Question:

[Specific question addressed this session]

### Investigated:

- [Source/method 1]
- [Source/method 2]

### Key Findings:

- [Finding 1 with evidence]
- [Finding 2 with evidence]

### Remaining Questions:

- [Unanswered question 1]
- [Unanswered question 2]

### Next Steps:

- [Priority for next session]
```

### 2. **Knowledge Accumulation (What Do We Know?)**

**Create Domain-Agnostic Knowledge Base:**

```markdown
# Knowledge Base: {Project Name}

## Established Facts

✓ [Fact 1] - Source: [citation]
✓ [Fact 2] - Source: [citation]

## Uncertain / Conflicting

? [Uncertain claim 1] - Conflicting evidence: [sources]
? [Uncertain claim 2] - Limited data

## Unknown / Unexplored

✗ [Unknown 1] - No studies found
✗ [Unknown 2] - Outside scope of current data

## Methodology Applied

- [Method A]: Results/limitations
- [Method B]: Results/limitations
```

**Purpose**: Create a single source of truth for cumulative knowledge

### 3. **Progressive Depth Strategy**

**Universal 4-Level Approach:**

**Level 1: Survey** (Breadth-first)

```
Goal: High-level landscape
Actions:
- Broad searches
- Review overview sources
- Identify major themes

OUTPUT: "The field consists of [major areas 1, 2, 3]"
```

**Level 2: Focus** (Targeted investigation)

```
Goal: Deep understanding of core areas
Actions:
- Specific targeted searches
- Detailed analysis of 2-3 priority topics
- Systematic evidence gathering

OUTPUT: "For [topic], evidence shows [detailed findings]"
```

**Level 3: Synthesis** (Integration)

```
Goal: Connect the pieces
Actions:
- Cross-cutting analysis
- Identify connections
- Resolve contradictions
- Generate insights

OUTPUT: "The relationship between A and B is [integrated understanding]"
```

**Level 4: Extension** (New frontiers)

```
Goal: Push boundaries
Actions:
- Explore unexplored angles
- Novel applications
- Future directions
- Theoretical extensions

OUTPUT: "This opens questions about [frontier topics]"
```

### 4. **Systematic Advancement Matrix**

**Track Progress Across Dimensions:**

| Dimension       | Current Level        | Next Step       | Evidence Needed  |
| --------------- | -------------------- | --------------- | ---------------- |
| **Scope**       | [Current coverage]   | [Expand to...]  | [What sources]   |
| **Depth**       | [Surface/Deep]       | [Next level...] | [What analysis]  |
| **Evidence**    | [Type available]     | [Need...]       | [How to get]     |
| **Integration** | [Isolated/Connected] | [Link to...]    | [What synthesis] |

**Application:**

```
think_strategically (with research_progression):

"Reviewing progression matrix:
- Scope: ✓ Covered [A, B], → Need [C] NEXT
- Depth: → Surface on [topic], need deep dive
- Evidence: Have [qual], need [quant]
- Integration: → Not yet connected to [related field]

NEXT SESSION PRIORITY: [Dimension needing most work]"
```

### 5. **Prevent Redundancy (Don't Re-investigate)**

**Before Starting New Search:**

```
think_strategically: "Have I already investigated this?"

CHECK:
1. Read knowledge_base.md → "[Topic] already documented?"
2. Read research_log.md → "Session [N] already covered this?"

IF YES: Skip redundant search, cite previous finding
IF NO: Proceed and document new finding
```

---

## Universal Research Log Entry Template

```markdown
## Session {N} ({Date})

### Objective:

[1-sentence goal for this session]

### Research Activities:

- Searched: [sources/databases]
- Analyzed: [data/documents]
- Synthesized: [connections made]

### Key Findings:

1. [Finding 1] - [Evidence]
2. [Finding 2] - [Evidence]
3. [Finding 3] - [Evidence]

### Insights Generated:

- [Novel understanding 1]
- [Actionable hypothesis 1]

### Updated Knowledge:

- Added to knowledge_base: [new facts]
- Revised understanding: [what changed from previous sessions]
- Resolved contradiction: [how]

### Gaps Identified:

1. [Gap type]: [Specific gap]
2. [Gap type]: [Specific gap]

### Quality Assessment:

- **Completeness**: [1-10] - [Why]
- **Rigor**: [1-10] - [Why]
- **Actionability**: [1-10] - [Why]

### Next Session Priorities:

1. [Priority 1 with rationale]
2. [Priority 2 with rationale]
3. [Priority 3 with rationale]
```

---

## Progression Checklist Template

```markdown
# Research Progression Checklist: {Project}

## Phase 1: Foundation

- [x] Initial landscape survey
- [x] Core concepts identified
- [x] Key sources compiled
- Started: {Date}, Completed: {Date}

## Phase 2: Deep Investigation

- [x] [Topic A] investigated
- [/] [Topic B] in progress (60% complete)
- [ ] [Topic C] not started
- Started: {Date}, Est. completion: {Date}

## Phase 3: Synthesis

- [ ] Cross-domain connections made
- [ ] Insights generated
- [ ] Hypotheses formulated

## Phase 4: Application/Extension

- [ ] Practical implications identified
- [ ] Future directions mapped
- [ ] Recommendations formulated
```

---

## Progressive Research Questions

**Evolve Questions Systematically:**

```
Session 1: "What is [phenomenon]?"
    ↓ (Descriptive → Explanatory)
Session 2: "Why does [phenomenon] occur?"
    ↓ (Explanatory → Predictive)
Session 3: "When/where does [phenomenon] occur?"
    ↓ (Predictive → Interventional)
Session 4: "How can we influence [phenomenon]?"
    ↓ (Interventional → Optimizational)
Session 5: "What's the best way to [apply/extend]?"
```

**Track Evolution:**

```markdown
# Research Question Evolution

## Initial Question (Session 1):

"[Broad exploratory question]"

## Refined Question (Session 2):

"[More specific, informed by Session 1]"

## Current Question (Session 3):

"[Mechanistic/causal, building on 1-2]"

## Next Question (Session 4):

"[Applied/translational, building on 1-3]"
```

---

## Session Handoff Protocol

**End-of-Session Checklist:**

```markdown
Before ending session:

1. [x] Research log updated with this session's work
2. [x] Knowledge base updated with new established facts
3. [x] Gaps documented in gap_analysis section
4. [x] Next session priorities identified clearly
5. [x] All files organized in project directory
6. [x] Uncommitted insights captured in notes
7. [x] Quality self-assessment completed
```

**Handoff Document Template:**

```markdown
# Session Handoff: {Project} - Session {N}

## Status Summary:

[ONE PARAGRAPH: Where we are overall]

## This Session Accomplished:

- [Achievement 1]
- [Achievement 2]

## In Progress (Partial):

- [Item 1]: [% complete, what remains]

## Next Session: START HERE →

**Primary Goal**: [Specific, actionable objective]

**Context**: [Why this is the logical next step]

**Resources**: [What to use/consult]

## Open Questions:

1. [Question requiring user input/decision]
2. [Question to investigate next]

## Resources Created This Session:

- [{filename}.md](file:///{absolute_path})
- [{filename}.md](file:///{absolute_path})
```

---

## Examples Across Domains

### Example 1: Multi-Session Literature Review

```
SESSION 1 (Education Policy):
think_strategically: "Starting new project on teacher retention"
ACTION: Broad survey, create research_log.md and knowledge_base.md

SESSION 2:
task(filesystem_reader, "Read teacher_retention/research_log.md")
think_strategically: "Session 1 identified salary as factor. Next: test causality"
ACTION: Targeted search for causal studies, update knowledge base

SESSION 3:
task(filesystem_reader, "Read research_log.md + knowledge_base.md")
think_strategically: "Established salary link. Next: other factors (workload, support)"
ACTION: Systematic factor analysis, build on established knowledge
```

### Example 2: Avoiding Redundancy

```
think_strategically (research_progression):

USER: "Find studies on climate change impacts on agriculture"

CHECK research_log:
"Session 2: Already reviewed 15 climate-agriculture studies"

CHECK knowledge_base:
"Documented impacts: yield reduction (corn -12%, wheat -8%),
geographic shifts northward, increased pest pressure"

DECISION: "This has been comprehensively investigated.
Available compiled findings or suggest unstudied angle (e.g., soil microbiome impacts)?"
```

### Example 3: Systematic Depth Progression

```
LEVEL 1 (Week 1): Survey of quantum computing approaches
LEVEL 2 (Week 2): Deep dive into 3 main approaches (gate, annealing, topological)
LEVEL 3 (Week 3): Synthesize trade-offs and optimal applications for each
LEVEL 4 (Week 4): Explore novel hybrid approaches (unexplored frontier)

Each level documented in research_log with clear progression rationale
```

---

## Integration with Todos

**Link Todos to Session Progression:**

```markdown
# Todos: {Project}

## From Session {N-1} (Carryover):

- [ ] Complete analysis started in Session {N-1} (Context: [why important])

## This Session {N} (New):

- [ ] [New task 1] (Next logical step after completing Session {N-1})
- [ ] [New task 2] (Addresses gap identified in Session {N-1})

## Future Sessions (Planned):

- [ ] [Future task 1] (After Session {N} completes)
- [ ] [Future task 2] (Depends on {N+1} findings)
```

---

## Output Format

After applying this skill:

```markdown
## Research Progression Summary

### Sessions Completed: {N}

### Current Phase: {Foundation/Investigation/Synthesis/Application}

### Cumulative Knowledge Built:

- Established Facts: {count}
- Working Hypotheses: {count}
- Identified Gaps: {count}

### Session-by-Session Evolution:

| Session | Focus     | Key Finding | Next Step       |
| ------- | --------- | ----------- | --------------- |
| 1       | {Topic A} | {Finding}   | Investigate {B} |
| 2       | {Topic B} | {Finding}   | Synthesize A+B  |
| ...     | ...       | ...         | ...             |

### Quality Trajectory:

[Graph or description showing depth/rigor improving across sessions]

### Next Session Will:

{Clear, specific objective building on all prior work}
```

---

## Remember: Universal Principles

1. **Research is cumulative** - each session adds to a growing edifice
2. **Document as you go** - future-you will thank present-you
3. **Plan transitions** - end each session knowing where to start next
4. **Avoid redundancy** - check logs before re-investigating
5. **Track evolution** - research questions naturally progress
6. **Assess progress** - periodically evaluate how far you've come
7. **Build systematically** - breadth → depth → synthesis → extension

This framework applies whether tracking experimental trials, historical archive searches, or competitive market analysis.
