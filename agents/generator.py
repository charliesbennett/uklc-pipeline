"""
UKLC Pipeline — Generator Agent
Produces a full lesson JSON (structural metadata + 13 student slides) from a research brief.
Includes retry logic with exponential backoff for rate limit handling.
"""

import json
import re
import time

import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are an expert EFL lesson designer for UKLC (UK Language Centres).
You create engaging, communicative lessons for international teenage students aged 13–17
at B1–B2 level (CEFR), studying English in the UK during summer programmes.

Your lessons follow the PURPOSE framework:
- Purposeful: every activity has a clear communicative goal
- Upbeat: energetic, fun, student-centred
- Real: authentic topics and language
- Personalized: students bring their own views and experiences
- Original: creative, memorable tasks
- Structured: clear arc from hook to reflection
- Engaging: variety of activity types, short sharp tasks

Output ONLY valid JSON — no markdown fences, no preamble, no commentary."""

LESSON_PROMPT = """Using the research brief below, generate a complete PURPOSE lesson JSON.

RESEARCH BRIEF:
{research_json}

Generate a lesson with EXACTLY this JSON structure:

{{
  "lesson_title": "TITLE IN CAPS (max 5 words, punchy)",
  "lesson_type_label": "LANG" or "LEAD" or "CULT",
  "level_label": "Level 2" or "Level 3",
  "week": "A" or "B",
  "lesson_focus": "2-3 sentence description of what students learn",
  "objectives": "By the end of the lesson, students will be able to...",
  "extra_materials": "Any props, cards, or printed materials needed (or 'None.')",
  "materials_notes": "Brief notes for the teacher about materials preparation",
  "teacher_steps": [
    {{
      "step_num": 1,
      "title": "Step title",
      "instructions": "Clear teacher instructions for this step",
      "time_mins": 5
    }}
  ],
  "student_slides": [
    {{
      "slide_type": "hook",
      "title": "Slide title",
      "content": "Main content text",
      "activity_instruction": "What students do",
      "image_placeholder": "Description of ideal image"
    }}
  ]
}}

STRICT 13-SLIDE ARC — student_slides must follow this EXACT sequence:
1.  hook          — Topic hook, image-led, provocative question
2.  vocab_intro   — 6-8 key words/phrases with definitions
3.  vocab_practice — Gap fill, matching, or example sentences
4.  info          — Key facts, stats, or background on the topic
5.  reading       — Short text (150-200 words) with 3-4 comprehension questions
6.  discussion    — 5-6 discussion questions, increasingly challenging
7.  grammar_focus — Target grammar point with examples
8.  gap_fill      — Grammar practice activity
9.  task_setup    — Instructions for the main communicative task
10. task_content  — Content/stimulus for the main task
11. pair_work     — Pair/group speaking activity
12. game          — Fun review game (quiz, ranking, debate, etc.)
13. reflection    — 3-4 reflection prompts on learning and opinions

TEACHER STEPS must have exactly 5 steps covering: Warmer, Input, Practice, Main Task, Feedback/Reflection.
Total time_mins across all steps must equal 60.

IMPORTANT RULES:
- lesson_type_label: LANG=language focus, LEAD=leadership/life skills, CULT=British culture
- level_label: Level 2=B1, Level 3=B2
- All content must be appropriate for ages 13-17
- Keep content British where possible (spellings, references, context)
- activity_instruction should be a clear, student-facing instruction
- content should be substantive — not just a title
- image_placeholder should describe a specific, visualisable image
- Do NOT include slide numbers in title fields
- Output ONLY the JSON object, nothing else"""


def _clean_json(text: str) -> str:
    """Strip markdown fences, leading/trailing whitespace, and common artifacts."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # Remove citation tags that Claude sometimes adds
    text = re.sub(r'</?antml:cite[^>]*>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def generate_lesson(research: dict, retries: int = 4) -> dict | None:
    """
    Generate a full lesson JSON from a research brief.
    Returns the lesson dict, or None if all retries are exhausted.
    """
    research_json = json.dumps(research, ensure_ascii=False, indent=2)
    prompt = LESSON_PROMPT.format(research_json=research_json)

    wait_times = [60, 120, 180, 240]

    for attempt in range(retries):
        try:
            print(f'[generator] generating lesson for: {research.get("topic_title", "unknown")} (attempt {attempt + 1}/{retries})')

            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            raw_text = response.content[0].text
            print(f'[generator] raw response length: {len(raw_text)}')

            cleaned = _clean_json(raw_text)
            lesson = json.loads(cleaned)

            # Validate slide count
            slides = lesson.get('student_slides', [])
            print(f'[generator] generated {len(slides)} student slides')
            if len(slides) > 16:
                lesson['student_slides'] = slides[:16]
                print(f'[generator] capped slides to 16')

            return lesson

        except anthropic.RateLimitError:
            if attempt < retries - 1:
                wait = wait_times[attempt]
                print(f'[generator] Rate limit hit, waiting {wait}s (attempt {attempt + 1}/{retries})')
                time.sleep(wait)
            else:
                print(f'[generator] Rate limit hit on final attempt — giving up')
                return None

        except json.JSONDecodeError as e:
            print(f'[generator] JSON parse error: {e}')
            print(f'[generator] cleaned text start: {cleaned[:200] if "cleaned" in dir() else "N/A"}')
            if attempt < retries - 1:
                wait = wait_times[attempt]
                print(f'[generator] Retrying in {wait}s...')
                time.sleep(wait)
            else:
                return None

        except Exception as e:
            print(f'[generator] Unexpected error: {e}')
            if attempt < retries - 1:
                wait = wait_times[attempt]
                print(f'[generator] Retrying in {wait}s...')
                time.sleep(wait)
            else:
                return None

    return None
