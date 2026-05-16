from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.director_graph_package.shot_director_impl import (  # noqa: E402
    _build_shot_director_signal_retrieval_profile,
    _build_shot_director_workflow_trace,
    _call_stage_split_by_fragment,
    _extract_rhythm_shot_director_notes,
    _planner_source_event_context,
    _reference_image_manifest_prompt,
    _reference_images,
    _scene_reference_items,
    _rhythm_shot_director_notes_prompt,
    _shot_library_signal_task_card,
    _shot_director_blocking_rule_block,
    _shot_director_coverage_contract_prompt,
    _shot_director_downstream_context,
    _shot_director_guard_stage_rule_block,
    _shot_director_rule_block,
    _shot_director_workflow_contract,
    _repair_shot_director_output_contracts,
    _validate_shot_director_output,
    _validate_shot_director_variety,
)
from agents.director_graph_package import shot_director_impl as sdi  # noqa: E402


def _coverage_v3_output(shots: str, *, target_count: int = 1, max_count: int = 3) -> str:
    return f"""- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: test coverage
    rhythm_intent: controlled
    space_contract:
      location: test room
    shot_budget:
      target_count: {target_count}
      max_count: {max_count}
    required_beats:
      - establish_continuity
  template_plan:
    shots:
{shots}
  guard_result:
    status: pass
    final_shots: [F01-S01]
    repairs: []
"""


def test_shot_director_explicit_workflow_contract_is_present():
    contract = _shot_director_workflow_contract()
    coverage_contract = _shot_director_coverage_contract_prompt()

    for stage_name in (
        "浜嬪疄鎻愬彇",
        "鑺傚鎰忓浘璇诲彇",
        "鍓緫绛栫暐鍒ゆ柇",
        "鎴忓墽浠诲姟鍒ゆ柇",
        "闀滃ご楠ㄦ灦",
        "闀滃ご璇█鍙樺寲",
        "鍔ㄤ綔涓庡瓙闀滃ご",
        "鍒囬暅鏃舵満",
        "鍐茬獊瑁佸喅",
        "鏈€灏忎慨澶?,
        "鏈€缁堜氦浠?,
    ):
        assert stage_name in contract

    for field_name in (
        "coverage_role",
        "cut_reason",
        "continuity",
        "tailframe_role",
        "template_plan",
    ):
        assert field_name in coverage_contract


def test_shot_director_rejects_legacy_chinese_output_fields():
    director_output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 鐢垫鍙ｅ帇杩?
  鑺傚: 鍓嶅帇鍚庡仠
  绌洪棿杩炵画鎬ф€绘帶: 鏈墖娈垫槸涓€娈电數姊彛鍘嬭揩锛涗箶鐔欏拰鍟嗗寳鐞涘缁堝湪鍚屼竴鐢垫鍙ｇ┖闂村唴锛涘崟浜洪暅鍙敼鍙樻媿鎽勪富浣擄紝涓嶄唬琛ㄥ彟涓€浜虹寮€锛涙瘡涓€闀滅户鎵夸笂涓€闀滃熬甯х殑浜虹墿浣嶇疆銆侀亾鍏风姸鎬併€佽绾挎柟鍚戝拰鍚屼晶杞寸嚎銆?
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-2绉?
      闀滃ご浠诲姟: 寤虹珛鍏崇郴
      鎷嶆憚涓讳綋: 涔旂啓鍜屽晢鍖楃悰
      闀滃ご: 渚ч潰瑙嗚鍙屼汉涓櫙
      鐢婚潰鍔ㄤ綔: 涔旂啓鍋滃湪鐢垫鍙ｏ紝鍟嗗寳鐞涙尅浣忓幓璺?
      鍙拌瘝: ~
      蹇呴』鎵胯浇: 涓や汉鐨勭┖闂磋窛绂诲拰鍘嬭揩鍏崇郴
      鍒囬暅鐐? 鐢垫闂ㄥ仠鍦ㄥ崐寮€鐘舵€佹椂鍒囧嚭
      杩炵画鎬? 涔旂啓鍦ㄧ敾闈㈠彸渚э紝鍟嗗寳鐞涘湪鐢婚潰宸︿晶锛岀數姊棬浠嶅崐寮€
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("only schema_version: shot_director_coverage_v3 is supported." in issue for issue in issues)


def test_shot_director_accepts_coverage_v3_template_plan():
    director_output = """- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: elevator two-person pressure
    rhythm_intent: hold reaction after pressure line
    space_contract:
      location: elevator
      characters_present: [Sunny, Nash]
      axis: face-to-face axis
    shot_budget:
      target_count: 2
      max_count: 3
    required_beats:
      - beat_id: B01
        purpose: establish_relation
  template_plan:
    shots:
      - shot_id: F01-S01
        duration: 0-3s
        task: establish close two-person pressure
        subject: Sunny and Nash
        shot: two-person medium relation shot, eye-level fixed view
        action: Sunny looks at Nash after standing steady; Nash holds his position.
        dialogue: ~
        must_carry: distance, facing direction, closed elevator door
        cut_point: cut after the distance relation is readable
        continuity: both remain inside the same closed elevator
        coverage_role: establish_relation
        cut_reason: distance relation becomes readable before reaction
        companion_visibility: both visible in same frame
        state_delta: Sunny is steady
        tailframe_role: hand off to reaction
        template_id: COV-SD20-W1-TWO-SHOT-PRESSURE
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: Sunny and Nash remain close, facing each other, elevator door closed.
      - shot_id: F01-S02
        duration: 3-6s
        task: carry Sunny impact reaction
        subject: Sunny
        shot: Sunny chest-up medium close shot, eye-level, from Nash shoulder toward Sunny
        action: Sunny looks up at Nash and briefly freezes.
        dialogue: ~
        must_carry: Sunny reaction after being pressured
        cut_point: cut after reaction appears
        continuity: Nash shoulder remains in foreground; distance unchanged
        coverage_role: impact_reaction
        cut_reason: reaction appears before returning to relation
        companion_visibility: Nash shoulder in foreground
        state_delta: Sunny changes from unsettled to frozen
        tailframe_role: hold post-reaction state
        template_id: COV-SD20-W1-REACTION-HOLD
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: Sunny remains facing Nash; Nash is still close in the same elevator.
  guard_result:
    status: pass
    repairs: []
    final_shots: [F01-S01, F01-S02]
"""

    assert _validate_shot_director_output(director_output, ["F01"]) == []

def test_shot_director_coverage_v3_requires_coverage_fields():
    director_output = """- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: 寤虹珛鍏崇郴
    rhythm_intent: 姝ｅ父鎵挎帴
    space_contract:
      location: 鐢垫鍐?
    shot_budget:
      target_count: 1
    required_beats:
      - establish_relation
  template_plan:
    shots:
      - shot_id: F01-S01
        duration: 0-3绉?
        task: 寤虹珛鍏崇郴
        subject: 涔旂啓鍜屽晢鍖楃悰
        shot: 鍙屼汉鍗婅韩鍏崇郴鏅紝骞宠锛屽浐瀹氳瑙?
        action: 涓や汉闈㈠闈㈢珯瀹氥€?
        dialogue: ~
        must_carry: 涓や汉浣嶇疆鍏崇郴
        cut_point: 浣嶇疆鍏崇郴鐪嬫竻鍚庡垏鍑?
        continuity: 涓や汉浠嶅湪鍚屼竴鐢垫鍐?
  guard_result:
    status: pass
    final_shots: [F01-S01]
"""

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("coverage v3 missing field coverage_role" in issue for issue in issues)
    assert any("coverage v3 missing field tailframe_role" in issue for issue in issues)
    assert any("missing Seedance coverage template field template_id" in issue for issue in issues)
    assert any("seedance_template_id_missing" in issue for issue in issues)


