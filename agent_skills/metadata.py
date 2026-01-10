"""Metadata for agent skills - used for progressive disclosure pattern."""

SKILLS_METADATA = {
    "gap_analysis": {
        "name": "Gap Analysis",
        "description": "Domain-agnostic framework for identifying gaps, contradictions, and unexplored areas across 5 dimensions (Completeness, Perspective, Consistency, Depth, Utility)",
        "when_to_use": "After gathering research context, before finalizing sections, when reviewing completed work"
    },
    "insight_generation": {
        "name": "Insight Generation",
        "description": "Framework for synthesizing novel connections, generating hypotheses, and transforming findings into actionable research directions",
        "when_to_use": "When writing Discussion/Implications sections, formulating next steps, synthesizing findings"
    },
    "research_progression": {
        "name": "Research Progression",
        "description": "Framework for tracking investigation history, building cumulative knowledge across sessions, and avoiding redundant work",
        "when_to_use": "At session start/end, when resuming previous work, to maintain research continuity"
    }
}


def get_skills_prompt_section() -> str:
    """Generate the skills section for injection into system prompt."""
    skills_list = "\n".join([
        f"   - **{skill_id}**: {meta['description']}"
        for skill_id, meta in SKILLS_METADATA.items()
    ])
    
    return f"""Agent Skills (Advanced Capabilities):
   You have access to specialized metacognitive frameworks:
   
{skills_list}
   
   To use a skill: load_skill("skill_name") to get the full framework, then apply it
   
   These skills provide structured questions, processes, templates, and examples to enhance your research capabilities."""
