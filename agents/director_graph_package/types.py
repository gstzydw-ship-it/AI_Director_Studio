from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypedDict

from ..utils import get_base_dir, get_config_path, get_output_dir

ROOT_DIR = get_base_dir()
OUTPUT_DIR = get_output_dir()
STATE_FILE = os.path.join(OUTPUT_DIR, "pipeline_state.json")
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "director_graph.sqlite")
CONFIG_FILE = get_config_path()
SESSION_ID_RE = re.compile(r"[^A-Za-z0-9_-]")

MAX_QC_RETRIES = 2
STORY_PLANNER_MAX_SCHEMA_ATTEMPTS = 2

_AXIS_LEFT_RE = re.compile(r"左前方")
_AXIS_RIGHT_RE = re.compile(r"右前方")
_REVERSE_SHOT_INSIDE_SEGMENT_RE = re.compile(r"反打(?:至|镜头|过来)")

AGENT_CONFIG_PARENTS = {
    "shot_director_layout": "shot_director",
    "shot_director_blocking": "shot_director",
    "shot_director_guard": "shot_director",
}
DEFAULT_LLM_MODEL = "gpt-5.4"


@dataclass(frozen=True)
class LLMSettings:
    agent_name: str
    api_key: str
    base_url: str
    model: str
    temperature: float | None
    config_path: str
    parent_agent: str | None = None

    @property
    def host(self) -> str:
        try:
            return self.base_url.split("//", 1)[1].split("/", 1)[0] if "//" in self.base_url else self.base_url
        except Exception:
            return self.base_url

    def as_tuple(self) -> tuple[str, str, str, float | None]:
        return self.api_key, self.base_url, self.model, self.temperature

    def missing_fields(self, *, require_api_key: bool = True) -> list[str]:
        missing: list[str] = []
        if require_api_key and not self.api_key:
            missing.append("api_key")
        if not self.base_url:
            missing.append("base_url")
        if not self.model:
            missing.append("model")
        return missing

    def require_valid(self, *, require_api_key: bool = True) -> None:
        missing = self.missing_fields(require_api_key=require_api_key)
        if not missing:
            return
        agent_label = self.agent_name or "default"
        raise ValueError(
            "LLM 配置不完整"
            f"（agent={agent_label}, config={self.config_path}）："
            f"缺少 {', '.join(missing)}。"
        )


class ShotTransitionType(str, Enum):
    HOLD_ON_A = "hold_on_a"
    CUT_TO_B = "cut_to_b"
    PUSH_IN_ON_A = "push_in_on_a"
    PULL_BACK_ON_A = "pull_back_on_a"
    LOCKED_KEEP = "locked_keep"


class TailStateCard(TypedDict, total=False):
    character_positions: list[str]
    contact_relations: list[str]
    prop_states: list[str]
    eyelines: list[str]
    distance_relations: list[str]


class StructuredShotContract(TypedDict, total=False):
    subject_id: str
    space_anchor: str
    action_chain: list[str]
    transition_type: str
    camera_motion: str
    tail_state: TailStateCard
    tail_state_card: TailStateCard
    inherits_prev_tail_state: bool


class DirectorState(TypedDict, total=False):
    thread_id: str
    status: str
    step: str
    message: str
    error: str
    started_at: str
    script: str
    original_script: str
    enhanced_script: str
    atmosphere_strategy: str
    director_brief: str
    aspect_ratio: str
    speed_mode: bool
    reference_images: str | None
    reference_image_b64s: list[str]
    reference_image_count: int
    reference_image_manifest: list[dict[str, str]]
    model_profile_snapshot: dict[str, Any]
    asset_selection: dict[str, Any]
    director_review_required: bool
    director_edits_by_segment: dict[str, Any]
    shot_director_original_by_segment: dict[str, str]
    shot_director_approved_by_segment: dict[str, str]
    knowledge_metadata: dict[str, dict[str, Any]]
    agent_outputs: dict[str, str]
    current_segment_index: int
    active_segment_index: int
    total_segments: int
    segment_names: list[str]
    tail_frame_analysis: str
    qc_retry_count: int
    revision_instruction: str
    director_review_report: str
    system_guard_report: str
    last_qc_status: str
    result: str
    storyboard_images_by_segment: dict[str, str]