def test_shot_director_rejects_overfragmented_life_pressure_segment():
    shot_lines = []
    durations = ["0-2.2绉?, "2.2-2.9绉?, "2.9-4.9绉?, "4.9-6.7绉?, "6.7-9.3绉?, "9.3-10.1绉?, "10.1-12.1绉?]
    for index, duration in enumerate(durations, start=1):
        shot_lines.append(
            f"""      - shot_id: F01-S{index:02d}
        duration: {duration}
        task: 鎵胯浇娓呮櫒璧舵椂闂寸┛琛ｅ姩浣?
        subject: 涔旂啓銆佸皬璞嗕竵
        shot: 鍙屼汉鍗婅韩鍏崇郴鏅紝鑼跺嚑渚ч潰鍥哄畾瑙嗚
        action: 涔旂啓鍦ㄦ矙鍙戝墠甯皬璞嗕竵绌胯。锛屽皬璞嗕竵鐭殏鎶楁嫆鍚庡仠浣忋€?
        dialogue: ~
        must_carry: 涔旂啓璧舵椂闂达紝灏忚眴涓佹姉鎷掔┛琛ｃ€?
        cut_point: 灏忚眴涓佹姉鎷掑姩浣滃仠浣忓悗鍒囧嚭
        continuity: 涔旂啓鍜屽皬璞嗕竵浠嶅湪娌欏彂涓庤尪鍑犱箣闂达紝鎵嬫満浠嶅湪鑼跺嚑涓娿€?
        coverage_role: 鎵胯浇鐢熸椿鍔ㄤ綔鍘嬪姏
        cut_reason: 灏忚眴涓佹姉鎷掑姩浣滃仠浣忓悗鍒囧嚭
        companion_visibility: 涔旂啓鍜屽皬璞嗕竵鍚屾
        state_delta: 鎶楁嫆鍔ㄤ綔鐭殏鍋滀綇
        tailframe_role: 浜ょ粰涓嬩竴闀滅户缁┛琛ｇ姸鎬?
        template_id: COV-SD20-W1-LIFE-PRESSURE
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: 涔旂啓鍜屽皬璞嗕竵浠嶅湪娌欏彂涓庤尪鍑犱箣闂?
"""
        )
    director_output = _coverage_v3_output("".join(shot_lines), target_count=7, max_count=7)

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("闀滃ご鍒囧垎杩囩" in issue for issue in issues)
    assert any("1绉掍互涓嬬闀? in issue for issue in issues)


def test_shot_director_rules_lock_subject_ownership_and_task_combos():
    combined_rules = "\n".join(
        [
            _shot_director_workflow_contract(),
            _shot_director_rule_block("9:16"),
            sdi._shot_director_layout_rule_block("9:16"),
            _shot_director_blocking_rule_block("9:16"),
            _shot_director_guard_stage_rule_block("9:16"),
        ]
    )

    assert "鎷嶆憚涓讳綋涓嶆槸浜虹墿/閬撳叿娓呭崟" in combined_rules
    assert "鎴忓墽浠诲姟闀滃ご缁勫悎" in combined_rules
    assert "鎵挎帴涓婁竴闀滃熬甯? in combined_rules


def test_shot_director_rejects_overloaded_random_subject_list():
    director_output = _coverage_v3_output("""      - shot_id: F01-S01
        duration: 0-4绉?
        task: 寤虹珛璧舵椂闂寸敓娲诲帇鍔?
        subject: 涔旂啓銆佸皬璞嗕竵銆侀椆閽熴€佹墜鏈恒€佸濂椼€佽崏鑾撹泲绯曘€佷功鍖?
        shot: 鍙屼汉鍗婅韩鍏崇郴鏅紝娌欏彂渚ч潰鍥哄畾瑙嗚
        action: 涔旂啓鍧愬湪娌欏彂杈圭粰灏忚眴涓佸琛ｆ湇锛屽皬璞嗕竵缂╄剼鎶楁嫆锛岄暅灏句袱浜轰粛鍦ㄦ矙鍙戣竟銆?
        dialogue: "Kiki, cover for me. I'll be right there!"
        must_carry: 涔旂啓璧舵椂闂达紝灏忚眴涓佹姉鎷掔┛琛ｃ€?
        cut_point: 灏忚眴涓佺缉鑴氬姩浣滃仠浣忓悗鍒囧嚭
        continuity: 鎵嬫満浠嶅湪涔旂啓鑰宠竟锛屽皬璞嗕竵浠嶅湪娌欏彂杈广€?
        coverage_role: 寤虹珛鐢熸椿鍘嬪姏
        cut_reason: 灏忚眴涓佺缉鑴氬姩浣滃仠浣忓悗鍒囧嚭
        companion_visibility: 涔旂啓鍜屽皬璞嗕竵鍚屾
        state_delta: 灏忚眴涓佹姉鎷掑姩浣滃嚭鐜?
        tailframe_role: 浜ょ粰涓嬩竴闀滅户缁┛琛ｇ姸鎬?
        template_id: COV-SD20-W1-LIFE-PRESSURE
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: 涔旂啓鍜屽皬璞嗕竵浠嶅湪娌欏彂杈?
""")

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("鎷嶆憚涓讳綋杩囪浇" in issue for issue in issues)
    assert any("闅忔満閬撳叿闆嗗悎" in issue or "閬撳叿娣疯繘涓绘媿鎽勪富浣? in issue for issue in issues)


def test_shot_director_rejects_teleport_without_tailframe_carry():
    director_output = _coverage_v3_output("""      - shot_id: F01-S01
        duration: 0-4绉?
        task: 寤虹珛姣嶅コ绌胯。闃诲姏
        subject: 涔旂啓鍜屽皬璞嗕竵
        shot: 鍙屼汉鍗婅韩鍏崇郴鏅紝娌欏彂渚ч潰鍥哄畾瑙嗚
        action: 涔旂啓鍧愬湪娌欏彂杈圭粰灏忚眴涓佸琛ｆ湇锛屽皬璞嗕竵缂╄剼鎶楁嫆锛岄暅灏句袱浜轰粛鍧愬湪娌欏彂杈广€?
        dialogue: "Kiki, cover for me. I'll be right there!"
        must_carry: 涔旂啓璧舵椂闂达紝灏忚眴涓佹姉鎷掔┛琛ｃ€?
        cut_point: 灏忚眴涓佺缉鑴氬姩浣滃仠浣忓悗鍒囧嚭
        continuity: 涔旂啓鍜屽皬璞嗕竵浠嶅潗鍦ㄦ矙鍙戣竟锛屾墜鏈轰粛鍦ㄤ箶鐔欒€宠竟銆?
        coverage_role: 寤虹珛姣嶅コ绌胯。闃诲姏
        cut_reason: 灏忚眴涓佺缉鑴氬姩浣滃仠浣忓悗鍒囧嚭
        companion_visibility: 涔旂啓鍜屽皬璞嗕竵鍚屾
        state_delta: 灏忚眴涓佹姉鎷掑姩浣滃嚭鐜?
        tailframe_role: 浜ょ粰涓嬩竴闀滅户缁┛琛ｇ姸鎬?
        template_id: COV-SD20-W1-LIFE-PRESSURE
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: 涔旂啓鍜屽皬璞嗕竵浠嶅潗鍦ㄦ矙鍙戣竟
      - shot_id: F01-S02
        duration: 4-8绉?
        task: 鎵胯浇绌胯。瀹屾垚鍜屾嬁涔﹀寘
        subject: 涔旂啓鍜屽皬璞嗕竵
        shot: 鍙屼汉涓櫙锛岃尪鍑犱晶闈㈠浐瀹氳瑙?
        action: 灏忚眴涓佺獊鐒剁珯鍦ㄨ尪鍑犳梺锛岃。鏈嶅凡缁忕┛濂姐€備箶鐔欐嬁璧蜂功鍖呫€?
        dialogue: ~
        must_carry: 灏忚眴涓佸凡缁忛厤鍚堢┛琛ｏ紝涔旂啓鍑嗗鍑洪棬銆?
        cut_point: 涔旂啓鎷胯捣涔﹀寘鍚庡垏鍑?
        continuity: 鎵嬫満鍦ㄨ尪鍑犱笂銆?
        coverage_role: 鎵胯浇绌胯。瀹屾垚鍜屾嬁涔﹀寘
        cut_reason: 涔旂啓鎷胯捣涔﹀寘鍚庡垏鍑?
        companion_visibility: 涔旂啓鍜屽皬璞嗕竵鍚屾
        state_delta: 灏忚眴涓佸凡绔欒捣涓旇。鏈嶇┛濂?
        tailframe_role: 浜ょ粰鍑洪棬鍔ㄤ綔
        template_id: COV-SD20-W1-LIFE-PRESSURE
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: 涔旂啓鎷胯捣涔﹀寘锛屽皬璞嗕竵绔欏湪鑼跺嚑鏃?
""", target_count=2, max_count=2)

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("缂哄皯鎵挎帴涓婁竴闀滃熬甯? in issue for issue in issues)


def test_shot_director_repair_adds_fragment_continuity_context():
    director_output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 杞﹀唴鍛戒护鎴撮」閾?
  鑺傚: 鍛戒护鍘嬭揩鍚庣粰涔旂啓鍙嶅簲
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-3绉?
      闀滃ご浠诲姟: 寤虹珛杞﹀唴鍙屼汉鍏崇郴
      鎷嶆憚涓讳綋: 涔旂啓銆佸晢鍖楃悰
      闀滃ご: 绔栧睆鍙屼汉涓櫙
      鐢婚潰鍔ㄤ綔: 鍟嗗寳鐞涙嬁鐫€椤归摼鐪嬪悜涔旂啓锛屼箶鐔欏潗鍦ㄦ梺杈规壙鎺ュ帇鍔?
      鍙拌瘝: ~
      蹇呴』鎵胯浇: 涓や汉鍚屽杞﹀唴鍜岄」閾惧帇杩叧绯?
      鍒囬暅鐐? 椤归摼琚嬁璧峰悗鍒囧嚭
      杩炵画鎬? 涔旂啓鍜屽晢鍖楃悰浠嶅湪鍚屼竴杞﹀唴绌洪棿锛岄」閾句粛鍦ㄥ晢鍖楃悰鎵嬩腑
"""
    script = """9-1 澶?鍐?鍔虫柉鑾辨柉杞﹀唴
浜虹墿锛氫箶鐔欍€佸晢鍖楃悰
鍟嗗寳鐞涳細Put the necklace on. And don't embarrass me.
"""

    repaired = _repair_shot_director_output_contracts(director_output, script)

    assert "绌洪棿杩炵画鎬ф€绘帶:" in repaired
    assert "涔旂啓銆佸晢鍖楃悰鍦?-1 澶?鍐?鍔虫柉鑾辨柉杞﹀唴鐨勫悓涓€绌洪棿鍐? in repaired
    assert "鍗曚汉闀滃彧鏀瑰彉鎷嶆憚涓讳綋" in repaired
    assert any(
        "only schema_version: shot_director_coverage_v3 is supported." in issue
        for issue in _validate_shot_director_output(repaired, ["F01"])
    )


def test_shot_director_rules_keep_camera_and_performance_fields_separate():
    rule_block = _shot_director_rule_block("9:16")
    blocking_rules = _shot_director_blocking_rule_block("9:16")
    guard_rules = _shot_director_guard_stage_rule_block("9:16")

    for text in (rule_block, blocking_rules, guard_rules):
        assert "template_plan" in text or "shot 瀛楁" in text or "shot_id" in text
        assert "action" in text or "鐢婚潰鍔ㄤ綔" in text

    assert "template_plan.shots" in blocking_rules
    assert "guard_result" in guard_rules
    assert "shot_director_coverage_v3" in guard_rules


def test_shot_director_rejects_untranslated_camera_jargon_in_final_shot_field():
    director_output = _coverage_v3_output("""      - shot_id: F01-S01
        duration: 0-4绉?
        task: 寤虹珛璧舵椂闂寸敓娲诲帇鍔?
        subject: 涔旂啓鍜屽皬璞嗕竵
        shot: 鍙屼汉鍗婅韩鍏崇郴鏅紝娌欏彂渚ч潰鍥哄畾鏈轰綅
        action: 涔旂啓鍧愬湪娌欏彂杈圭粰灏忚眴涓佸琛ｆ湇锛岃绾跨湅鍚戦棬鍙ｏ紱灏忚眴涓佺缉鑴氭姉鎷掞紝闀滃熬涓や汉浠嶅湪娌欏彂杈广€?
        dialogue: "Kiki, cover for me. I'll be right there!"
        must_carry: 涔旂啓璧舵椂闂达紝灏忚眴涓佹姉鎷掔┛琛ｃ€?
        cut_point: 鍙拌瘝钀戒笅鍚庡皬璞嗕竵鎶楁嫆鍙嶅簲鍑虹幇鏃跺垏鍑?
        continuity: 鎵嬫満浠嶅湪涔旂啓鑰宠竟锛屽皬璞嗕竵浠嶅湪娌欏彂杈广€?
        coverage_role: 寤虹珛鐢熸椿鍘嬪姏
        cut_reason: 灏忚眴涓佹姉鎷掑弽搴斿嚭鐜版椂鍒囧嚭
        companion_visibility: 涔旂啓鍜屽皬璞嗕竵鍚屾
        state_delta: 灏忚眴涓佹姉鎷掑姩浣滃嚭鐜?
        tailframe_role: 浜ょ粰涓嬩竴闀滅户缁┛琛ｇ姸鎬?
        template_id: COV-SD20-W1-LIFE-PRESSURE
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: 涔旂啓鍜屽皬璞嗕竵浠嶅湪娌欏彂杈?
""")

    issues = _validate_shot_director_output(director_output, ["F01"])

    assert any("untranslated camera jargon" in issue for issue in issues)
    assert any("渚ч潰瑙嗚" in issue and "鍥哄畾瑙嗚" in issue for issue in issues)


def test_shot_logic_reviewer_local_issues_flag_camera_action_leak():
    director_output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 杞﹀唴鍛戒护鎴撮」閾?
  鑺傚: 椤归摼璇嗗埆鍙嶅簲蹇呴』鍋滀綇
  绌洪棿杩炵画鎬ф€绘帶: 鏈墖娈垫槸涓€娈佃溅鍐呴」閾惧帇杩紱涔旂啓鍜屽晢鍖楃悰濮嬬粓鍦ㄥ悓涓€杞﹀悗鎺掔┖闂村唴锛涘崟浜洪暅鍙敼鍙樻媿鎽勪富浣擄紝涓嶄唬琛ㄥ彟涓€浜虹寮€銆?
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-2绉?
      闀滃ご浠诲姟: 鎵胯浇涔旂啓璇嗗埆椤归摼
      鎷嶆憚涓讳綋: 涔旂啓
      闀滃ご: 涔旂啓涓繎鏅紝濂逛綆澶寸湅娓呴」閾?
      鐢婚潰鍔ㄤ綔: 涔旂啓鐪嬮」閾?
      鍙拌瘝: ~
      蹇呴』鎵胯浇: 涔旂啓璁ゅ嚭椤归摼
      鍒囬暅鐐? 涔旂啓鐪嬫竻鍚庡垏鍑?
      杩炵画鎬? 椤归摼鍦ㄧ敾闈㈤噷
"""
    script = """9-1 澶?鍐?鍔虫柉鑾辨柉杞﹀唴
浜虹墿锛氫箶鐔欍€佸晢鍖楃悰
"""

    issues = sdi._shot_logic_local_issues(director_output, script)

    assert any("闀滃ご瀛楁娣峰叆浜虹墿鍔ㄤ綔" in issue for issue in issues)
    assert any("鐢婚潰鍔ㄤ綔缂哄皯鍔ㄤ綔琛ㄦ儏閾? in issue for issue in issues)
    assert any("鍗曚汉闀滅己灏戝悓鍦轰汉鐗╀繚鐣? in issue for issue in issues)


def test_shot_logic_reviewer_local_issues_flag_action_overload_for_prompt_compiler():
    director_output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 娌欏彂杈瑰畨鎶氬瀛?
  鑺傚: 鍏堝帇杩啀瀹夋姎
  绌洪棿杩炵画鎬ф€绘帶: 涔旂啓鍜屽皬璞嗕竵濮嬬粓鍦ㄦ矙鍙戣竟锛屾墜鏈轰粛鍦ㄤ箶鐔欒€宠竟銆?
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-4绉?
      闀滃ご浠诲姟: 鎵胯浇涔旂啓闈犺繎骞惰瘯鍥炬帶鍒跺眬闈?
      鎷嶆憚涓讳綋: 涔旂啓涓庡皬璞嗕竵
      闀滃ご: 涓繎鏅紝娌欏彂杈瑰悓渚ф満浣?
      鐢婚潰鍔ㄤ綔: 涔旂啓浠嶇敤鍙虫墜鎷跨潃鎵嬫満璐村湪鑰宠竟璇磋瘽锛屽悓鏃堕『鐫€娌欏彂杈逛几鎵嬬壍浣忓皬璞嗕竵锛岃韩浣撳帇杩戞矙鍙戣竟鎯虫妸澶栧濂楀埌瀛╁瓙韬笂锛涘皬璞嗕竵鍏堢缉鑴氳翰寮€锛屽張閰嶅悎绌胯。瀹屾垚銆?
      鍙拌瘝: ~
      蹇呴』鎵胯浇: 鎵嬫満浠嶅湪涔旂啓鎵嬮噷锛屽皬璞嗕竵杩樺湪鎶楁嫆銆?
      鍒囬暅鐐? 灏忚眴涓佺缉鑴氬悗鍒囧嚭
      杩炵画鎬? 涓や汉浠嶅湪娌欏彂杈癸紝琛ｆ湇灏氭湭绌垮ソ銆?
"""

    issues = sdi._shot_logic_local_issues(director_output, "涔旂啓锛欿iki, cover for me.\n灏忚眴涓侊細涓嶈銆?)

    assert any("鐢婚潰鍔ㄤ綔杩囪浇鎴栬偄浣撳崰鐢ㄤ笉娓? in issue for issue in issues)
    assert any("浜虹墿浠庢姉鎷掑埌閰嶅悎缂哄皯杩囨浮" in issue for issue in issues)
    assert any("1-2 鍙ヨ嚜鐒剁煭鍔ㄤ綔" in issue for issue in issues)


def test_shot_logic_reviewer_accepts_safe_repair(monkeypatch):
    primary_output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 杞﹀唴鍛戒护鎴撮」閾?
  鑺傚: 椤归摼闈犺繎鍚庝箶鐔欒瘑鍒?
  绌洪棿杩炵画鎬ф€绘帶: 鏈墖娈垫槸涓€娈佃溅鍐呴」閾惧帇杩紱涔旂啓鍜屽晢鍖楃悰濮嬬粓鍦ㄥ悓涓€杞﹀悗鎺掔┖闂村唴锛涘崟浜洪暅鍙敼鍙樻媿鎽勪富浣擄紝涓嶄唬琛ㄥ彟涓€浜虹寮€銆?
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-2绉?
      闀滃ご浠诲姟: 鎵胯浇涔旂啓璇嗗埆椤归摼
      鎷嶆憚涓讳綋: 涔旂啓
      闀滃ご: 涔旂啓涓繎鏅紝濂逛綆澶寸湅娓呴」閾?
      鐢婚潰鍔ㄤ綔: 涔旂啓鐪嬮」閾?
      鍙拌瘝: ~
      蹇呴』鎵胯浇: 涔旂啓璁ゅ嚭椤归摼
      鍒囬暅鐐? 涔旂啓鐪嬫竻鍚庡垏鍑?
      杩炵画鎬? 椤归摼鍦ㄧ敾闈㈤噷
"""
    repaired_output = """- fragment_id: F01
  schema_version: shot_director_coverage_v3
  coverage_plan:
    dramatic_task: 杞﹀唴鍛戒护鎴撮」閾?
    rhythm_intent: 椤归摼闈犺繎鍚庝箶鐔欒瘑鍒?
    space_contract:
      location: 鍔虫柉鑾辨柉杞﹀唴
    shot_budget:
      target_count: 1
      max_count: 1
    required_beats:
      - necklace_recognition
  template_plan:
    shots:
      - shot_id: F01-S01
        duration: 0-2绉?
        task: 鎵胯浇涔旂啓璇嗗埆椤归摼
        subject: 涔旂啓
        shot: 涔旂啓涓繎鏅紝杞﹀唴鍚屼晶寰晶瑙嗚
        action: 涔旂啓鑲╅缁风揣锛岃绾夸粠鍟嗗寳鐞涙墜涓殑椤归摼钀藉埌鍚婂潬銆傜湅娓呭悗濂圭溂绁炲仠浣忥紝韬綋浠嶅潗鍦ㄥ師浣嶃€?
        dialogue: ~
        must_carry: 涔旂啓璁ゅ嚭椤归摼锛屽晢鍖楃悰浠嶅湪杩戜晶褰㈡垚鍘嬪姏锛岄」閾句粛鏈埓涓娿€?
        cut_point: 涔旂啓鐪嬫竻椤归摼鍚庣溂绁炲仠浣忔椂鍒囧嚭
        continuity: 鍟嗗寳鐞涗粛鍦ㄤ箶鐔欒繎渚э紝椤归摼浠嶅湪鍟嗗寳鐞涙墜涓紝涔旂啓鍧愬湪鍘熶綅娌℃湁绂诲紑銆?
        coverage_role: 鎵胯浇涔旂啓璇嗗埆椤归摼
        cut_reason: 涔旂啓鐪嬫竻椤归摼鍚庣溂绁炲仠浣忔椂鍒囧嚭
        companion_visibility: 鍟嗗寳鐞涗粛鍦ㄤ箶鐔欒繎渚х敾澶栨垨杈圭紭
        state_delta: 涔旂啓浠庣揣缁疯浆涓鸿鍑洪」閾惧悗鐨勫仠浣?
        tailframe_role: 淇濈暀涔旂啓璁ゅ嚭椤归摼鍚庣殑鍋滈】
        template_id: COV-SD20-W1-REACTION-HOLD
        template_level: W1
        reference_need: identity_reference scene_reference
        model_complexity_score: 2
        tail_state: 涔旂啓鍧愬湪鍘熶綅锛屽晢鍖楃悰杩戜晶鏂藉帇锛岄」閾句粛鏈埓涓娿€?
  guard_result:
    status: pass
    final_shots: [F01-S01]
    repairs: []
"""

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        assert "闀滃ご閫昏緫瑁佸垽" in system_prompt
        assert "鍗曠墖娈靛唴閮ㄩ€昏緫" in user_prompt
        assert kwargs["agent_name"] == "shot_director_logic_reviewer"
        return f"""瀹℃煡缁撹: 闇€瑕佽繑淇?
瑁佸垽鎽樿: 闀滃ご瀛楁娣峰叆浜虹墿鍔ㄤ綔锛屽凡鍋氭渶灏忎慨澶嶃€?
鍗曠墖娈靛鏌?
  - 鐗囨缂栧彿: F01
    閫氳繃: false
    闂:
      - 闀滃ご瀛楁娣峰叆鍔ㄤ綔銆?
纭敊璇? []
淇鍚庨暅澶存柟妗?
{repaired_output}
"""

    monkeypatch.setattr(sdi, "call_llm", fake_call_llm)

    output, runtime, report = sdi._run_shot_director_review_board(
        script="9-1 澶?鍐?鍔虫柉鑾辨柉杞﹀唴\n浜虹墿锛氫箶鐔欍€佸晢鍖楃悰",
        planner_output="",
        director_brief="",
        primary_output=primary_output,
    )

    assert runtime["agent_name"] == "shot_director_logic_reviewer"
    assert runtime["status"] == "repaired_by_logic_reviewer"
    assert "涔旂啓涓繎鏅紝杞﹀唴鍚屼晶寰晶瑙嗚" in output
    assert "濂逛綆澶寸湅娓呴」閾? not in sdi._yaml_line_field(output, "shot")
    assert "瑁佸垽淇閲囩撼: 鏄? in report


def test_shot_logic_reviewer_reports_connection_failure(monkeypatch):
    primary_output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 杞﹀唴鍛戒护鎴撮」閾?
  鑺傚: 椤归摼闈犺繎鍚庝箶鐔欒瘑鍒?
  绌洪棿杩炵画鎬ф€绘帶: 鏈墖娈垫槸涓€娈佃溅鍐呴」閾惧帇杩紱涔旂啓鍜屽晢鍖楃悰濮嬬粓鍦ㄥ悓涓€杞﹀悗鎺掔┖闂村唴锛涘崟浜洪暅鍙敼鍙樻媿鎽勪富浣擄紝涓嶄唬琛ㄥ彟涓€浜虹寮€銆?
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-2绉?
      闀滃ご浠诲姟: 鎵胯浇涔旂啓璇嗗埆椤归摼
      鎷嶆憚涓讳綋: 涔旂啓
      闀滃ご: 涔旂啓涓繎鏅紝濂逛綆澶寸湅娓呴」閾?
      鐢婚潰鍔ㄤ綔: 涔旂啓鐪嬮」閾?
      鍙拌瘝: ~
      蹇呴』鎵胯浇: 涔旂啓璁ゅ嚭椤归摼
      鍒囬暅鐐? 涔旂啓鐪嬫竻鍚庡垏鍑?
      杩炵画鎬? 椤归摼鍦ㄧ敾闈㈤噷
"""

    def fake_call_llm(*args, **kwargs):
        raise RuntimeError("绂荤嚎")

    monkeypatch.setattr(sdi, "call_llm", fake_call_llm)

    with pytest.raises(RuntimeError, match="闀滃ご閫昏緫瀹℃煡澶фā鍨嬭繛鎺ヤ笉鎴愬姛"):
        sdi._run_shot_director_review_board(
            script="9-1 澶?鍐?鍔虫柉鑾辨柉杞﹀唴\n浜虹墿锛氫箶鐔欍€佸晢鍖楃悰",
            planner_output="",
            director_brief="",
            primary_output=primary_output,
        )


def test_shot_director_workflow_trace_summarises_planner_fragments():
    planner_output = """- fragment_id: F01
  duration_target: "8s"
  dramatic_unit: "Photo reveal"
  source_script_events:
    - "Qiao Xi picks up the photo."
    - "Xiaodouding says she wants him to be daddy."
  reaction_plan: "Hold Qiao Xi reaction before flashback."
  shot_director_handoff: "Reveal the photo fully before the flashback handoff."
  director_brief: "Protect the photo reveal and emotional recoil."
- fragment_id: F02
  source_script_events:
    - "Flashback begins under the ginkgo tree."
"""

    trace = _build_shot_director_workflow_trace(
        planner_output=planner_output,
        expected_segments=["F01", "F02"],
        atmosphere_strategy="slow down before the reveal",
        director_brief="use the photo as the handoff anchor",
        aspect_ratio="9:16",
    )

    assert trace["mode"] == "three_stage_fused_pipeline"
    assert trace["stages"] == [
        "layout_task_space",
        "blocking_language_action",
        "guard_final_handoff",
    ]
    assert trace["stage_contracts"]["layout_task_space"].startswith("鎽嗕綅瀵兼紨")
    assert trace["coverage_contract_fields"] == [
        "coverage_role",
        "cut_reason",
        "companion_visibility",
        "state_delta",
        "tailframe_role",
    ]
    assert trace["fragments"][0]["fragment_id"] == "F01"
    assert trace["fragments"][0]["fragment_task"] == "Photo reveal"
    assert trace["fragments"][0]["duration_target"] == "8s"
    assert "flashback handoff" in trace["fragments"][0]["shot_director_handoff"]
    assert trace["fragments"][0]["source_event_count"] == 2
    assert "photo" in trace["fragments"][0]["source_event_preview"][0]


def test_shot_director_reads_chinese_story_planner_handoff():
    planner_output = """- 鐗囨缂栧彿: F01
  鐩爣鏃堕暱: "8-10绉?
  鏂藉伐鍓ф湰鍘熸枃浜嬩欢:
    - "涔旂啓鎷胯捣涔﹀寘銆?
    - "鐓х墖浠庝功鍖呴噷婊戣惤銆?
  鍑虹幇浜虹墿:
    - "涔旂啓"
  鍏ュ満鐘舵€? "涔旂啓鎵嬭竟鏈変功鍖咃紝鐓х墖浠嶅湪涔﹀寘鍐呫€?
  鍑哄満鐘舵€? "鐓х墖婊戣惤鍒板湴闈紝涔旂啓鐪嬪埌鐓х墖銆?
  鎵挎帴瑕佹眰: "鍙嶅簲鐣欏湪鏈灏鹃儴銆?
  鐗囨鍐呰妭濂忓垎閰? "0-3绉掞細鐓х墖婊戣惤锛?-8绉掞細涔旂啓鐪嬫竻鐓х墖骞跺畬鎴愬弽搴斻€?
  闀滃ご瀵兼紨浜ゆ帴: "鐓х墖婊戣惤蹇呴』鎷嶅畬鏁达紝鍙嶅簲鐣欏湪鏈灏鹃儴锛岀粨灏惧仠鍦ㄤ箶鐔欑湅鍒扮収鐗囥€?
"""

    trace = _build_shot_director_workflow_trace(
        planner_output=planner_output,
        expected_segments=["鐗囨01"],
        atmosphere_strategy="",
        director_brief="",
        aspect_ratio="9:16",
    )
    context = _shot_director_downstream_context(planner_output, "", "9:16")

    assert trace["fragments"][0]["fragment_id"] == "F01"
    assert trace["fragments"][0]["duration_target"] == "8-10绉?
    assert "鍙嶅簲鐣欏湪鏈灏鹃儴" in trace["fragments"][0]["reaction_plan"]
    assert "鐓х墖婊戣惤" in trace["fragments"][0]["intra_fragment_rhythm"]
    assert "鐓х墖婊戣惤蹇呴』鎷嶅畬鏁? in trace["fragments"][0]["shot_director_handoff"]
    assert trace["fragments"][0]["source_event_count"] == 2
    assert "鐩爣鏃堕暱: 8-10绉? in context
    assert "鐗囨鍐呰妭濂忓垎閰? 0-3绉? in context
    assert "鎵挎帴瑕佹眰: 鍙嶅簲鐣欏湪鏈灏鹃儴" in context
    assert "闀滃ご瀵兼紨浜ゆ帴: 鐓х墖婊戣惤蹇呴』鎷嶅畬鏁? in context
    assert "涔旂啓鎷胯捣涔﹀寘" in context
    assert "鍑哄満浜虹墿: 涔旂啓" in context
    assert "鍑哄満杩炵画鎬? 鐓х墖婊戣惤鍒板湴闈? in context


def test_rhythm_shot_director_notes_are_extracted_for_handoff():
    atmosphere_strategy = """鑺傚鎬诲悎鍚? 鐓х墖鎻ず瑕侀檷閫熴€?
缁撴瀯瑙勫垝鏂藉伐鎸囦护: 鐓х墖鎻ず鐣欏湪鍚屼竴鐗囨鍐呫€?
闀滃ご瀵兼紨鑺傚鎵ц绾︽潫: 涔旂啓杩涘叆闂洖鍓嶅繀椤诲厛瀹屾垚鍙楀嚮鍙嶅簲銆?
  - 鍒囩偣钀藉湪鐓х墖鍐呭琚娓呬箣鍚庯紝涓嶈惤鍦ㄩ殢鏈哄姩浣滀笂銆?
  - 灏惧抚蹇呴』鐢ㄧ収鐗囨壙鎺ュ埌闂洖銆?
椋庨櫓鎻愰啋: 涓嶈鏂板瑙ｉ噴鍙拌瘝銆?
"""

    notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)
    prompt = _rhythm_shot_director_notes_prompt(atmosphere_strategy)

    assert "涔旂啓杩涘叆闂洖鍓嶅繀椤诲厛瀹屾垚鍙楀嚮鍙嶅簲" in notes
    assert "鍒囩偣钀藉湪鐓х墖鍐呭琚娓呬箣鍚? in notes
    assert "鑺傚鎬绘帶缁欓暅澶村婕旂殑鎵ц绾︽潫" in prompt
    assert "灏惧抚" in prompt


def test_shot_director_downstream_context_includes_rhythm_shot_notes():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "Qiao Xi sees the photo."
"""
    atmosphere_strategy = """鑺傚鎬诲悎鍚? 鐓х墖鎻ず瑕侀檷閫熴€?
闀滃ご瀵兼紨鑺傚鎵ц绾︽潫: 鍙嶅簲褰掍箶鐔欙紱鐓х墖璇绘竻鍚庡啀鍒囥€?
缁撴瀯瑙勫垝鏂藉伐鎸囦护: 闂洖鍓嶄笉鎷嗐€?
"""

    context = _shot_director_downstream_context(planner_output, atmosphere_strategy, "9:16")

    assert "[鑺傚鎬绘帶缁欓暅澶村婕旂殑鎵ц绾︽潫]" in context
    assert "鍙嶅簲褰掍箶鐔? in context
    assert "[Atmosphere Excerpt]" not in context
    assert "缁撴瀯瑙勫垝鏂藉伐鎸囦护" not in context


def test_shot_director_builds_signal_based_shot_library_tasks():
    planner_output = """- 鐗囨缂栧彿: F01
  鏂藉伐鍓ф湰鍘熸枃浜嬩欢:
    - "涔旂啓鍐茶繘鐢垫锛屾挒鍒板晢鍖楃悰銆?
    - "鍟嗗寳鐞涘懡浠ゅス鍋滀笅锛屼箶鐔欎笉鏁㈢珛鍒诲洖绛斻€?
    - "鐓х墖浠庝功鍖呴噷婊戣惤锛屼箶鐔欑湅娓呯収鐗囧唴瀹广€?
  鍑哄満鐘舵€? "鐢垫闂ㄧ户缁悎鎷紝涔旂啓鐩潃鐓х墖鍋滀綇銆?
"""
    atmosphere_strategy = "闀滃ご瀵兼紨鑺傚鎵ц绾︽潫: 鍛戒护鍙ュ悗缁欏惉鑰呭弽搴旓紱纰版挒鍚庡厛缁欎箶鐔欏彈鍑诲弽搴旓紝鐓х墖鐪嬫竻鍚庡啀鍒囷紝灏惧抚鐢ㄧ収鐗囨壙鎺ャ€?

    card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief="淇濇姢鐓х墖鎻ず锛屼笉瑕佹妸纰版挒鎷嶆垚鏆ф槯銆?,
        aspect_ratio="9:16",
    )

    assert "[闀滃ご搴撹皟鐢ㄤ换鍔″崟]" in card
    assert "impact_reaction" in card
    assert "long_dialogue_coverage" in card
    assert "reveal_insert_reaction" in card
    assert "door_threshold_continuity" in card
    assert "tailframe_handoff" in card
    assert "璋冪敤鍙楀嚮/纰版挒闀滃ご搴? in card
    assert "璋冪敤瀵圭櫧瑕嗙洊闀滃ご搴? in card
    assert "涓嶅緱涓€涓浐瀹氭満浣嶅悆瀹屾暣闀垮彴璇? in card
    assert "蹇呴』鑷冲皯瀹夋帓涓€娆¤璇濊€呭鐨勭敾闈㈡壙杞藉彴璇嶅悗鍗婂彞" in card
    assert "璋冪敤淇℃伅鎻ず闀滃ご搴? in card
    assert "蹇呴』妫€绱㈢殑鐭ヨ瘑" in card
    assert "SHOT-DIALOGUE-PAUSE-001" in card
    assert "BLOCKING-REACTION-COVERAGE-002" in card
    assert "BLOCKING-DIALOGUE-FIDELITY-003" in card
    assert "SHOT-DIALOGUE-COVERAGE-001" in card
    assert "寮哄埗钀藉湴" in card


def test_shot_director_signal_profile_routes_knowledge_retrieval():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "涔旂啓鍐茶繘鐢垫锛屾挒鍒板晢鍖楃悰銆?
    - "鍟嗗寳鐞涘懡浠ゅス鍋滀笅锛屼箶鐔欑湅娓呯収鐗囥€?
"""

    profile = _build_shot_director_signal_retrieval_profile(
        planner_output=planner_output,
        atmosphere_strategy="闀滃ご瀵兼紨鑺傚鎵ц绾︽潫: 闀垮鐧介渶瑕佸惉鑰呭弽搴旓紝灏惧抚鍋滃湪鐓х墖銆?,
        director_brief="鍘嬩綇纰版挒娴极鍖栭闄╋紝淇濇寔鐢垫绌洪棿杩炵画銆?,
        aspect_ratio="9:16",
    )

    assert "elevator" in profile["scene_types"]
    assert "collision" in profile["events"]
    assert "dialogue" in profile["events"]
    assert "romanticize_collision" in profile["risks"]
    assert "dialogue_integrity" in profile["risks"]
    assert "shot_library_routing" in profile["signals"]
    assert "editing_ellipsis" in profile["signals"]
    assert "shot_variety" in profile["signals"]
    assert "rhythm_alignment" in profile["signals"]
    assert "long_dialogue_coverage" in profile["reusable_pattern"]
    assert "SHOT-DIALOGUE-COVERAGE-001" in profile["reusable_pattern"]
    assert "SHOT-DIALOGUE-PAUSE-001" in profile["reusable_pattern"]
    assert "shot_library_routing" in profile["tags"]
    assert "multicam_strategy" in profile["tags"]
    assert "shot_variation" in profile["tags"]
    assert "upstream_director_constraint" in profile["tags"]
    assert "coverage_role" in profile["tags"]
    assert "relation_shot" in profile["tags"]
    assert "reaction_shot" in profile["tags"]
    assert "tailframe_handoff" in profile["tags"]
    assert "no_pseudo_viewpoint" in profile["tags"]
    assert "蹇呴』鎶婃绱㈠埌鐨勫壀杈?闀滃ご搴撹鍒欒浆鎴愰暅澶淬€佸垏闀滅偣銆佽繛缁€с€佸０闊筹紝涓嶅緱鍙啓鍘熷垯" in profile["visual_constraints"]
    assert "蹇呴』浼樺厛浣跨敤鏈墖娈靛墽鎯呬俊鍙峰尮閰嶅埌鐨?CASE 妗堜緥鍜岃鍒欏崱" in profile["visual_constraints"]
    assert profile["max_chunks_per_source"] == 1


def test_shot_director_variety_guard_flags_repeated_shot_language():
    output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 闀垮鐧藉帇杩?
  鑺傚: 鍘嬭揩閫掕繘
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-2绉?
      闀滃ご: 姝ｉ潰涓櫙
      鍙拌瘝: "浣犺В閲娿€?
    - 闀滃ご缂栧彿: F01-S02
      鏃堕暱: 2-4绉?
      闀滃ご: 姝ｉ潰涓櫙
      鍙拌瘝: ~
    - 闀滃ご缂栧彿: F01-S03
      鏃堕暱: 4-6绉?
      闀滃ご: 姝ｉ潰涓櫙
      鍙拌瘝: ~
"""

    issues = _validate_shot_director_variety(output)

    assert issues
    assert "杩炵画浣跨敤鍚屼竴绉嶉暅澶磋瑷€" in issues[0] or "杩炵画涓変釜闀滃ご閲嶅" in issues[0]


def test_shot_director_variety_guard_allows_explicit_rhythm_exception():
    output = """- 鐗囨缂栧彿: F01
  鐗囨浠诲姟: 鍘嬩綇娌夐粯
  鑺傚: 鑺傚鎬绘帶瑕佹眰鍥哄畾鏈轰綅鍘嬩綇涓嶅垏
  闀滃ご鍒楄〃:
    - 闀滃ご缂栧彿: F01-S01
      鏃堕暱: 0-2绉?
      闀滃ご: 姝ｉ潰涓櫙
    - 闀滃ご缂栧彿: F01-S02
      鏃堕暱: 2-4绉?
      闀滃ご: 姝ｉ潰涓櫙
    - 闀滃ご缂栧彿: F01-S03
      鏃堕暱: 4-6绉?
      闀滃ご: 姝ｉ潰涓櫙
"""

    assert _validate_shot_director_variety(output) == []


def test_shot_library_signal_task_card_keeps_rhythm_as_constraints_without_overriding_boundaries():
    planner_output = """- 鐗囨缂栧彿: F01
  鏂藉伐鍓ф湰鍘熸枃浜嬩欢:
    - "涔旂啓鍐茶繘鐢垫锛屾挒鍒板晢鍖楃悰銆?
  鍑哄満鐘舵€? "涔旂啓绔欏湪鐢垫闂ㄥ唴渚э紝鍟嗗寳鐞涙尅浣忛棬鍙ｃ€?
- 鐗囨缂栧彿: F02
  鏂藉伐鍓ф湰鍘熸枃浜嬩欢:
    - "涔旂啓鐪嬫竻鐓х墖鍐呭锛屾劊鍦ㄥ師鍦般€?
  鍑哄満鐘舵€? "鐓х墖鐣欏湪涔旂啓鎵嬮噷锛岃绾挎壙鎺ュ埌涓嬩竴娈点€?
"""
    atmosphere_strategy = """鑺傚鎬诲悎鍚? F01 纰版挒鍚庣煭鏆傚仠椤匡紝F02 鐓х墖鎻ず闄嶉€熴€?
闀滃ご瀵兼紨鑺傚鎵ц绾︽潫: F01 鍙帇浣忓彈鍑诲弽搴旓紱F02 蹇呴』鐓х墖璇绘竻鍚庡啀鍒囷紝涓嶈兘鎶婄収鐗囨彁鍓嶅鍥?F01銆?
鎷嗙墖杈圭晫寤鸿: 淇濇寔 F01/F02 杈圭晫锛岄暅澶村彧鍋氳妭濂忔柦宸ャ€?
"""

    card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief="涓ユ牸鎸夋媶鐗囪竟鐣屾墽琛岋紝涓嶆柊澧炲墽鏈鍔ㄤ綔銆?,
        aspect_ratio="9:16",
    )

    assert "鑺傚鎬绘帶绾︽潫:" in card
    assert "鍏堣涓婃父瀵兼紨璧勪骇" in card
    assert "涓嶈兘鎵╁啓鏂板墽鎯? in card
    assert "- 鐗囨缂栧彿: F01" in card
    assert "- 鐗囨缂栧彿: F02" in card
    assert "涔旂啓鍐茶繘鐢垫锛屾挒鍒板晢鍖楃悰" in card
    assert "涔旂啓鐪嬫竻鐓х墖鍐呭锛屾劊鍦ㄥ師鍦? in card
    assert card.index("- 鐗囨缂栧彿: F01") < card.index("- 鐗囨缂栧彿: F02")
    assert "F02 蹇呴』鐓х墖璇绘竻鍚庡啀鍒? in card
    assert card.count("- 鐗囨缂栧彿:") == 2


def test_shot_library_signal_task_card_asserts_long_dialogue_and_repeated_camera_rules():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "鍟嗗寳鐞涚敤涓€鏁存楂樺帇鍛戒护璐ㄩ棶涔旂啓銆?
    - "涔旂啓娌夐粯鍥為伩锛岀數姊棬缁х画鍚堟嫝銆?
"""
    atmosphere_strategy = "闀滃ご瀵兼紨鑺傚鎵ц绾︽潫: 闀垮鐧藉唴閮ㄥ繀椤诲垏缁欏惉鑰呭弽搴旓紝閬垮厤鍚屼竴姝ｅ弽鎵撴満浣嶉噸澶嶅悆瀹屾暣鍙ャ€?

    card = _shot_library_signal_task_card(
        planner_output=planner_output,
        atmosphere_strategy=atmosphere_strategy,
        director_brief="瀵圭櫧鍘嬭揩鎰熼€掕繘锛屼絾涓嶈鏈烘閲嶅鍥哄畾鏈轰綅銆?,
        aspect_ratio="9:16",
    )

    assert "long_dialogue_coverage" in card
    assert "authority_pressure" in card
    assert "璋冪敤瀵圭櫧瑕嗙洊闀滃ご搴? in card
    assert "鍚屼晶鍚€呭弽搴?杩囪偐" in card
    assert "涓嶅緱涓€涓浐瀹氭満浣嶅悆瀹屾暣闀垮彴璇? in card
    assert "cut_point 鍐欐槑鍙拌瘝鏂偣鎴栧帇杩惤鐐? in card
    assert "璋冪敤鏉冨姏鍘嬭揩闀滃ご搴? in card
    assert "涓嶅緱鍏ㄧ▼鍧囬€熸鍙嶆墦" in card


def test_legacy_rhythm_shot_director_notes_are_still_extracted():
    atmosphere_strategy = """rhythm_diagnosis: reveal is too fast.
shot_director_notes: reaction belongs to Qiao Xi; cut after the photo is readable.
construction_notes: no split before the flashback.
"""

    notes = _extract_rhythm_shot_director_notes(atmosphere_strategy)

    assert "reaction belongs to Qiao Xi" in notes


def test_planner_source_event_context_keeps_only_selected_fragments():
    planner_output = """- fragment_id: F01
  source_script_events:
    - "Qiao Xi reads the photo."
  director_brief: "Protect the photo reveal."
- fragment_id: F02
  source_script_events:
    - "Flashback begins under the ginkgo tree."
"""

    context = _planner_source_event_context(planner_output, ["F02"])

    assert "F02 source_script_events" in context
    assert "Flashback begins" in context
    assert "Qiao Xi reads the photo" not in context


def test_shot_director_does_not_upload_raw_reference_images_without_scene_manifest():
    state = {"reference_image_b64s": ["scene-a", "person-a"]}

    assert _reference_images(state) == []


def test_shot_director_uploads_only_scene_layout_references():
    state = {
        "reference_image_b64s": ["person-a", "layout-a", "grid-a", "annotated-a", "raw-scene-a"],
        "reference_image_manifest": [
            {"label": "@鍥剧墖1", "role": "character", "purpose": "涓昏浜虹墿"},
            {"label": "@鍥剧墖2", "role": "scene_layout", "purpose": "鐢垫鍙ｅ満鏅刊瑙嗗竷灞€鍥撅紝鍚汉鐗╀綅缃拰绉诲姩杞ㄨ抗"},
            {"label": "@鍥剧墖3", "type": "scene_card", "purpose": "鍦烘櫙涔濆鏍兼満浣嶅浘"},
            {"label": "@鍥剧墖4", "role": "annotated_scene_layout", "purpose": "鐢ㄦ埛鏍囨敞鍚庣殑淇鍥?},
            {"label": "@鍥剧墖5", "asset_type": "scene", "purpose": "鍘熷鍦烘櫙鍙傝€冨浘"},
        ],
        "scene_layout_annotations": [{"scene_number": "1", "summary": "浜虹墿鏍囩偣: 涔旂啓(0.30,0.50)"}],
    }

    assert _reference_images(state) == ["layout-a", "grid-a", "annotated-a"]
    assert [item["label"] for _image, item in _scene_reference_items(state)] == ["@鍥剧墖2", "@鍥剧墖3", "@鍥剧墖4"]

    prompt = _reference_image_manifest_prompt(state)
    assert "[Scene Layout Reference Images]" in prompt
    assert "@鍥剧墖2" in prompt
    assert "绉诲姩杞ㄨ抗" in prompt
    assert "@鍥剧墖3" in prompt
    assert "@鍥剧墖4" in prompt
    assert "涔旂啓(0.30,0.50)" in prompt
    assert "涓昏浜虹墿" not in prompt
    assert "鍘熷鍦烘櫙鍙傝€冨浘" not in prompt


def test_shot_director_merges_completed_background_scene_cards(monkeypatch):
    monkeypatch.setenv("AIDIRECTOR_SCENE_CARD_WAIT_SECONDS", "0")
    monkeypatch.setattr(
        sdi,
        "load_state",
        lambda: {
            "scene_card_status": "done",
            "reference_image_b64s": ["layout-a"],
            "reference_image_manifest": [
                {"role": "scene_layout", "purpose": "generated scene layout"},
            ],
            "agent_outputs": {"scene_card_status": "done"},
        },
    )

    merged = sdi._await_scene_card_generation(
        {
            "scene_card_status": "running",
            "reference_image_b64s": ["raw-scene"],
            "reference_image_manifest": [{"purpose": "raw scene reference"}],
            "agent_outputs": {"scene_card_status": "running"},
        }
    )

    assert _reference_images(merged) == ["layout-a"]
    assert merged["scene_card_status"] == "done"


def test_split_fragment_mode_can_pass_scene_reference_images_when_explicit(monkeypatch):
    captured_images: list[list[str] | None] = []

    def fake_call_llm(**kwargs):
        captured_images.append(kwargs.get("images_base64"))
        return "- 鐗囨缂栧彿: F01\n  鐗囨浠诲姟: 寤虹珛绌洪棿\n  闀滃ご鍒楄〃: []\n"

    monkeypatch.setattr(sdi, "call_llm", fake_call_llm)

    output, runtime = _call_stage_split_by_fragment(
        stage_key="shot_director",
        system_prompt="system",
        expected_segments=["F01"],
        planner_output="- fragment_id: F01\n  source_script_events:\n    - A enters.\n",
        aspect_ratio="9:16",
        contract_output="",
        prompt_builder=lambda _fid, context, _contract: context,
        images_base64=["layout-a"],
    )

    assert "鐗囨缂栧彿: F01" in output
    assert runtime["mode"] == "split_by_fragment"
    assert captured_images == [["layout-a"]]


def test_shot_director_stages_do_not_upload_scene_reference_images():
    assert sdi._shot_director_stage_images("shot_director_layout", ["layout-a"]) is None
    assert sdi._shot_director_stage_images("shot_director_blocking", ["layout-a"]) is None
    assert sdi._shot_director_stage_images("shot_director_guard", ["layout-a"]) is None


def test_segment_shot_director_uses_text_scene_references_without_uploading_images(monkeypatch):
    captured: dict[str, object] = {}

    def fake_three_stage(**kwargs):
        captured["images_base64"] = kwargs.get("images_base64")
        captured["scene_reference_context"] = kwargs.get("scene_reference_context")
        return (
            "- 鐗囨缂栧彿: F01\n  鐗囨浠诲姟: 寤虹珛绌洪棿\n  闀滃ご鍒楄〃: []\n",
            {"elapsed_seconds": 0.1},
            {"final": {"retrieval_mode": "stub"}},
            {"final": "- 鐗囨缂栧彿: F01\n  鐗囨浠诲姟: 寤虹珛绌洪棿\n  闀滃ご鍒楄〃: []\n"},
        )

    monkeypatch.setattr(sdi, "_run_shot_director_three_stage", fake_three_stage)
    monkeypatch.setattr(sdi, "_persist_update", lambda state, update: {**state, **update})
    monkeypatch.setattr(sdi, "_collect_shot_director_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr(sdi, "_hard_shot_director_issues", lambda issues: [])
    monkeypatch.setattr(
        sdi,
        "_run_shot_director_review_board",
        lambda **kwargs: (
            kwargs["primary_output"],
            {"agent_name": "shot_director_logic_reviewer", "status": "accepted_primary"},
            "review-ok",
        ),
    )

    result = sdi.run_shot_director_for_segment(
        {
            "script": "涔旂啓璧板埌鐢垫闂ㄥ彛銆?,
            "aspect_ratio": "9:16",
            "scene_context_brief": "绌洪棿绾︽潫锛氱數姊棬鍦ㄧ敾闈㈠彸渚э紝璧板粖涓嶈兘鏂板鍓嶅彴銆?,
            "agent_outputs": {"story_planner": "- fragment_id: F01\n  source_script_events:\n    - 涔旂啓璧板埌鐢垫闂ㄥ彛銆俓n"},
            "reference_image_b64s": ["person-a", "layout-a", "annotated-a", "prop-a"],
            "reference_image_manifest": [
                {"role": "character", "purpose": "涓昏浜虹墿"},
                {"role": "scene_layout", "purpose": "鐢垫鍙ｄ刊瑙嗗竷灞€鍥?},
                {"role": "annotated_scene_layout", "purpose": "鐢ㄦ埛鏍囨敞鍚庣殑淇鍥?},
                {"role": "prop", "purpose": "閬撳叿"},
            ],
            "scene_layout_annotations": [{"scene_number": "1", "summary": "浜虹墿鏍囩偣: 涔旂啓(0.30,0.50)"}],
            "knowledge_metadata": {},
            "segment_names": ["F01"],
            "total_segments": 1,
        },
        1,
        force=True,
    )

    assert "shot_director_review_fragment_F01" in result["agent_outputs"]
    assert "shot_director_guard_fragment_F01" in result["agent_outputs"]
    assert captured["images_base64"] is None
    assert "鍦烘櫙鍒嗘瀽甯堢粰闀滃ご瀵兼紨鐨勭┖闂寸害鏉? in str(captured["scene_reference_context"])
    assert "璧板粖涓嶈兘鏂板鍓嶅彴" in str(captured["scene_reference_context"])
    assert "鐢ㄦ埛鏍囨敞鍚庣殑淇鍥? in str(captured["scene_reference_context"])
    assert "涔旂啓(0.30,0.50)" in str(captured["scene_reference_context"])
    assert result["agent_outputs"]["shot_director"].startswith("- 鐗囨缂栧彿: F01")
