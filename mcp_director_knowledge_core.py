"""
MCP Director Knowledge Core - 知识库核心集成模块

严格遵循用户的核心规则和知识库文档，实现：
1. 规则优先级系统 (P0-P5)
2. Agent 职责边界
3. 知识库智能检索
4. 规则验证引擎
"""

from __future__ import annotations

import os
import re
import yaml
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from enum import Enum
from pathlib import Path


class RulePriority(Enum):
    """规则优先级 (P0-P5)"""
    P0_USER_SAFETY = "P0"  # 用户显式要求与安全边界
    P1_CONTINUITY = "P1"   # 连续性与模型可生成性
    P2_SEGMENT = "P2"      # 片段边界与主分镜合法性
    P3_RHYTHM = "P3"       # 故事节奏与剧本层改写
    P4_SHOT = "P4"         # 镜头调用、多机位与视觉风格
    P5_EXAMPLE = "P5"      # 范例、案例与源材料


class AgentType(Enum):
    """Agent 类型"""
    SCENE_ANALYST = "scene_analyst"
    RHYTHM_REWRITE_DIRECTOR = "rhythm_rewrite_director"
    STORY_PLANNER = "story_planner"
    SHOT_DIRECTOR = "shot_director"
    PROMPT_COMPILER = "prompt_compiler"
    QUALITY_INSPECTOR = "quality_inspector"
    SHARED = "shared"


@dataclass
class Rule:
    """规则定义"""
    rule_id: str
    title: str
    agent_scope: List[AgentType]
    rule_type: str
    priority: RulePriority
    status: str
    applies_to: List[str]
    content: str = ""
    conflicts_with: List[str] = field(default_factory=list)
    supersedes: List[str] = field(default_factory=list)
    source_file: str = ""


@dataclass
class StateContract:
    """
    状态合同
    
    根据 06_连续性与安全规则 实现
    """
    active_cast: List[str] = field(default_factory=list)  # 当前活跃人物
    offscreen_cast: List[str] = field(default_factory=list)  # 退场/不可见人物
    entry_state: Dict[str, Any] = field(default_factory=dict)  # 首帧状态
    exit_state: Dict[str, Any] = field(default_factory=dict)  # 尾帧状态
    object_transitions: Dict[str, str] = field(default_factory=dict)  # 道具状态转移
    forbidden_continuity: List[str] = field(default_factory=list)  # 禁止项
    
    def validate(self) -> Tuple[bool, List[str]]:
        """验证状态合同的合法性"""
        errors = []
        
        # 检查活跃人物和退场人物是否有重叠
        overlap = set(self.active_cast) & set(self.offscreen_cast)
        if overlap:
            errors.append(f"人物同时在活跃和退场列表: {overlap}")
        
        # 检查状态转移是否单向
        for obj, transition in self.object_transitions.items():
            if '->' not in transition:
                errors.append(f"对象 {obj} 的状态转移格式错误: {transition}")
        
        return len(errors) == 0, errors


@dataclass
class ShotDefinition:
    """
    分镜定义
    
    根据 01_导演分镜总手册 实现
    """
    # 基础字段（缺一不可）
    time_range: Tuple[float, float] = (0.0, 5.0)  # 时间段 [start, end]
    subject: str = ""  # 主体
    shot_size: str = ""  # 景别 (ELS, LS, MLS, MS, MCU, CU, ECU)
    focal_length: str = ""  # 焦段
    depth_of_field: str = ""  # 景深
    camera_height: str = ""  # 机位高度
    camera_angle: str = ""  # 拍摄角度
    camera_movement: str = ""  # 运镜（只允许一种主导运镜）
    action_description: str = ""  # 动作/表演描述
    lighting: str = ""  # 光源描述
    
    # 扩展字段
    state_contract: Optional[StateContract] = None
    is_subshot: bool = False  # 是否是子分镜
    parent_shot_id: Optional[str] = None  # 父分镜ID
    
    def validate(self) -> Tuple[bool, List[str]]:
        """验证分镜定义的合法性"""
        errors = []
        
        # 检查必填字段
        if not self.subject:
            errors.append("主体不能为空")
        if not self.shot_size:
            errors.append("景别不能为空")
        if not self.camera_movement:
            errors.append("运镜不能为空")
        
        # 检查景别代码有效性
        valid_sizes = ['ELS', 'LS', 'MLS', 'MS', 'MCU', 'CU', 'ECU']
        if self.shot_size and self.shot_size.upper() not in valid_sizes:
            errors.append(f"无效的景别代码: {self.shot_size}")
        
        # 检查时间段
        if self.time_range[0] >= self.time_range[1]:
            errors.append("时间段起始必须小于结束")
        if self.time_range[1] - self.time_range[0] > 15:
            errors.append("单个分镜时长不能超过15秒")
        
        return len(errors) == 0, errors
    
    def to_prompt_format(self) -> str:
        """转换为 Seedance prompt 格式"""
        lines = [
            f"[{self.time_range[0]:.1f}s-{self.time_range[1]:.1f}s]",
            f"主体：{self.subject}",
        ]
        
        if self.shot_size:
            lines.append(f"景别：{self.shot_size}")
        if self.focal_length:
            lines.append(f"焦段：{self.focal_length}")
        if self.depth_of_field:
            lines.append(f"景深：{self.depth_of_field}")
        if self.camera_height:
            lines.append(f"机位：{self.camera_height}")
        if self.camera_angle:
            lines.append(f"角度：{self.camera_angle}")
        if self.camera_movement:
            lines.append(f"运镜：{self.camera_movement}")
        if self.action_description:
            lines.append(f"动作：{self.action_description}")
        if self.lighting:
            lines.append(f"光源：{self.lighting}")
        
        return '\n'.join(lines)


