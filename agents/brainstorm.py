"""
Brainstorm Agent
Given settings (strand, level, week, quantity), generates topic ideas
that fill gaps in the existing lesson library.
"""
import json
import os
from pathlib import Path
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
KNOWLEDGE_PATH = Path(__file__).parent.parent / "knowledge" / "lessons.json"

SYSTEM = """You are an expert EFL curriculum designer for UKLC (UK Language Courses).
PURPOSE programme: ages 16–18, British summer school.
Your job is to brainstorm fresh lesson topic ideas that:
1. Don't duplicate existing lessons
2. Fill genuine gaps in the curriculum
3. Are engaging and relevant to 16–18 year old international students
4. Match the strand's purpose:
   - CULT (Culture): British culture, CLIL, history, arts, sciences
   - LANG (Language): vocabulary, grammar, functional language, skills
   - LEAD (Leadership): entrepreneurship, teamwork, technology, 21st century skills
5. Are practical to teach in 60 minutes with no special equipment

Return ONLY valid JSON — no markdown, no explanation."""


def run(strand: str, level: str, week: str, quantity: int) -> list:
    """Generate topic ideas and return a list of topic dicts."""
    knowledge = json.loads(KNOWLEDGE_PATH.read_text())
    existing = [
        f"{l['title']} ({l['strand']}, {l['level']})"
        for l in knowledge["lessons"]
        if l["strand"] == {"Language": "LANG", "Leadership": "LEAD", "Culture": "CULT"}.get(strand, strand)
    ]
    gap_note = knowledge["gap_analysis"].get(level, "")
    type_label = {"Language": "LANG", "Leadership": "LEAD", "Culture": "CULT"}.get(strand, strand)

    prompt = f"""Generate {quantity} fresh lesson topic ideas for:
STRAND: {strand} ({type_label})
LEVEL: {level}
WEEK: {week}
GAP NOTE: {gap_note}

EXISTING {type_label} LESSONS (do not duplicate these):
{chr(10).join(existing) if existing else "None yet"}

Return a JSON array of {quantity} objects:
[
  {{
    "title": "CATCHY ALL-CAPS TITLE (2-4 words, like AMONG US or THE SAUCE)",
    "topic_summary": "One sentence describing what the lesson is about",
    "why_it_fits": "One sentence on why this fits {strand} at {level}",
    "main_task_type": "One of: Design & Create / Debate / Game / Role-Play / Presentation / Tech-Assisted",
    "vocabulary_angle": "What vocabulary area this covers",
    "engagement_hook": "What makes this immediately interesting to 16-18 year olds",
    "search_terms": ["3", "to", "5", "web search terms to research this topic"]
  }}
]

Make all {quantity} topics genuinely different from each other and from existing lessons.
Think about what 16-18 year olds find interesting in 2025: technology, identity, social media,
culture clashes, real-world careers, ethical dilemmas, British life, global issues."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```")
    return json.loads(raw)
