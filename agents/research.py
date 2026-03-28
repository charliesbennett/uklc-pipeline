"""
Research Agent
Takes an approved topic and uses web search to build a structured
research brief: real statistics, vocabulary, examples, activity ideas.
"""
import json
import os
import re
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM = """You are a research assistant for a UKLC EFL lesson designer.
You search the web and compile accurate, current information to help
build engaging lessons for international students aged 16-18.
Return ONLY valid JSON — no markdown, no explanation, no citation tags."""


def _clean_json(text: str) -> str:
    """Aggressively clean text to extract valid JSON."""
    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    # Remove ALL XML/HTML tags including citation tags of any format
    text = re.sub(r'<[^>]*>', '', text)
    # Remove leftover closing tags with slashes
    text = re.sub(r'</[^>]*>', '', text)
    # Find the first { and last } to extract just the JSON object
    start = text.find('{')
    end   = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text.strip()


def run(topic: dict, strand: str, level: str) -> dict:
    """Research a topic and return a structured brief."""
    type_label = {"Language": "LANG", "Leadership": "LEAD", "Culture": "CULT"}.get(strand, strand)
    search_terms = topic.get("search_terms", [topic["title"]])

    prompt = f"""Research this lesson topic and compile a brief for a {strand} lesson at {level} for 16-18 year olds.

TOPIC: {topic['title']}
SUMMARY: {topic['topic_summary']}
MAIN TASK: {topic['main_task_type']}
VOCABULARY ANGLE: {topic.get('vocabulary_angle', '')}

Use web search to find current, real information. Search for: {', '.join(search_terms)}

Return a JSON object with these exact keys:
{{
  "topic_title": "{topic['title']}",
  "key_facts": ["3-5 specific real statistics or facts, engaging to teenagers"],
  "vocabulary_items": [
    {{"word": "term", "definition": "clear simple definition"}},
    "6-8 items total"
  ],
  "gap_fill_sentences": [
    "6 sentences with ___ gap, SCRAMBLED ORDER, answer in brackets: (answer: word)"
  ],
  "discussion_questions": ["5 open questions relevant to 16-18 year olds"],
  "main_task_brief": {{
    "description": "specific collaborative task description",
    "groups": "groups of 3",
    "output": "what they produce or perform",
    "duration_mins": 20
  }},
  "video_suggestion": "specific YouTube search term for a 2-4 minute clip",
  "quiz_questions": [{{"q": "Question?", "a": "Answer"}}, "6-7 items"],
  "hook_image_idea": "very specific opening image description",
  "cultural_notes": "nationality considerations, sensitivity flags, British culture connections"
}}

CRITICAL: Return ONLY the raw JSON object. No prose before or after. No citation tags. No markdown fences."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}]
    )

    # Collect all text blocks from response
    text_parts = [block.text for block in resp.content if hasattr(block, "text")]
    text = " ".join(text_parts).strip()

    # If model only used tools and returned no text, do a synthesis call
    if not text:
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": resp.content},
            {"role": "user", "content": "Now return ONLY the raw JSON object. No prose, no citation tags, no markdown fences. Start your response with { and end with }."}
        ]
        resp2 = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM,
            messages=messages
        )
        text = " ".join(
            block.text for block in resp2.content if hasattr(block, "text")
        ).strip()

    # Log raw text for debugging (first 500 chars)
    print(f"[research] raw response start: {repr(text[:500])}", flush=True)

    cleaned = _clean_json(text)

    # Log cleaned text for debugging
    print(f"[research] cleaned start: {repr(cleaned[:300])}", flush=True)

    return json.loads(cleaned)