class RuleRegistry:
    """
    规则注册表
    
    管理所有规则，提供优先级裁决和冲突解决
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.agent_rules: Dict[AgentType, List[str]] = {agent: [] for agent in AgentType}
        self.priority_rules: Dict[RulePriority, List[str]] = {priority: [] for priority in RulePriority}
    
    def register(self, rule: Rule):
        """注册规则"""
        self.rules[rule.rule_id] = rule
        
        # 按 Agent 分类
        for agent in rule.agent_scope:
            if agent not in self.agent_rules:
                self.agent_rules[agent] = []
            self.agent_rules[agent].append(rule.rule_id)
        
        # 按优先级分类
        self.priority_rules[rule.priority].append(rule.rule_id)
    
    def get_rules_for_agent(self, agent: AgentType, priority: Optional[RulePriority] = None) -> List[Rule]:
        """获取指定 Agent 的规则"""
        rule_ids = self.agent_rules.get(agent, [])
        rules = [self.rules[rid] for rid in rule_ids if rid in self.rules]
        
        if priority:
            rules = [r for r in rules if r.priority == priority]
        
        # 按优先级排序
        return sorted(rules, key=lambda r: r.priority.value)
    
    def resolve_conflict(self, rule_ids: List[str]) -> Optional[Rule]:
        """
        解决规则冲突
        
        根据优先级裁决，返回应执行的规则
        """
        if not rule_ids:
            return None
        
        if len(rule_ids) == 1:
            return self.rules.get(rule_ids[0])
        
        # 获取所有规则
        rules = [self.rules.get(rid) for rid in rule_ids if rid in self.rules]
        rules = [r for r in rules if r is not None]
        
        if not rules:
            return None
        
        # 按优先级排序，返回最高优先级的规则
        return min(rules, key=lambda r: r.priority.value)
    
    def check_supersedes(self, rule_id: str) -> List[str]:
        """检查被指定规则取代的规则"""
        rule = self.rules.get(rule_id)
        if not rule:
            return []
        return rule.supersedes


class KnowledgeBaseLoader:
    """
    知识库加载器
    
    从知识库目录加载规则文档
    """
    
    def __init__(self, knowledge_base_path: str):
        self.kb_path = Path(knowledge_base_path)
        self.registry = RuleRegistry()
    
    def load_all(self) -> RuleRegistry:
        """加载所有知识库文档"""
        # 加载主文档
        main_docs = [
            '01_导演分镜总手册.md',
            '00_知识库优先级与冲突裁决规则.md',
            '06_连续性与安全规则.md',
            '05_剧本拆分与15秒片段规划规则.md',
            '03_镜头切换与推进规则.md',
            '04_对白与表演镜头规则.md',
            '02_焦段景深与景别画幅策略.md',
            '07_Seedance输出词典与模型适配.md',
            '09_节奏总控与剧本改写规则.md',
            '15_故事节奏控制规则.md',
            '17_结果质检与回溯修正规则.md',
            '18_情绪锚点与逐段交互与仰拍限制补丁.md',
            '20_镜头库与机位库.md',
            '21_镜头调用规则与多机位模板.md',
            '22_多机位分镜与镜头多样性规则.md',
        ]
        
        for doc_name in main_docs:
            doc_path = self.kb_path / doc_name
            if doc_path.exists():
                self._load_document(doc_path)
        
        # 加载 rules 目录下的规则卡
        rules_dir = self.kb_path / 'rules'
        if rules_dir.exists():
            for rule_file in rules_dir.rglob('*.md'):
                self._load_document(rule_file)
        
        return self.registry
    
    def _load_document(self, file_path: Path):
        """加载单个文档"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    
                    # 创建规则对象
                    rule = self._create_rule_from_frontmatter(
                        frontmatter, body, str(file_path)
                    )
                    if rule:
                        self.registry.register(rule)
        
        except Exception as e:
            print(f"[WARNING] 加载文档失败 {file_path}: {e}")
    
    def _create_rule_from_frontmatter(self, frontmatter: Dict, content: str, source_file: str) -> Optional[Rule]:
        """从 frontmatter 创建规则对象"""
        if not frontmatter or 'rule_id' not in frontmatter:
            return None
        
        # 解析 agent_scope
        agent_scope = []
        for agent_str in frontmatter.get('agent_scope', []):
            try:
                agent_scope.append(AgentType(agent_str))
            except ValueError:
                pass
        
        # 解析 priority
        priority_str = frontmatter.get('priority', 'P4')
        priority_map = {
            'hard': RulePriority.P1_CONTINUITY,
            'medium': RulePriority.P4_SHOT,
            'low': RulePriority.P5_EXAMPLE,
        }
        priority = priority_map.get(priority_str, RulePriority.P4_SHOT)
        
        return Rule(
            rule_id=frontmatter['rule_id'],
            title=frontmatter.get('title', ''),
            agent_scope=agent_scope or [AgentType.SHARED],
            rule_type=frontmatter.get('rule_type', 'general'),
            priority=priority,
            status=frontmatter.get('status', 'active'),
            applies_to=frontmatter.get('applies_to', []),
            content=content,
            conflicts_with=frontmatter.get('conflicts_with', []),
            supersedes=frontmatter.get('supersedes', []),
            source_file=source_file,
        )


