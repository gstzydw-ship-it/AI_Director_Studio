"""Full pipeline test: Phase 1 planning + Phase 2 segment 1 compilation"""

import sys, os, uuid, io
sys.path.insert(0, os.path.dirname(__file__))

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from agents.director_graph import (
    create_director_graph, _config, clear_state, _normalise_graph_result, OUTPUT_DIR, CHECKPOINT_FILE
)
from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver

SCRIPT = """4-1 夜/内/高端餐吧
人物：乔熙、商北琛、陈进
▲商北琛没看她，慢条斯理地整理着价值不菲的西装袖口。
商北琛：I've got a business dinner. Come with me.
乔熙：Mr. Pierce, I'm off the clock.
商北琛：Company rules—your shift ends when mine does. Need me to remind you?
▲乔熙死死咬住下唇，唇瓣上泛起一圈白色。
▲她转头，满怀歉意地看向陈进。
乔熙：Mr. Quinn, I'm so sorry.
▲话没说完，她惊呼一声——整个人天旋地转，被他一把扛在了肩上。
乔熙：What are you doing? Put me down, Nash Pierce!
▲陈进当场石化。"""

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "full_pipeline_result.txt")

class Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, s):
        for stream in self.streams:
            stream.write(s)
    def flush(self):
        for stream in self.streams:
            stream.flush()

def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    log_f = open(OUTPUT_FILE, "w", encoding="utf-8")
    old_stdout = sys.stdout
    sys.stdout = Tee(old_stdout, log_f)

    try:
        _run()
    finally:
        sys.stdout = old_stdout
        log_f.close()
        print(f"\n✅ 完整输出已保存到: {OUTPUT_FILE}")

def _run():
    clear_state()
    thread_id = f"fulltest-{uuid.uuid4().hex[:8]}"
    print(f"Thread: {thread_id}")

    input_state = {
        "thread_id": thread_id,
        "status": "starting",
        "step": "init",
        "message": "",
        "error": "",
        "started_at": "",
        "script": SCRIPT,
        "aspect_ratio": "9:16",
        "speed_mode": False,
        "reference_images": None,
        "reference_image_b64s": [],
        "reference_image_count": 0,
        "reference_image_manifest": [],
        "agent_outputs": {},
        "current_segment_index": 0,
        "active_segment_index": 0,
        "total_segments": 0,
        "segment_names": [],
        "tail_frame_analysis": "",
        "qc_retry_count": 0,
        "revision_instruction": "",
        "system_guard_report": "",
        "last_qc_status": "",
        "result": "",
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Phase 1: Planning
    print("\n" + "="*60)
    print("=== PHASE 1: PLANNING ===")
    print("="*60)

    with SqliteSaver.from_conn_string(CHECKPOINT_FILE) as checkpointer:
        app = create_director_graph().compile(checkpointer=checkpointer)
        result = app.invoke(input_state, config=_config(thread_id))

    result = _normalise_graph_result(result, thread_id)

    print(f"\nStatus: {result.get('status')}")
    print(f"Step: {result.get('step')}")
    print(f"Total segments: {result.get('total_segments')}")
    print(f"Segment names: {result.get('segment_names')}")

    outputs = result.get("agent_outputs", {})

    if "rhythm_rewrite_director" in outputs:
        print("\n" + "="*60)
        print("=== RHYTHM & REWRITE DIRECTOR OUTPUT ===")
        print("="*60)
        print(outputs["rhythm_rewrite_director"])

    if "story_planner" in outputs:
        print("\n" + "="*60)
        print("=== STORY PLANNER OUTPUT ===")
        print("="*60)
        print(outputs["story_planner"])

    if "shot_director" in outputs:
        print("\n" + "="*60)
        print("=== SHOT DIRECTOR OUTPUT (FULL) ===")
        print("="*60)
        print(outputs["shot_director"])

    # Phase 2: Compile segment 1
    print("\n" + "="*60)
    print("=== PHASE 2: COMPILING SEGMENT 1 ===")
    print("="*60)

    resume_payload = {"segment_index": 1}

    with SqliteSaver.from_conn_string(CHECKPOINT_FILE) as checkpointer:
        app = create_director_graph().compile(checkpointer=checkpointer)
        result2 = app.invoke(Command(resume=resume_payload), config=_config(thread_id))

    result2 = _normalise_graph_result(result2, thread_id)
    outputs2 = result2.get("agent_outputs", {})

    print(f"\nStatus: {result2.get('status')}")
    print(f"QC Status: {result2.get('last_qc_status')}")

    if "compiled_segment_1" in outputs2:
        print("\n" + "="*60)
        print("=== COMPILED SEGMENT 1 PROMPT ===")
        print("="*60)
        print(outputs2["compiled_segment_1"])

    if "quality_inspector" in outputs2:
        print("\n" + "="*60)
        print("=== QUALITY INSPECTOR ===")
        print("="*60)
        print(outputs2["quality_inspector"])

if __name__ == "__main__":
    main()

