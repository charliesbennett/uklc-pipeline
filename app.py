"""
UKLC Lesson Pipeline — Flask App
Multi-agent pipeline: Brainstorm → Research → Generate → Review → PPTX
"""
import json
import os
import threading
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, send_file

import state_manager as sm
from agents import brainstorm, research, generator, review
from pptx_builder import build_lesson_pptx

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── Ensure required directories exist (Railway ephemeral filesystem) ──────────
Path("state").mkdir(exist_ok=True)
Path("outputs").mkdir(exist_ok=True)
Path("knowledge").mkdir(exist_ok=True)

TEMPLATE_PATH = str(Path(__file__).parent / "PURPOSE_Template_blank.pptx")
OUTPUTS_DIR   = Path(__file__).parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# ── SSE event streams ─────────────────────────────────────────────────────────
_streams: dict[str, list] = {}

def _push(run_id: str, event: str, data: dict):
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    _streams.setdefault(run_id, []).append(msg)

def _stream(run_id: str):
    idx = 0
    while True:
        msgs = _streams.get(run_id, [])
        while idx < len(msgs):
            yield msgs[idx]
            idx += 1
        state = sm.load(run_id)
        if state["status"] in ("complete", "error"):
            break
        time.sleep(0.4)


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return "OK", 200


# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    runs = sm.list_runs()
    return render_template("index.html", runs=runs)

@app.route("/run/<run_id>")
def run_page(run_id):
    state = sm.load(run_id)
    return render_template("run.html", state=state, run_id=run_id)


# ── API routes ────────────────────────────────────────────────────────────────
@app.route("/api/start", methods=["POST"])
def start():
    data = request.json
    key  = data.get("api_key", "").strip()
    if not key:
        return jsonify({"error": "API key required"}), 400
    os.environ["ANTHROPIC_API_KEY"] = key
    settings = {
        "strand":   data.get("strand", "Language"),
        "level":    data.get("level", "Level 3"),
        "week":     data.get("week", "A"),
        "quantity": int(data.get("quantity", 3)),
    }
    run_id = sm.new_run(settings)
    threading.Thread(target=_run_brainstorm, args=(run_id, settings), daemon=True).start()
    return jsonify({"run_id": run_id})


