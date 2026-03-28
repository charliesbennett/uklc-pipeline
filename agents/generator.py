"""
UKLC Pipeline — Generator Agent
"""
import json, re, time
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are an expert EFL lesson designer for UKLC (UK Language Centres).
You create engaging, communicative lessons for international teenage students aged 13-17
at B1-B2 level (CEFR), studying English in the UK during summer programmes.
Output ONLY valid JSON - no markdown fences, no preamble, no commentary."""

LESSON_PROMPT = """Using the research brief below, generate a complete PURPOSE lesson JSON.

RESEARCH BRIEF:
{research_json}

Output a JSON object with these exact keys:
- lesson_title: CAPS, max 5 words
- lesson_type_label: "LANG", "LEAD", or "CULT"
- level_label: "Level 2" or "Level 3"
- week: "A" or "B"
- lesson_focus: 2-3 sentences
- objectives: "By the end of the lesson, students will be able to..."
- extra_materials: props/cards needed, or "None."
- materials_notes: teacher prep notes
- teacher_steps: array of 5 objects with step_num, title, instructions, time_mins (total=60)
- student_slides: array of EXACTLY 13 objects with slide_type, title, content, activity_instruction, image_placeholder

STRICT 13-SLIDE ARC:
1. hook, 2. vocab_intro, 3. vocab_practice, 4. info, 5. reading,
6. discussion, 7. grammar_focus, 8. gap_fill, 9. task_setup,
10. task_content, 11. pair_work, 12. game, 13. reflection

Output ONLY the JSON object, nothing else."""


def _clean_json(text):
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def generate_lesson(research, retries=4):
    research_json = json.dumps(research, ensure_ascii=False, indent=2)
    prompt = LESSON_PROMPT.format(research_json=research_json)
    wait_times = [60, 120, 180, 240]

    for attempt in range(retries):
        try:
            print(f'[generator] generating: {research.get("topic_title", "unknown")} (attempt {attempt+1}/{retries})')
            response = client.messages.create(
                model=MODEL, max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.content[0].text
            cleaned = _clean_json(raw_text)
            lesson = json.loads(cleaned)
            slides = lesson.get('student_slides', [])
            print(f'[generator] got {len(slides)} slides')
            if len(slides) > 16:
                lesson['student_slides'] = slides[:16]
            return lesson

        except anthropic.RateLimitError:
            if attempt < retries - 1:
                wait = wait_times[attempt]
                print(f'[generator] Rate limit hit, waiting {wait}s (attempt {attempt+1}/{retries})')
                time.sleep(wait)
            else:
                print('[generator] Rate limit hit on final attempt — giving up')
                return None

        except (json.JSONDecodeError, Exception) as e:
            print(f'[generator] Error: {e}')
            if attempt < retries - 1:
                time.sleep(wait_times[attempt])
            else:
                return None

    return None
