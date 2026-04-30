"""Quick test: run Phase-1 of the director pipeline with the original script
and verify the new knowledge-base rules take effect."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from agents.director_graph import (
    create_director_graph, _invoke_graph, _config, clear_state
)
import uuid

SCRIPT = """2-1 日/内/天御集团大堂
人物：乔熙、商北琛、苏小可、严飞、众员工
▲商北琛迈步走进大堂，锐利的眸子淡淡扫过两边的人群。
严飞：Welcome, Mr. Pierce.
▲商北琛没说话，眉头微皱。
商北琛：Meeting in ten minutes. Directors and above, be there.
▲主管们瞬间四散。
▲商北琛转身进入电梯，就在电梯门即将关闭之际——
乔熙：Wait a second!
▲乔熙像风一般冲进电梯，一个刹不住，整个人直扑到商北琛身上。
▲男人西装布料下的胸膛，坚实滚烫。
▲商北琛下意识伸手，稳稳扶住她的腰。
商北琛：Long time no see—since when did you start throwing yourself at people?
▲乔熙寻声抬头，撞进一双深不见底的眼眸里。
商北琛：You gonna keep holding on or what?
▲乔熙瞬间回神，触电般松开手，尴尬地拨弄头发。"""

def main():
    clear_state()
    thread_id = f"test-{uuid.uuid4().hex[:8]}"
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
    
    result = _invoke_graph(input_state, thread_id)
    
    # Print key outputs
    if isinstance(result, dict):
        print(f"\n=== STATUS: {result.get('status')} ===")
        print(f"=== STEP: {result.get('step')} ===")
        print(f"=== TOTAL SEGMENTS: {result.get('total_segments')} ===")
        print(f"=== SEGMENT NAMES: {result.get('segment_names')} ===")
        
        outputs = result.get("agent_outputs", {})
        
        if "story_planner" in outputs:
            print("\n" + "="*60)
            print("=== STORY PLANNER OUTPUT ===")
            print("="*60)
            print(outputs["story_planner"][:3000])
        
        # Find compiled segment keys
        for key in sorted(outputs.keys()):
            if "compiled" in key or key == "prompt_compiler":
                print(f"\n{'='*60}")
                print(f"=== {key.upper()} ===")
                print("="*60)
                print(outputs[key][:2000])

if __name__ == "__main__":
    main()
