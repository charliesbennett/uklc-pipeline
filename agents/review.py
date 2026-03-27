"""
Review Agent
Reads a generated lesson, checks it against Charlie's patterns,
and automatically fixes any issues found.
"""
import json
import os
import re
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

REVIEW_RULES = """
CHARLIE'S LESSON QUALITY RULES — check ALL of these:

STRUCTURE:
- Must NOT end with a reflection or writing task slide — remove them
- Must have a teacher plan (teacher_steps) with exactly 5 steps
- Must have a video_placeholder slide
- Must have an answers_hidden slide after any quiz slide
- Must have at least one gap_fill slide with SCRAMBLED sentences
- Must have a discussion slide with questions numbered 1-5 (not bullets)
- Must have a feedback slide as the LAST student slide
- Minimum 13 student slides, maximum 20

CONTENT QUALITY:
- Lesson focus must be ONE sentence starting with a gerund
- Objectives must have exactly 2 outcomes (not 3+)
- Teacher instructions must say "the next slide" not "Slide 6" etc.
- Gap-fill sentences must be scrambled (not in sequential order 1,2,3,4,5,6)
- Quiz slides must have max 7 items (trim if more)
- Task structure slides must NOT contain timestamps like "0:00-0:15"
- Feedback slide must have max 3 criteria
- Activity instructions on student slides must be SHORT (1 sentence max)
- Discussion questions should feel personally relevant to 16-18 year olds

LANGUAGE LEVEL:
- Level 1/2 (A1-B1): Simpler vocabulary, sentence frames provided
- Level 3/4 (B2-C2): More complex/nuanced language, idioms OK, less scaffolding

Return ONLY valid JSON — no markdown, no explanation."""


def run(lesson: dict) -> dict:
    """Review and auto-fix a lesson. Returns the corrected lesson JSON."""

    # First pass: automated checks we can do without Claude
    lesson = _auto_fix_structure(lesson)

    # Second pass: Claude reviews and fixes content quality
    prompt = f"""Review this lesson plan and fix ALL issues you find according to the rules.

LESSON:
{json.dumps(lesson, indent=2)}

ISSUES TO CHECK AND FIX:
1. Remove any reflection or writing task slides at the end
2. Ensure lesson ends with a feedback slide
3. Ensure gap_fill sentences are SCRAMBLED (if they look sequential, reorder them)
4. Remove timestamps from task structure slides (e.g. "0:00-0:15")
5. Ensure discussion questions are numbered 1,2,3,4,5 in the content
6. Trim quiz items to max 7 if there are more
7. Ensure feedback slide has max 3 criteria
8. Ensure lesson_focus is one gerund sentence
9. Ensure objectives has exactly 2 outcomes
10. Ensure teacher instructions say "the next slide" not specific slide numbers
11. Ensure activity_instruction on each slide is 1 short sentence
12. Ensure there is an answers_hidden slide after any quiz slide
13. Ensure there is a video_placeholder slide

Return the COMPLETE corrected lesson as JSON with the same structure.
Fix everything — do not just flag issues."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=REVIEW_RULES,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


def _auto_fix_structure(lesson: dict) -> dict:
    """Fast structural fixes without Claude."""
    slides = lesson.get("student_slides", [])

    # Remove trailing reflection/writing slides
    while slides and slides[-1].get("slide_type") in ("reflection", "writing"):
        slides.pop()

    # Ensure feedback slide is last
    if slides and slides[-1].get("slide_type") != "group_work":
        has_feedback = any(s.get("slide_type") == "group_work" and
                          ("feedback" in s.get("title", "").lower() or
                           "vote" in s.get("content", "").lower())
                          for s in slides)
        if not has_feedback:
            slides.append({
                "slide_type": "group_work",
                "title": "Pitch Feedback",
                "content": "After each group presents:\n\nVOTE: Would you buy / try / use this?\nSTAR: What was the most effective moment?\nSUGGESTION: One thing that could make it stronger",
                "image_placeholder": "Audience voting graphic",
                "activity_instruction": "Be honest — explain your vote"
            })

    # Cap quiz slides at 7 items
    for slide in slides:
        if slide.get("slide_type") == "quiz":
            lines = slide.get("content", "").split("\n")
            q_lines = [l for l in lines if re.match(r"^(Q\d|Round \d|\d+\.|\d+:)", l.strip())]
            if len(q_lines) > 7:
                # Keep first 7 quiz lines + any non-question lines (headers etc)
                non_q = [l for l in lines if not re.match(r"^(Q\d|Round \d|\d+\.|\d+:)", l.strip())]
                slide["content"] = "\n".join(non_q[:2] + q_lines[:7])

    lesson["student_slides"] = slides
    return lesson
