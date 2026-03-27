"""
Research Agent
Takes an approved topic and uses web search to build a structured
research brief: real statistics, vocabulary, examples, activity ideas.
"""
import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM = """You are a research assistant for a UKLC EFL lesson designer.
You search the web and compile accurate, current information to help
build engaging lessons for international students aged 16–18.
Return ONLY valid JSON — no markdown, no explanation."""


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

Return a JSON object:
{{
  "topic_title": "{topic['title']}",
  "key_facts": [
    "3-5 specific, surprising, or striking REAL statistics or facts about this topic",
    "These will appear on the info/context slide",
    "Must be current (2022-2025 where possible) and engaging to teenagers"
  ],
  "vocabulary_items": [
    {{"word": "...", "definition": "Clear, simple definition a B1-C1 student can understand"}},
    "...6-8 items total..."
  ],
  "gap_fill_sentences": [
    "6 sentences using the vocabulary, SCRAMBLED ORDER (not 1-2-3-4-5-6), each with ___ for the missing word",
    "Include the answer in brackets at the end: (answer: word)"
  ],
  "discussion_questions": [
    "5 open questions genuinely relevant to 16-18 year olds",
    "Must feel personal and spark debate, not textbook-generic"
  ],
  "main_task_brief": {{
    "description": "Specific description of the main collaborative task",
    "groups": "groups of 3",
    "output": "What tangible thing they produce or perform",
    "duration_mins": 20
  }},
  "video_suggestion": "Specific YouTube search term to find a relevant 2-4 minute clip",
  "quiz_questions": [
    {{"q": "Question?", "a": "Answer"}},
    "...6-7 items..."
  ],
  "hook_image_idea": "Very specific description of the ideal opening image",
  "cultural_notes": "Any UKLC-specific notes: nationality considerations, sensitivity flags, British culture connections"
}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}]
    )

    # Extract text content from response (may have tool use blocks)
    text = ""
    for block in resp.content:
        if hasattr(block, "text"):
            text += block.text

    # If no text yet (model used tool), make a follow-up without tools to synthesise
    if not text.strip():
        # Build a synthesis call with the search results
        messages = [{"role": "user", "content": prompt}]
        for block in resp.content:
            if block.type == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({"role": "user", "content": "Now compile the research brief as JSON based on your search results."})
                break

        resp2 = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM,
            messages=messages
        )
        text = resp2.content[0].text

    raw = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(raw)
