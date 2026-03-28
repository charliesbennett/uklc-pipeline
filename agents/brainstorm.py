"""
Brainstorm Agent
Given settings (strand, level, week, quantity), generates topic ideas
that fill gaps in the existing lesson library.
"""
import json
import os
import re
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


def run(strand: str, level: str, week: str, quantity: int, exclude: list = None) -> list:
    """Generate topic ideas and return a list of topic dicts."""
    type_label = {"Language": "LANG", "Leadership": "LEAD", "Culture": "CULT"}.get(strand, strand)

    # Load existing lessons to avoid duplicates
    existing_titles = []
    if KNOWLEDGE_PATH.exists():
        try:
            with open(KNOWLEDGE_PATH) as f:
                lessons = json.load(f)
            existing_titles = [l.get("lesson_title", "") for l in lessons]
        except Exception:
            pass

    if exclude:
        existing_titles.extend(exclude)

    exclude_block = ""
    if existing_titles:
        exclude_block = f"\nDo NOT suggest topics similar to: {', '.join(existing_titles[:30])}\n"

    prompt = f"""Generate {quantity} fresh topic idea(s) for a PURPOSE {strand} lesson.

SETTINGS:
- Strand: {strand} ({type_label})
- Level: {level}
- Week: {week}
- Quantity needed: {quantity}
{exclude_block}
Return a JSON array of {quantity} topic object(s):
[
  {{
    "title": "SHORT PUNCHY TITLE IN CAPS",
    "topic_summary": "One sentence: what students will do in this lesson.",
    "why_it_fits": "One sentence: why this fits the strand and level.",
    "main_task_type": "Role-Play / Debate / Presentation / Game / Quiz / Group Work",
    "vocabulary_angle": "What vocabulary area this covers",
    "engagement_hook": "What makes this exciting or relevant to 16-18 year olds",
    "search_terms": ["3-5 web search terms to research this topic"]
  }}
]"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)
