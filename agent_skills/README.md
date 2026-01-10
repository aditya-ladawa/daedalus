# Agent Skills

This directory contains modular skill definitions for the Deep Research Agent, following the **Progressive Disclosure** pattern.

## Skills Available

| Skill                                                | Purpose                                                      | When to Use                                     |
| ---------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------- |
| [gap_analysis.md](./gap_analysis.md)                 | Identify missing research, unexplored angles, contradictions | After gathering research, before finalizing     |
| [insight_generation.md](./insight_generation.md)     | Synthesize novel connections, generate hypotheses            | When writing Discussion, formulating next steps |
| [research_progression.md](./research_progression.md) | Track investigation history, build cumulative knowledge      | Starting/ending sessions, avoiding redundancy   |

## How Skills Work

### Progressive Disclosure Pattern

Skills follow a 3-layer architecture:

1. **Metadata Layer** (YAML frontmatter):

   - Name and brief description (~100 tokens)
   - Loaded at session start to help agent decide relevance

2. **Full Instructions** (Markdown content):

   - Complete frameworks, processes, and examples
   - Loaded only when skill is deemed relevant

3. **Just-in-Time Application**:
   - Agent references skill when needed
   - No overhead when not in use

### Usage in Agent Prompt

Skills are referenced in the main agent prompt:

```markdown
**Advanced Capabilities - Agent Skills:**

For specialized research capabilities, you can reference skill files in `../agent_skills/`:

- **Gap Analysis**: Use when identifying missing research → Read `../agent_skills/gap_analysis.md`
- **Insight Generation**: Use when synthesizing connections → Read `../agent_skills/insight_generation.md`
- **Research Progression**: Use when tracking multi-session work → Read `../agent_skills/research_progression.md`

To use a skill:

1. task(filesystem_reader, "Read ../agent_skills/{skill_name}.md")
2. Apply the framework from the skill to your current work
3. Document application in your research output
```

## Benefits

- **Modular**: Easy to add/remove/update skills
- **Scalable**: No prompt bloat - only load what's needed
- **Maintainable**: Skills can be versioned and improved independently
- **Discoverable**: Agent knows which skills exist via metadata

## Creating New Skills

To add a new skill:

1. Create `{skill_name}.md` with YAML frontmatter:

```yaml
---
name: Skill Name
description: Brief description of what this skill does (~100 tokens)
---
```

2. Add full framework in markdown below frontmatter

3. Update this README with new skill entry

4. Reference in main agent prompt if it should be always-available
