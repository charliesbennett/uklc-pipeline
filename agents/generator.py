"""
UKLC Pipeline — Generator Agent
Produces a full lesson JSON (structural metadata + 13 student slides) from a research brief.
Includes retry logic with exponential backoff for rate limit handling.
"""
import json, re, time
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are an expert EFL lesson designer for UKLC (UK Language Centres).
You create engaging, communicative lessons for international teenage students aged 16-18
at B1-B2 level (CEFR), studying English in the UK during summer programmes.

UKLC PURPOSE LESSON PRINCIPLES:
- Lessons are 60 minutes, student-centred, communicative
- Students work in groups of 3 as the default grouping
- Activities are fast-paced with short, punchy instructions
- Every slide has a clear communicative purpose — no filler
- British English spellings and references throughout
- Content must be appropriate for mixed-nationality classrooms

CRITICAL LESSON PATTERN RULES (from analysis of real UKLC lessons):
- Warm-up: exactly 2 questions, image-led, no more
- No writing activities or reflection slides at the end — end on energy (game or task)
- Video slides: include a video_placeholder slide with watch instructions, never describe the video content
- Gap-fills: always use scrambled/jumbled sentences, not simple blanks
- Games: cap items at 7 maximum — never more
- Feedback: maximum 3 criteria when giving peer/group feedback
- Discussion questions: 5-6 questions, start easy, build to challenging
- Vocab: 6-8 target items maximum per vocab slide
- Reading texts: 150-200 words, always followed by 3-4 comprehension questions
- Task instructions: one clear action per bullet point, max 4 bullets

STRAND GUIDANCE:
- CULT lessons: anchor everything to British culture, history, or identity; use British examples
- LEAD lessons: frame around a real skill or decision; include a role-play or group challenge
- LANG lessons: identify a clear vocabulary set and grammar point; make language the star

Output ONLY valid JSON — no markdown fences, no preamble, no commentary."""

LESSON_PROMPT = """Using the research brief below, generate a complete PURPOSE lesson JSON.

RESEARCH BRIEF:
{research_json}

Generate a JSON object with EXACTLY these keys:

{{
  "lesson_title": "PUNCHY TITLE IN CAPS — max 5 words",
  "lesson_type_label": "LANG" | "LEAD" | "CULT",
  "level_label": "Level 2" | "Level 3",
  "week": "A" | "B",
  "lesson_focus": "2-3 sentences describing the topic angle and language/skill focus",
  "objectives": "By the end of the lesson, students will be able to [3 specific, measurable outcomes]",
  "extra_materials": "Specific props, printed cards, or handouts needed — or 'None.'",
  "materials_notes": "Brief teacher prep note — what to prepare before class",
  "teacher_steps": [5 step objects — see format below],
  "student_slides": [13 slide objects — see format and arc below]
}}

TEACHER STEPS FORMAT — exactly 5 steps, time_mins must total 60:
{{
  "step_num": 1,
  "title": "Step name",
  "instructions": "Clear teacher instructions. What to say, what to show, how to manage the class.",
  "time_mins": 10
}}

Steps should follow: Warmer (5 min) -> Input/Presentation (15 min) -> Practice (15 min) -> Main Task (20 min) -> Feedback & Close (5 min)

STUDENT SLIDES — EXACTLY 13 slides in this order:

Slide 1 — hook
  Purpose: Grab attention. Image-led. Exactly 2 warm-up questions.
  content: Exactly 2 questions about the image or topic. No more.
  activity_instruction: "Look at the image. Discuss the questions with your group."
  image_placeholder: Specific, vivid description of the ideal image.

Slide 2 — vocab_intro
  Purpose: Introduce 6-8 target words/phrases with definitions.
  content: List of "WORD — definition" pairs. Max 8 items.
  activity_instruction: "Match the words to the definitions. Then test your partner."

Slide 3 — vocab_practice
  Purpose: Practise target vocab in context.
  content: 6 scrambled/jumbled sentences using target vocabulary. Label as 1-6.
  activity_instruction: "Unjumble the sentences. Then check with your group."

Slide 4 — info
  Purpose: Build topic knowledge with real facts.
  content: 5-6 punchy facts or statistics from the research brief. Use bullet points.
  activity_instruction: "Read the facts. Which surprises you most? Tell your group."

Slide 5 — video_placeholder
  Purpose: Teacher-embedded video break. DO NOT describe video content.
  content: "Watch the video carefully.\\n\\nAs you watch, think about:\\n- [Question 1]\\n- [Question 2]\\n- [Question 3]"
  activity_instruction: "Your teacher will play a video. Note down your answers."
  image_placeholder: ""

Slide 6 — reading
  Purpose: Authentic-style reading text with comprehension.
  content: A 150-200 word reading text on the topic, followed by:\\nQuestions:\\n1. [question]\\n2. [question]\\n3. [question]\\n4. [question]
  activity_instruction: "Read the text. Answer the questions. Compare with your partner."

Slide 7 — discussion
  Purpose: Communicative discussion, building to opinion.
  content: Exactly 5 questions. Start factual, build to personal opinion. Number them 1-5.
  activity_instruction: "Discuss the questions in your group. Be ready to share your best answer."

Slide 8 — grammar_focus
  Purpose: Present target grammar point in context of topic.
  content: Grammar rule + 3 clear examples from the topic context. Label the grammar point.
  activity_instruction: "Study the grammar. Can you make your own example sentence?"

Slide 9 — gap_fill
  Purpose: Grammar practice with scrambled sentences.
  content: 6 gap-fill sentences using the target grammar. Provide a word box.
  activity_instruction: "Complete the sentences using words from the box."

Slide 10 — task_setup
  Purpose: Set up the main communicative task clearly.
  content: Task instructions as bullet points. Max 4 bullets. One action per bullet.
  activity_instruction: "Read the instructions carefully before you start."

Slide 11 — task_content
  Purpose: Provide the stimulus or content for the main task.
  content: The cards, scenarios, data, or prompts students need for the task.
  activity_instruction: "Use this information to complete your task."

Slide 12 — pair_work
  Purpose: Structured speaking task between pairs or groups.
  content: A clear roleplay scenario OR a set of conversation prompts. Max 4 items.
  activity_instruction: "Work in pairs. Student A is [role]. Student B is [role]. Swap after 3 minutes."

Slide 13 — game
  Purpose: High-energy review game. End on a high — NO reflection here.
  content: Game content — quiz questions, ranking items, or challenge prompts. MAX 7 items.
  activity_instruction: "Play the game in your group. Your teacher will explain the rules."

FINAL CHECKS before outputting:
- student_slides has EXACTLY 13 items
- Slide 13 is a game, NOT a reflection
- No writing tasks appear anywhere
- Vocab slides have MAX 8 items
- Game slide has MAX 7 items
- All content is appropriate for ages 16-18, mixed nationality

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
                model=MODEL, max_tokens=8096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.content[0].text
            print(f'[generator] raw response length: {len(raw_text)}')
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


def run(topic, brief, strand, level, week):
    """Wrapper matching app.py call signature."""
    research = dict(brief) if brief else {}
    research['topic_title'] = topic
    research['strand'] = strand
    research['level'] = level
    research['week'] = week
    return generate_lesson(research)
