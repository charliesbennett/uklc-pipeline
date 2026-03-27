"""
Generator Agent
Takes a research brief and settings, generates a complete lesson JSON.
"""
import json
import os
import re
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


# ── LEARNT FROM 24 REAL LESSONS ─────────────────────────────────────────
# Slide counts: avg 16.5, min 7, max 30
# Typical sequence: content → content → content → content → content → content → content → content → content → content → content → content → content → blank → content → content
# Video placeholder present: 17% of lessons
# Hidden answers present:    4% of lessons
# Warm-up slide present:     29% of lessons
# Reflection at end:         4% of lessons
# Most common ending slide:  content

SYSTEM_PROMPT = """You are an expert EFL curriculum designer for UKLC (UK Language Courses),
a British summer school for international students aged 16–18.

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

LESSON ARC (use the research brief to populate ALL content):
1. Hook (1 slide): Bold image + 1-2 questions from research
2. Warm-up (1 slide): Simple 2-question discussion
3. Info/Context (1-2 slides): Key facts from research brief
4. Vocabulary (1 slide): vocab_items from research
5. Gap-fill (1 slide): gap_fill_sentences from research — SCRAMBLED
6. Video placeholder (1 slide): video_suggestion from research
7. Quiz (1 slide): quiz_questions from research (max 7)
8. Answers (1 slide, hidden): quiz answers
9. Discussion (1 slide): discussion_questions from research (numbered 1-5)
10. Task Setup (1 slide): main_task_brief from research
11. Task Structure (1 slide): how to do the task, NO timestamps
12. Roles/Content (1 slide): character cards or task materials
13. Feedback (1 slide): vote + max 3 criteria → END HERE

CRITICAL RULES:
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
    {{"step_num":4,"title":"[Main Task name]","instructions":"...reference 'the next slide'...practical note for shy students if relevant...","time_mins":20}},
    {{"step_num":5,"title":"Feedback","instructions":"Groups share output. Class votes. Give language feedback. Award points for best performance.","time_mins":6}}
  ],
  "student_slides": [
    {{
      "slide_type": "hook",
      "title": "...",
      "content": "content using research hook_image_idea",
      "image_placeholder": "specific image from research",
      "activity_instruction": "Discuss in pairs - 2 minutes"
    }},
    ... 13-16 slides following the arc above, using ALL research brief content ...
  ],
  "materials_notes": "..."
}}

USE THE RESEARCH BRIEF — every slide should draw on the actual facts, vocabulary,
questions, and task brief from the research. Do not invent generic content."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)