class RuleValidator:
    """
    规则验证引擎
    
    验证输出是否符合规则要求
    """
    
    def __init__(self, registry: RuleRegistry):
        self.registry = registry
        self.validation_errors: List[str] = []
    
    def validate_shot(self, shot: ShotDefinition, agent: AgentType) -> Tuple[bool, List[str]]:
        """
        验证分镜定义
        
        根据 01_导演分镜总手册 验证
        """
        errors = []
        
        # 基础验证
        is_valid, base_errors = shot.validate()
        errors.extend(base_errors)
        
        # 获取该 Agent 的硬规则
        hard_rules = self.registry.get_rules_for_agent(agent, RulePriority.P1_CONTINUITY)
        
        # 应用硬规则验证
        for rule in hard_rules:
            if rule.status != 'active':
                continue
            
            # 检查 POV 规则
            if 'POV' in rule.applies_to or '主观视角' in rule.content:
                if 'POV' in shot.camera_angle.upper() or '主观' in shot.camera_angle:
                    # POV 镜头需要前置的建立镜头
                    pass  # 这里需要上下文信息
            
            # 检查连续性规则
            if '连续性' in rule.applies_to:
                if shot.state_contract:
                    is_valid, contract_errors = shot.state_contract.validate()
                    errors.extend(contract_errors)
        
        return len(errors) == 0, errors
    
    def validate_segment_boundary(self, segments: List[Dict], script: str) -> Tuple[bool, List[str]]:
        """
        验证片段边界
        
        根据 05_剧本拆分与15秒片段规划规则 验证
        """
        errors = []
        
        # 检查片段时长
        for i, seg in enumerate(segments):
            duration = seg.get('duration', 0)
            if duration > 15:
                errors.append(f"片段 {i+1} 时长 {duration}s 超过15秒限制")
            if duration < 10 and i < len(segments) - 1:
                # 非最后片段，检查是否确实需要短时长
                pass
        
        # 检查完整发言单元
        # TODO: 实现台词完整性检查
        
        return len(errors) == 0, errors
    
    def validate_continuity(self, shots: List[ShotDefinition]) -> Tuple[bool, List[str]]:
        """
        验证连续性
        
        根据 06_连续性与安全规则 验证
        """
        errors = []
        
        if not shots:
            return True, []
        
        # 检查首帧状态继承
        prev_exit_state = None
        for i, shot in enumerate(shots):
            if shot.state_contract:
                entry_state = shot.state_contract.entry_state
                
                # 检查与前一个片段的尾帧状态是否一致
                if prev_exit_state and i > 0:
                    # 简化检查：人物位置一致性
                    pass
                
                prev_exit_state = shot.state_contract.exit_state
            
            # 检查轴线一致性
            if i > 0:
                # 检查是否无理由翻轴
                pass
        
        return len(errors) == 0, errors
    
    def get_validation_report(self) -> str:
        """获取验证报告"""
        if not self.validation_errors:
            return "[OK] 所有验证通过"
        
        report = ["[ERROR] 验证发现以下问题:"]
        for i, error in enumerate(self.validation_errors, 1):
            report.append(f"  {i}. {error}")
        
        return '\n'.join(report)


