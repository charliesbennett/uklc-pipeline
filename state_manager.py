"""
State manager for the UKLC lesson pipeline.
Saves and loads pipeline state to disk so runs can be resumed.
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

STATE_DIR = Path(__file__).parent / "state"
STATE_DIR.mkdir(exist_ok=True)


def new_run(settings: dict) -> str:
    """Create a new pipeline run and return its ID."""
    run_id = str(uuid.uuid4())[:8]
    state = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "status": "brainstorming",
        "settings": settings,
        "topics": [],           # list of topic dicts from brainstorm
        "approved_topics": [],  # topics approved by user
        "research": {},         # topic_title -> research brief
        "lessons": {},          # topic_title -> lesson JSON
        "reviewed": {},         # topic_title -> reviewed lesson JSON
        "outputs": {},          # topic_title -> pptx filename
        "errors": {}            # topic_title -> error message
    }
    _save(run_id, state)
    return run_id


def load(run_id: str) -> dict:
    path = STATE_DIR / f"{run_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Run {run_id} not found")
    with open(path) as f:
        return json.load(f)


def save(run_id: str, updates: dict):
    state = load(run_id)
    state.update(updates)
    state["updated_at"] = datetime.now().isoformat()
    _save(run_id, state)


def set_status(run_id: str, status: str):
    save(run_id, {"status": status})


def set_topics(run_id: str, topics: list):
    save(run_id, {"topics": topics, "status": "awaiting_topic_approval"})


def approve_topics(run_id: str, approved_indices: list):
    state = load(run_id)
    approved = [state["topics"][i] for i in approved_indices if i < len(state["topics"])]
    save(run_id, {"approved_topics": approved, "status": "researching"})


def set_research(run_id: str, topic_title: str, brief: dict):
    state = load(run_id)
    state["research"][topic_title] = brief
    state["updated_at"] = datetime.now().isoformat()
    _save(run_id, state)


def approve_research(run_id: str):
    save(run_id, {"status": "generating"})


def set_lesson(run_id: str, topic_title: str, lesson: dict):
    state = load(run_id)
    state["lessons"][topic_title] = lesson
    state["updated_at"] = datetime.now().isoformat()
    _save(run_id, state)


def set_reviewed(run_id: str, topic_title: str, lesson: dict):
    state = load(run_id)
    state["reviewed"][topic_title] = lesson
    state["updated_at"] = datetime.now().isoformat()
    _save(run_id, state)


def set_output(run_id: str, topic_title: str, filename: str):
    state = load(run_id)
    state["outputs"][topic_title] = filename
    state["updated_at"] = datetime.now().isoformat()
    _save(run_id, state)


def set_error(run_id: str, topic_title: str, error: str):
    state = load(run_id)
    state["errors"][topic_title] = error
    state["updated_at"] = datetime.now().isoformat()
    _save(run_id, state)


def list_runs() -> list:
    runs = []
    for f in sorted(STATE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(f) as fh:
                s = json.load(fh)
            runs.append({
                "run_id": s["run_id"],
                "created_at": s["created_at"],
                "status": s["status"],
                "settings": s.get("settings", {}),
                "topic_count": len(s.get("approved_topics", s.get("topics", []))),
                "outputs_count": len(s.get("outputs", {}))
            })
        except Exception:
            pass
    return runs[:20]


def _save(run_id: str, state: dict):
    with open(STATE_DIR / f"{run_id}.json", "w") as f:
        json.dump(state, f, indent=2)
