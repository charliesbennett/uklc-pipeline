"""
Research Agent
Takes an approved topic and uses web search to build a structured
research brief: real statistics, vocabulary, examples, activity ideas.
"""
import json
import os
import re
import time
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM = """You are a research assistant for a UKLC EFL lesson designer.
You search the web and compile accurate, current information to help
build engaging lessons for international students aged 16-18.
Return ONLY valid JSON — no markdown, no explanation, no citation tags."""


def _api_call_with_retry(fn, max_retries=4):
    """Call fn() with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except anthropic.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = 60 * (attempt + 1)
            print(f"[research] Rate limit hit, waiting {wait}s (attempt {attempt+1}/{max_retries})", flush=True)
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code == 429:
                if attempt == max_retries - 1:
                    raise
                wait = 60 * (attempt + 1)
                print(f"[research] 429 error, waiting {wait}s (attempt {attempt+1}/{max_retries})", flush=True)
                time.sleep(wait)
            else:
                raise


def _clean_json(text: str) -> str:
    """Aggressively clean text to extract valid JSON."""
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    # Remove ALL XML/HTML tags (citation tags, antml:cite, etc.)
    text = re.sub(r'<[^>]+>', '', text)
    # Find the first { and last } to extract just the JSON object
    start = text.find('{')
    end   = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text.strip()


def run(topic: dict, strand: str, level: str) -> dict:
    """Research a topic and return a structured brief."""
    search_terms = topic.get("search_terms", [topic["title"]])

    prompt = f"""Research this lesson topic and compile a brief for a {strand} lesson at {level} for 16-18 year olds.

TOPIC: {topic['title']}
SUMMARY: {topic['topic_summary']}
MAIN TASK: {topic['main_task_type']}
VOCABULARY ANGLE: {topic.get('vocabulary_angle', '')}

Search for: {', '.join(search_terms)}

Return ONLY this JSON object — no prose, no citation tags, no markdown:
{{
  "topic_title": "{topic['title']}",
  "key_facts": ["3-5 real statistics or facts engaging to teenagers"],
  "vocabulary_items": [{{"word": "term", "definition": "simple definition"}}, "6-8 items"],
  "gap_fill_sentences": ["6 sentences with ___ gap, SCRAMBLED, (answer: word) at end"],
  "discussion_questions": ["5 open questions relevant to 16-18 year olds"],
  "main_task_brief": {{
    "description": "collaborative task description",
    "groups": "groups of 3",
    "output": "what they produce or perform",
    "duration_mins": 20
  }},
  "video_suggestion": "YouTube search term for 2-4 min clip",
  "quiz_questions": [{{"q": "Question?", "a": "Answer"}}, "6-7 items"],
  "hook_image_idea": "specific opening image description",
  "cultural_notes": "sensitivity flags, British culture connections"
}}"""

    # First call — with web search tool
    resp = _api_call_with_retry(lambda: client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}]
    ))

    text_parts = [block.text for block in resp.content if hasattr(block, "text")]
    text = " ".join(text_parts).strip()
    print(f"[research] raw text length: {len(text)}, start: {repr(text[:200])}", flush=True)

    # If no text, model used tools only — make synthesis call
    if not text:
        resp2 = _api_call_with_retry(lambda: client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": resp.content},
                {"role": "user", "content": "Now output ONLY the JSON object. Start with { and end with }. No other text."}
            ]
        ))
        text = " ".join(
            block.text for block in resp2.content if hasattr(block, "text")
        ).strip()
        print(f"[research] synthesis text start: {repr(text[:200])}", flush=True)

    cleaned = _clean_json(text)
    print(f"[research] cleaned start: {repr(cleaned[:200])}", flush=True)
    return json.loads(cleaned)