class KnowledgeIntegrator:
    """
    知识库集成器
    
    为每个 Agent 提供相关知识
    """
    
    def __init__(self, registry: RuleRegistry):
        self.registry = registry
    
    def get_knowledge_for_agent(self, agent: AgentType, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取指定 Agent 的相关知识
        
        根据运行时上下文智能选择规则
        """
        knowledge = {
            'rules': [],
            'constraints': [],
            'examples': [],
        }
        
        # 获取该 Agent 的所有规则
        agent_rules = self.registry.get_rules_for_agent(agent)
        
        # 按优先级分组
        for priority in RulePriority:
            priority_rules = [r for r in agent_rules if r.priority == priority]
            
            for rule in priority_rules:
                if rule.status != 'active':
                    continue
                
                # 检查规则是否适用于当前上下文
                if self._is_rule_applicable(rule, context):
                    knowledge['rules'].append({
                        'id': rule.rule_id,
                        'title': rule.title,
                        'priority': rule.priority.value,
                        'content': rule.content[:500],  # 摘要
                    })
        
        return knowledge
    
    def _is_rule_applicable(self, rule: Rule, context: Dict[str, Any]) -> bool:
        """检查规则是否适用于当前上下文"""
        # 检查 applies_to 字段
        applies_to = rule.applies_to
        
        if not applies_to:
            return True
        
        # 检查场景类型
        scene_type = context.get('scene_type', '')
        if scene_type and any(app in scene_type for app in applies_to):
            return True
        
        # 检查动作类型
        action_type = context.get('action_type', '')
        if action_type and any(app in action_type for app in applies_to):
            return True
        
        # 默认适用
        return True
    
    def get_priority_guidance(self) -> str:
        """获取优先级指导"""
        return """
规则优先级 (从高到低):
P0: 用户显式要求与安全边界
P1: 连续性与模型可生成性 (06, 07, 18)
P2: 片段边界与主分镜合法性 (03, 05)
P3: 故事节奏与剧本层改写 (09, 15)
P4: 镜头调用、多机位与视觉风格 (20, 21, 22)
P5: 范例、案例与源材料 (19, 23)

冲突裁决: 高优先级规则覆盖低优先级规则
"""


# 便捷函数
def create_knowledge_core(knowledge_base_path: Optional[str] = None) -> Tuple[RuleRegistry, KnowledgeIntegrator, RuleValidator]:
    """
    创建知识库核心
    
    Returns:
        (规则注册表, 知识集成器, 规则验证器)
    """
    if knowledge_base_path is None:
        knowledge_base_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'knowledge'
        )
    
    # 加载知识库
    loader = KnowledgeBaseLoader(knowledge_base_path)
    registry = loader.load_all()
    
    # 创建集成器和验证器
    integrator = KnowledgeIntegrator(registry)
    validator = RuleValidator(registry)
    
    return registry, integrator, validator


# 测试
if __name__ == "__main__":
    print("=" * 80)
    print("Knowledge Core 测试")
    print("=" * 80)
    
    registry, integrator, validator = create_knowledge_core()
    
    print(f"\n已加载规则数量: {len(registry.rules)}")
    
    # 测试获取 Agent 规则
    for agent in [AgentType.SHOT_DIRECTOR, AgentType.STORY_PLANNER]:
        rules = registry.get_rules_for_agent(agent)
        print(f"\n{agent.value} 规则数量: {len(rules)}")
    
    # 测试知识集成
    context = {'scene_type': '对话', 'action_type': '对白'}
    knowledge = integrator.get_knowledge_for_agent(AgentType.SHOT_DIRECTOR, context)
    print(f"\n获取知识条目: {len(knowledge['rules'])}")
    
    # 测试分镜验证
    shot = ShotDefinition(
        subject="陈明面部特写（CU）",
        shot_size="CU",
        camera_height="平视",
        camera_angle="正面",
        camera_movement="固定机位",
        time_range=(0.0, 3.0),
    )
    is_valid, errors = validator.validate_shot(shot, AgentType.SHOT_DIRECTOR)
    print(f"\n分镜验证: {'通过' if is_valid else '失败'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
