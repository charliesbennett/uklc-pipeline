"""
Brainstorm Agent
Given settings (strand, level, week, quantity), generates topic ideas
that fill gaps in the existing lesson library.
"""
import json
import os
import re
import time
from pathlib import Path
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
KNOWLEDGE_PATH = Path(__file__).parent.parent / "knowledge" / "lessons.json"

SYSTEM = """You are an expert EFL curriculum designer for UKLC (UK Language Courses).
PURPOSE programme: ages 16-18, British summer school.
Your job is to brainstorm fresh lesson topic ideas that:
1. Don't duplicate existing lessons
2. Fill genuine gaps in the curriculum
3. Are engaging and relevant to 16-18 year old international students
4. Match the strand's purpose:
   - CULT (Culture): British culture, CLIL, history, arts, sciences
   - LANG (Language): vocabulary, grammar, functional language, skills
   - LEAD (Leadership): entrepreneurship, teamwork, technology, 21st century skills
5. Are practical to teach in 60 minutes with no special equipment

Return ONLY valid JSON — no markdown, no explanation."""


def _api_call_with_retry(fn, max_retries=4):
    """Call fn() with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except anthropic.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = 60 * (attempt + 1)
            print(f"[brainstorm] Rate limit hit, waiting {wait}s (attempt {attempt+1}/{max_retries})", flush=True)
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code == 429:
                if attempt == max_retries - 1:
                    raise
                wait = 60 * (attempt + 1)
                print(f"[brainstorm] 429 error, waiting {wait}s (attempt {attempt+1}/{max_retries})", flush=True)
                time.sleep(wait)
            else:
                raise


def _load_existing_titles():
    if KNOWLEDGE_PATH.exists():
        try:
            with open(KNOWLEDGE_PATH) as f:
                return [l.get("lesson_title", "") for l in json.load(f)]
        except Exception:
            pass
    return []


def run(strand: str, level: str, week: str, quantity: int, exclude: list = None) -> list:
    """Generate topic ideas and return a list of topic dicts."""
    type_label = {"Language": "LANG", "Leadership": "LEAD", "Culture": "CULT"}.get(strand, strand)
    existing_titles = _load_existing_titles()
    if exclude:
        existing_titles.extend(exclude)
    exclude_block = f"\nDo NOT suggest topics similar to: {', '.join(existing_titles[:30])}\n" if existing_titles else ""

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

    resp = _api_call_with_retry(lambda: client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    ))
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


def make_from_prompt(title: str, context: str, strand: str, level: str, week: str) -> dict:
    """Turn a user-supplied topic title + context into a full topic dict."""
    type_label = {"Language": "LANG", "Leadership": "LEAD", "Culture": "CULT"}.get(strand, strand)

    prompt = f"""A teacher wants to create a PURPOSE {strand} lesson on the following topic.
Complete the topic profile so it can go through the lesson pipeline.

TEACHER INPUT:
- Title: {title}
- Context / notes: {context or 'None provided'}

LESSON SETTINGS:
- Strand: {strand} ({type_label})
- Level: {level}
- Week: {week}

Return a single JSON object:
{{
  "title": "{title.upper()}",
  "topic_summary": "One sentence: what students will do in this lesson.",
  "why_it_fits": "One sentence: why this fits the strand and level.",
  "main_task_type": "Role-Play / Debate / Presentation / Game / Quiz / Group Work",
  "vocabulary_angle": "What vocabulary area this covers",
  "engagement_hook": "What makes this exciting or relevant to 16-18 year olds",
  "search_terms": ["3-5 web search terms to research this topic"]
}}"""

    resp = _api_call_with_retry(lambda: client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    ))
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)
