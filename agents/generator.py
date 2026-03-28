"""
Generator Agent
Takes a research brief and settings, generates a complete lesson JSON.
"""
import json
import os
import re
import time
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _api_call_with_retry(fn, max_retries=4):
    """Call fn() with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except anthropic.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = 60 * (attempt + 1)
            print(f"[generator] Rate limit hit, waiting {wait}s (attempt {attempt+1}/{max_retries})", flush=True)
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code == 429:
                if attempt == max_retries - 1:
                    raise
                wait = 60 * (attempt + 1)
                print(f"[generator] 429 error, waiting {wait}s (attempt {attempt+1}/{max_retries})", flush=True)
                time.sleep(wait)
            else:
                raise


SYSTEM_PROMPT = """You are an expert EFL curriculum designer for UKLC (UK Language Courses),
a British summer school for international students aged 16-18.

PURPOSE PROGRAMME CONTEXT:
- Ages 16-18, global citizens, maturing young adults
- 4 levels: Level 1 (A1-A2), Level 2 (B1), Level 3 (B2-C1), Level 4 (C1-C2)
- 3 strands: Language (LANG), Leadership (LEAD), Culture (CULT)
- Students: Italian, French, Spanish, Turkish, Chinese etc. on a UK summer course

UKLC METHODOLOGY: Communication-first. Student-centred. Inductive grammar.
Personalisation. Context always. Confidence-building.
ELT shorthand: Ss, CCQs, ICQs, elicit, monitor, drill.

CHARLIE'S STYLE: Task-based learning. Communicative approach. Visual and interactive.
Students practise English while learning transferable life skills. Fun, relevant topics.
Practical tasks. Discussion-heavy. Groups of 3 as default.

LESSON ARC — follow this EXACTLY, one slide per step (13 slides total):
1. Hook (1 slide): Bold image + 1-2 questions from research
2. Warm-up (1 slide): Simple 2-question discussion
3. Info/Context (1 slide): Key facts from research brief
4. Vocabulary (1 slide): vocab_items from research
5. Gap-fill (1 slide): gap_fill_sentences from research — SCRAMBLED
6. Video placeholder (1 slide): video_suggestion from research
7. Quiz (1 slide): quiz_questions from research (max 7)
8. Answers (1 slide, hidden): quiz answers
9. Discussion (1 slide): discussion_questions from research (numbered 1-5)
10. Task Setup (1 slide): main_task_brief from research
11. Task Structure (1 slide): how to do the task, NO timestamps
12. Roles/Content (1 slide): character cards or task materials
13. Feedback (1 slide): vote + max 3 criteria

CRITICAL RULES:
- student_slides MUST contain EXACTLY 13 slides — no more, no fewer
- Each slide maps to exactly one step in the arc above
- Do NOT add extra slides, do NOT combine steps, do NOT split steps
- Gap-fill MUST be scrambled (not sequential)
- Games/quizzes: maximum 7 items
- NO timestamps (0:00-0:15) on task structure slides
- NO reflection slide, NO writing task at the end
- Lesson Focus: 1 sentence, gerund-led
- Objectives: 2 simple outcomes only
- Teacher instructions: say "the next slide" not "Slide 6"
- Feedback: max 3 criteria

Return ONLY valid JSON — no markdown, no explanation."""


def run(topic: dict, research: dict, strand: str, level: str, week: str) -> dict:
    """Generate full lesson JSON from a research brief."""
    type_label = {"Language": "LANG", "Leadership": "LEAD", "Culture": "CULT"}.get(strand, strand)

    prompt = f"""Generate a complete PURPOSE lesson plan using this research brief.

SETTINGS:
- Title: {topic['title']}
- Strand: {strand} ({type_label})
- Level: {level}
- Week: {week}
- Main task type: {topic.get('main_task_type', 'Group Work')}

RESEARCH BRIEF:
{json.dumps(research, indent=2)}

Return a JSON object:
{{
  "lesson_title": "{topic['title']}",
  "lesson_type_label": "{type_label}",
  "level_label": "{level}",
  "week": "{week}",
  "lesson_focus": "One gerund-led sentence using research context.",
  "objectives": "By the end of the lesson, students will be able to [2 specific outcomes].",
  "extra_materials": "Specific materials or 'None.'",
  "teacher_steps": [
    {{"step_num":1,"title":"Introduction","instructions":"Introduce the topic by activating Ss' schemata. Show the image on the next slide and ask the questions. Let Ss discuss in pairs for 2 minutes, then take whole-class feedback.","time_mins":5}},
    {{"step_num":2,"title":"[Input phase name]","instructions":"...using 'the next slide'...","time_mins":12}},
    {{"step_num":3,"title":"[Practice phase]","instructions":"...","time_mins":12}},
    {{"step_num":4,"title":"[Main Task name]","instructions":"...reference 'the next slide'...","time_mins":20}},
    {{"step_num":5,"title":"Feedback","instructions":"Groups share output. Class votes. Give language feedback.","time_mins":6}}
  ],
  "student_slides": [
    {{"slide_type":"hook","title":"...","content":"Two questions using research context","image_placeholder":"specific image description","activity_instruction":"Discuss in pairs - 2 minutes"}},
    {{"slide_type":"info","title":"Warm Up","content":"Two simple discussion questions","activity_instruction":"Talk to your partner"}},
    {{"slide_type":"info","title":"Did You Know?","content":"3-4 key facts from research brief","activity_instruction":null}},
    {{"slide_type":"vocab_intro","title":"Vocabulary","content":"word: definition\\nword: definition\\n...","activity_instruction":"Match the words to the definitions"}},
    {{"slide_type":"gap_fill","title":"Gap Fill","content":"Scrambled gap fill sentences from research","activity_instruction":"Complete the sentences"}},
    {{"slide_type":"video_placeholder","title":"Video","content":"Watch the video. What do you notice?","activity_instruction":null}},
    {{"slide_type":"quiz","title":"Quiz Time!","content":"Q1: ...\\nQ2: ...\\n... (max 7 questions)","activity_instruction":"Answer in your teams"}},
    {{"slide_type":"answers_hidden","title":"Answers","content":"1. answer\\n2. answer\\n...","activity_instruction":null}},
    {{"slide_type":"discussion","title":"Discussion","content":"1. question\\n2. question\\n3. question\\n4. question\\n5. question","activity_instruction":"Discuss in groups of 3"}},
    {{"slide_type":"task_setup","title":"[Task Name]","content":"Task brief from research","activity_instruction":"You have 15 minutes"}},
    {{"slide_type":"group_work","title":"How It Works","content":"Step-by-step task instructions (no timestamps)","activity_instruction":null}},
    {{"slide_type":"task_content","title":"Your Materials","content":"Character cards / scenario cards from task brief","activity_instruction":null}},
    {{"slide_type":"reflection","title":"Feedback","content":"Which group did best?\\nCriteria 1\\nCriteria 2\\nCriteria 3","activity_instruction":"Vote for the best group"}}
  ],
  "materials_notes": "..."
}}

IMPORTANT: student_slides must contain EXACTLY 13 slides.
USE THE RESEARCH BRIEF — every slide must draw on the actual content from the research."""

    resp = _api_call_with_retry(lambda: client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    ))

    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    lesson = json.loads(raw)

    # Safety cap
    if len(lesson.get('student_slides', [])) > 16:
        lesson['student_slides'] = lesson['student_slides'][:16]

    return lesson
