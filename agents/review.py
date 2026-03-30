"""
Review Agent
Reads a generated lesson, checks it against UKLC PURPOSE patterns,
and automatically fixes any issues found.
"""
import json
import os
import re
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

REVIEW_RULES = """
UKLC PURPOSE LESSON QUALITY RULES — check ALL of these:

STRUCTURE:
- Must have EXACTLY 13 student slides (trim or flag if different)
- Must end with a 'game' slide — NEVER reflection, writing, or feedback
- Must NOT have a reflection or writing slide anywhere
- Must have a video_placeholder slide (slide 5 in the arc)
- Must have exactly 5 teacher_steps totalling exactly 60 minutes
- Slide arc must follow: hook, vocab_intro, vocab_practice, info, video_placeholder,
  reading, discussion, grammar_focus, gap_fill, task_setup, task_content, pair_work, game

CONTENT QUALITY:
- hook slide: exactly 2 warm-up questions, no more
- vocab_intro: 6-8 items maximum
- gap_fill: sentences must be scrambled/jumbled — NOT simple fill-in-the-blank
- discussion: exactly 5 questions numbered 1-5, starting factual, building to opinion
- game slide: maximum 7 items
- task_setup: bullet points only, max 4 bullets, one action per bullet
- No timestamps (e.g. "0:00-0:15") anywhere in content
- activity_instruction on every slide must be 1 short sentence max
- Teacher instructions must reference "the next slide" not specific slide numbers
- All content appropriate for ages 16-18, mixed-nationality classroom

LESSON METADATA:
- lesson_focus: 2-3 sentences describing topic angle and skill focus
- objectives: exactly 3 measurable outcomes starting "By the end of the lesson..."
- lesson_type_label: must be "LANG", "LEAD", or "CULT" only
- level_label: must be "Level 2" or "Level 3" only
- week: must be "A" or "B" only

Return ONLY valid JSON — no markdown, no explanation."""


def run(lesson: dict) -> dict:
    """Review and auto-fix a lesson. Returns the corrected lesson JSON."""

    # First pass: fast structural fixes without Claude
    lesson = _auto_fix_structure(lesson)

    # Second pass: Claude fixes content quality
    prompt = f"""Review this lesson plan and fix ALL issues according to the rules.

LESSON:
{json.dumps(lesson, indent=2)}

FIX ALL OF THE FOLLOWING:
1. Ensure student_slides has exactly 13 slides in the correct arc order:
   hook, vocab_intro, vocab_practice, info, video_placeholder, reading,
   discussion, grammar_focus, gap_fill, task_setup, task_content, pair_work, game
2. Ensure slide 13 is a game slide — never reflection, writing, or feedback
3. Ensure hook slide has exactly 2 questions in content
4. Ensure vocab_intro has max 8 items
5. Ensure gap_fill sentences are scrambled/jumbled, not simple blanks
6. Ensure discussion has exactly 5 questions numbered 1-5
7. Ensure game slide has max 7 items
8. Ensure task_setup has max 4 bullet points
9. Remove any timestamps like "0:00-0:15" from content
10. Ensure every activity_instruction is 1 short sentence
11. Ensure teacher_steps has exactly 5 steps totalling 60 minutes
12. Ensure teacher instructions say "the next slide" not slide numbers

Return the COMPLETE corrected lesson as JSON with the same structure.
Fix everything — do not just flag issues."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8096,
        system=REVIEW_RULES,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # If Claude's response is malformed, return the auto-fixed version
        print('[review] JSON parse error on Claude response — returning auto-fixed lesson')
        return lesson


def _auto_fix_structure(lesson: dict) -> dict:
    """Fast structural fixes without Claude."""
    slides = lesson.get("student_slides", [])

    # Remove trailing reflection/writing slides
    while slides and slides[-1].get("slide_type") in ("reflection", "writing", "feedback"):
        slides.pop()

    # Cap at 16 slides
    if len(slides) > 16:
        slides = slides[:16]

    # Ensure last slide is a game — if not, swap the last slide type
    if slides and slides[-1].get("slide_type") != "game":
        # Check if there's a game slide elsewhere we can move to end
        game_indices = [i for i, s in enumerate(slides) if s.get("slide_type") == "game"]
        if game_indices:
            game_slide = slides.pop(game_indices[-1])
            slides.append(game_slide)
        else:
            # Convert last slide to a game if no game exists
            slides[-1]["slide_type"] = "game"

    # Cap game slides at 7 items
    for slide in slides:
        if slide.get("slide_type") == "game":
            lines = [l for l in slide.get("content", "").split("\n") if l.strip()]
            if len(lines) > 7:
                slide["content"] = "\n".join(lines[:7])

    # Cap vocab slides at 8 items
    for slide in slides:
        if slide.get("slide_type") in ("vocab_intro", "vocab_practice"):
            lines = [l for l in slide.get("content", "").split("\n") if l.strip()]
            if len(lines) > 8:
                slide["content"] = "\n".join(lines[:8])

    # Remove timestamps from all content
    for slide in slides:
        if "content" in slide:
            slide["content"] = re.sub(r'\d+:\d{2}[-–]\d+:\d{2}', '', slide["content"])

    # Ensure teacher_steps times sum to 60
    steps = lesson.get("teacher_steps", [])
    if steps:
        total = sum(s.get("time_mins", 0) for s in steps)
        if total != 60 and len(steps) == 5:
            diff = 60 - total
            steps[-1]["time_mins"] = steps[-1].get("time_mins", 0) + diff

    lesson["student_slides"] = slides
    lesson["teacher_steps"] = steps
    return lesson
