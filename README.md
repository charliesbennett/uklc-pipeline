# UKLC Purpose Lesson Pipeline

4-agent agentic pipeline for generating PURPOSE lesson PowerPoints.

## Setup

```bash
cd uklc-pipeline
pip install -r requirements.txt
```

## Run

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python app.py
```

Then open http://localhost:5001 in your browser.

## Pipeline stages

1. **Brainstorm** — Generates topic ideas based on strand, level, week, and the existing lesson library
2. **Research** — Web-searches each approved topic to build a structured brief (facts, vocabulary, quiz questions, task brief)
3. **Generate** — Uses the research brief to build a complete lesson JSON (15–18 slides)
4. **Review** — Auto-fixes the lesson against Charlie's patterns (structure, scrambled gap-fills, max 7 quiz items, no timestamps, etc.)
5. **PPTX** — Builds and downloads clean PowerPoint files

## State

All pipeline state is saved to `state/` as JSON files.
Each run has a unique ID and can be resumed if something fails.

## Knowledge library

`knowledge/lessons.json` contains all existing PURPOSE lessons.
The Brainstorm Agent reads this to avoid topic duplication.
Update it as new lessons are finalised.