@app.route("/api/stream/<run_id>")
def stream(run_id):
    return Response(_stream(run_id),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/state/<run_id>")
def get_state(run_id):
    return jsonify(sm.load(run_id))


@app.route("/api/approve-topics", methods=["POST"])
def approve_topics():
    data   = request.json
    run_id = data["run_id"]
    state  = sm.load(run_id)
    if state["status"] == "researching":
        return jsonify({"ok": True, "skipped": "already researching"})
    sm.approve_topics(run_id, data["indices"])
    state = sm.load(run_id)
    key   = data.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    threading.Thread(target=_run_research, args=(run_id, state), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/regenerate-topics", methods=["POST"])
def regenerate_topics():
    data   = request.json
    run_id = data["run_id"]
    state  = sm.load(run_id)
    key    = data.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    sm.set_status(run_id, "brainstorming")
    threading.Thread(target=_run_brainstorm,
                     args=(run_id, state["settings"]), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/regenerate-one-topic", methods=["POST"])
def regenerate_one_topic():
    """Replace a single topic idea at the given index, keeping all others."""
    data   = request.json
    run_id = data["run_id"]
    index  = int(data["index"])
    key    = data.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    state    = sm.load(run_id)
    settings = state["settings"]
    existing = state["topics"]

    def _do_regen():
        try:
            new_topics = brainstorm.run(
                strand   = settings["strand"],
                level    = settings["level"],
                week     = settings["week"],
                quantity = 1,
                exclude  = [t["title"] for t in existing]
            )
            if new_topics:
                existing[index] = new_topics[0]
                sm.set_topics(run_id, existing)
                _push(run_id, "topic_replaced", {"index": index, "topic": new_topics[0]})
        except Exception as e:
            _push(run_id, "error", {"message": str(e)})

    threading.Thread(target=_do_regen, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/add-custom-topic", methods=["POST"])
def add_custom_topic():
    """Add a user-supplied topic to the list, fleshed out by Claude."""
    data    = request.json
    run_id  = data["run_id"]
    title   = data.get("title", "").strip()
    context = data.get("context", "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    key = data.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    state    = sm.load(run_id)
    settings = state["settings"]
    existing = list(state.get("topics", []))

    def _do_add():
        try:
            topic = brainstorm.make_from_prompt(
                title   = title,
                context = context,
                strand  = settings["strand"],
                level   = settings["level"],
                week    = settings["week"]
            )
            existing.append(topic)
            sm.set_topics(run_id, existing)
            _push(run_id, "topic_added", {"topic": topic, "index": len(existing) - 1})
        except Exception as e:
            _push(run_id, "error", {"message": str(e)})

    threading.Thread(target=_do_add, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/approve-research", methods=["POST"])
def approve_research():
    data   = request.json
    run_id = data["run_id"]
    state  = sm.load(run_id)
    if state["status"] not in ("awaiting_research_approval",):
        return jsonify({"ok": True, "skipped": "not awaiting approval"})
    key = data.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    sm.approve_research(run_id)
    state = sm.load(run_id)
    threading.Thread(target=_run_generate_all,
                     args=(run_id, state), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/regenerate-lesson", methods=["POST"])
def regenerate_lesson():
    data   = request.json
    run_id = data["run_id"]
    title  = data["title"]
    key    = data.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    state  = sm.load(run_id)
    topic  = next((t for t in state["approved_topics"] if t["title"] == title), None)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    threading.Thread(
        target=_run_single_lesson,
        args=(run_id, topic, state["research"].get(title, {}), state["settings"]),
        daemon=True
    ).start()
    return jsonify({"ok": True})


@app.route("/api/download/<run_id>/<path:topic_slug>")
def download(run_id, topic_slug):
    state = sm.load(run_id)
    fname = state["outputs"].get(topic_slug)
    if not fname:
        return "Not found", 404
    return send_file(OUTPUTS_DIR / fname, as_attachment=True)


@app.route("/api/download-all/<run_id>")
def download_all(run_id):
    import zipfile, io
    state   = sm.load(run_id)
    buf     = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for slug, fname in state.get("outputs", {}).items():
            p = OUTPUTS_DIR / fname
            if p.exists():
                zf.write(p, fname)
    buf.seek(0)
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True,
                     download_name=f"PURPOSE_lessons_{run_id}.zip")


# ── Pipeline workers ──────────────────────────────────────────────────────────
def _run_brainstorm(run_id: str, settings: dict):
    try:
        _push(run_id, "status", {"status": "brainstorming",
                                  "message": "Brainstorming topic ideas…"})
        topics = brainstorm.run(
            strand   = settings["strand"],
            level    = settings["level"],
            week     = settings["week"],
            quantity = settings["quantity"]
        )
        sm.set_topics(run_id, topics)
        _push(run_id, "topics_ready", {"topics": topics})
        _push(run_id, "status", {"status": "awaiting_topic_approval",
                                  "message": "Topics ready — please review and approve."})
    except Exception as e:
        sm.set_status(run_id, "error")
        _push(run_id, "error", {"message": str(e)})


def _run_research(run_id: str, state: dict):
    try:
        settings = state["settings"]
        topics   = state["approved_topics"]
        _push(run_id, "status", {"status": "researching",
                                  "message": f"Researching {len(topics)} topic(s)…"})
        for i, topic in enumerate(topics):
            _push(run_id, "progress", {
                "phase": "research", "current": i + 1,
                "total": len(topics), "topic": topic["title"]
            })
            brief = research.run(topic, settings["strand"], settings["level"])
            sm.set_research(run_id, topic["title"], brief)
            _push(run_id, "research_done", {"topic": topic["title"], "brief": brief})
            if i < len(topics) - 1:
                time.sleep(15)  # avoid rate limiting between research calls
        sm.set_status(run_id, "awaiting_research_approval")
        _push(run_id, "status", {"status": "awaiting_research_approval",
                                  "message": "Research complete — please review and approve."})
    except Exception as e:
        sm.set_status(run_id, "error")
        _push(run_id, "error", {"message": str(e)})


def _run_single_lesson(run_id: str, topic: dict, brief: dict, settings: dict):
    title = topic["title"]
    try:
        _push(run_id, "status", {"status": "generating", "message": f"Regenerating: {title}"})
        _push(run_id, "progress", {"phase": "generate", "topic": title, "current": 1, "total": 1})
        lesson = generator.run(topic, brief, settings["strand"], settings["level"], settings["week"])
        sm.set_lesson(run_id, title, lesson)

        _push(run_id, "progress", {"phase": "review", "topic": title, "current": 1, "total": 1})
        fixed = review.run(lesson)
        sm.set_reviewed(run_id, title, fixed)

        _push(run_id, "progress", {"phase": "pptx", "topic": title, "current": 1, "total": 1})
        pptx_bytes = build_lesson_pptx(fixed, TEMPLATE_PATH)
        tl   = settings["strand"][:4].upper()
        lv   = settings["level"].replace(" ", "")
        wk   = settings["week"]
        slug = title.replace(" ", "_").upper()[:30]
        fname = f"PURPOSE_{wk}_{lv}_{tl}_{slug}.pptx"
        (OUTPUTS_DIR / fname).write_bytes(pptx_bytes)
        sm.set_output(run_id, title, fname)
        _push(run_id, "lesson_done", {
            "topic": title, "filename": fname,
            "slide_count": len(fixed.get("student_slides", [])) + 6,
            "index": 1, "total": 1
        })
        state = sm.load(run_id)
        if all(t["title"] in state.get("outputs", {}) for t in state["approved_topics"]):
            sm.set_status(run_id, "complete")
            _push(run_id, "status", {"status": "complete",
                                      "message": "All lessons generated successfully!"})
    except Exception as e:
        sm.set_error(run_id, title, str(e))
        _push(run_id, "lesson_error", {"topic": title, "error": str(e)})


def _run_generate_all(run_id: str, state: dict):
    settings      = state["settings"]
    topics        = state["approved_topics"]
    research_data = state["research"]

    for i, topic in enumerate(topics):
        title = topic["title"]
        _push(run_id, "status", {"status": "generating",
                                  "message": f"Generating lesson {i+1}/{len(topics)}: {title}"})
        try:
            _push(run_id, "progress", {"phase": "generate", "topic": title,
                                        "current": i+1, "total": len(topics)})
            lesson = generator.run(topic, research_data.get(title, {}),
                                   settings["strand"], settings["level"], settings["week"])
            sm.set_lesson(run_id, title, lesson)

            _push(run_id, "progress", {"phase": "review", "topic": title,
                                        "current": i+1, "total": len(topics)})
            fixed = review.run(lesson)
            sm.set_reviewed(run_id, title, fixed)

            _push(run_id, "progress", {"phase": "pptx", "topic": title,
                                        "current": i+1, "total": len(topics)})
            pptx_bytes = build_lesson_pptx(fixed, TEMPLATE_PATH)
            tl   = settings["strand"][:4].upper()
            lv   = settings["level"].replace(" ", "")
            wk   = settings["week"]
            slug = title.replace(" ", "_").upper()[:30]
            fname = f"PURPOSE_{wk}_{lv}_{tl}_{slug}.pptx"
            (OUTPUTS_DIR / fname).write_bytes(pptx_bytes)
            sm.set_output(run_id, title, fname)
            _push(run_id, "lesson_done", {
                "topic": title, "filename": fname,
                "slide_count": len(fixed.get("student_slides", [])) + 6,
                "index": i + 1, "total": len(topics)
            })
        except Exception as e:
            sm.set_error(run_id, title, str(e))
            _push(run_id, "lesson_error", {"topic": title, "error": str(e)})

        if i < len(topics) - 1:
            time.sleep(5)

    sm.set_status(run_id, "complete")
    _push(run_id, "status", {"status": "complete",
                              "message": "All lessons generated successfully!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
