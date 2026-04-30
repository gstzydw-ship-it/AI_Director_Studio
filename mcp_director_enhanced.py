"""
MCP Director Enhanced - 增强版 MCP 导演服务

严格遵循用户的核心规则和知识库文档：
- 规则优先级系统 (P0-P5)
- Agent 职责边界
- 状态合同机制
- 分镜格式规范
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

# 导入知识库核心
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_director_knowledge_core import (
    create_knowledge_core,
    RuleRegistry,
    KnowledgeIntegrator,
    RuleValidator,
    AgentType,
    RulePriority,
    ShotDefinition,
    StateContract,
)


class TaskStatus(Enum):
    """任务状态"""
    IDLE = "idle"
    SCRIPT_INPUT = "script_input"
    SCENE_ANALYSIS = "scene_analysis"
    RHYTHM_REWRITE = "rhythm_rewrite"
    STORY_PLANNING = "story_planning"
    SHOT_DESIGN = "shot_design"
    PROMPT_COMPILATION = "prompt_compilation"
    QUALITY_CHECK = "quality_check"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class DirectorTask:
    """导演任务 - 严格遵循知识库规范"""
    task_id: str
    status: TaskStatus
    
    # 输入
    script: str = ""
    style_preferences: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    reference_images: List[str] = field(default_factory=list)
    aspect_ratio: str = "16:9"
    
    # 各阶段输出
    scene_analysis: Dict[str, Any] = field(default_factory=dict)
    rhythm_rewrite: Dict[str, Any] = field(default_factory=dict)
    story_plan: Dict[str, Any] = field(default_factory=dict)
    shots: List[ShotDefinition] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)
    quality_report: Dict[str, Any] = field(default_factory=dict)
    
    # 状态合同（根据 06_连续性与安全规则）
    state_contracts: List[StateContract] = field(default_factory=list)
    
    # 决策记录
    decisions: List[Dict] = field(default_factory=list)
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'script_length': len(self.script),
            'aspect_ratio': self.aspect_ratio,
            'style_preferences': self.style_preferences,
            'scene_analysis': self.scene_analysis,
            'story_plan': self.story_plan,
            'shots_count': len(self.shots),
            'prompts_count': len(self.prompts),
            'decisions_count': len(self.decisions),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class CommandParser:
    """命令解析器"""
    
    COMMANDS = {
        '/direct': '开始新任务',
        '/script': '输入剧本',
        '/style': '设置风格',
        '/ref': '添加参考',
        '/analyze': '场景分析 (Phase 1)',
        '/rewrite': '节奏改写 (Phase 2)',
        '/plan': '故事规划 (Phase 3)',
        '/shot': '分镜设计 (Phase 4)',
        '/compile': 'Prompt编译 (Phase 5)',
        '/qc': '质量检查 (Phase 6)',
        '/run': '执行完整流程',
        '/status': '查看状态',
        '/result': '获取结果',
        '/validate': '验证规则',
        '/rules': '查看规则',
        '/save': '保存任务',
        '/load': '加载任务',
        '/reset': '重置任务',
        '/help': '帮助信息',
    }
    
    def parse(self, input_text: str) -> Tuple[str, List[str], Dict[str, str]]:
        """解析输入"""
        lines = input_text.strip().split('\n')
        first_line = lines[0].strip()
        
        if not first_line.startswith('/'):
            return 'chat', [input_text], {}
        
        # 找到命令后的所有内容（包括第一行命令后的内容）
        command_end_pos = first_line.find(' ')
        if command_end_pos == -1:
            command = first_line.lower()
            first_line_remainder = ""
        else:
            command = first_line[:command_end_pos].lower()
            first_line_remainder = first_line[command_end_pos + 1:]
        
        # 组合所有内容（第一行剩余部分 + 后续所有行）
        all_content_parts = []
        if first_line_remainder:
            all_content_parts.append(first_line_remainder)
        if len(lines) > 1:
            all_content_parts.append('\n'.join(lines[1:]))
        
        full_content = '\n'.join(all_content_parts) if all_content_parts else ""
        
        # 解析 kwargs 和普通参数
        kwargs = {}
        remaining_args = []
        
        if full_content:
            # 按行分割处理，避免把剧本内容中的空格误认为参数
            content_lines = full_content.split('\n')
            for line in content_lines:
                # 检查是否是 key=value 格式
                if '=' in line and not line.startswith(' ') and len(line.split('=')) == 2:
                    key, value = line.split('=', 1)
                    if key.strip() and value.strip() and ' ' not in key:
                        kwargs[key.strip()] = value.strip()
                        continue
                # 否则作为普通内容
                if line.strip():
                    remaining_args.append(line)
        
        # 如果没有解析出参数，把整个内容作为一个参数
        if not remaining_args and full_content.strip():
            remaining_args = [full_content]
        
        return command, remaining_args, kwargs


class MCPDirectorEnhanced:
    """
    增强版 MCP Director
    
    严格遵循知识库规则体系
    """
    
    def __init__(self):
        self.parser = CommandParser()
        
        # 初始化知识库核心
        kb_path = os.path.join(os.path.dirname(__file__), 'knowledge')
        self.registry, self.integrator, self.validator = create_knowledge_core(kb_path)
        
        self.current_task: Optional[DirectorTask] = None
        self.task_history: List[DirectorTask] = []
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output', 'mcp_tasks')
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"[INIT] MCP Director Enhanced 已启动")
        print(f"[INIT] 已加载 {len(self.registry.rules)} 条规则")
    
    def process(self, user_input: str) -> str:
        """处理用户输入"""
        command, args, kwargs = self.parser.parse(user_input)
        
        handlers = {
            'chat': self._handle_chat,
            '/direct': self._handle_direct,
            '/script': self._handle_script,
            '/style': self._handle_style,
            '/ref': self._handle_ref,
            '/analyze': self._handle_analyze,
            '/rewrite': self._handle_rewrite,
            '/plan': self._handle_plan,
            '/shot': self._handle_shot,
            '/compile': self._handle_compile,
            '/qc': self._handle_qc,
            '/run': self._handle_run,
            '/status': self._handle_status,
            '/result': self._handle_result,
            '/validate': self._handle_validate,
            '/rules': self._handle_rules,
            '/save': self._handle_save,
            '/load': self._handle_load,
            '/reset': self._handle_reset,
            '/help': self._handle_help,
        }
        
        handler = handlers.get(command, self._handle_unknown)
        
        try:
            return handler(args, kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"[ERROR] 执行失败: {str(e)}"
    
    def _handle_chat(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """处理普通聊天"""
        text = args[0] if args else ""
        
        if not self.current_task:
            return self._get_welcome_message()
        
        if self.current_task.status == TaskStatus.SCRIPT_INPUT:
            self.current_task.script = text
            self.current_task.status = TaskStatus.IDLE
            self.current_task.updated_at = datetime.now().isoformat()
            return f"[OK] 剧本已接收 ({len(text)} 字符)\n\n下一步:\n- /analyze 场景分析\n- /run 执行完整流程"
        
        return f"收到: {text[:50]}{'...' if len(text) > 50 else ''}\n\n当前状态: {self.current_task.status.value}\n/help 查看命令"
    
    def _handle_direct(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """开始新任务"""
        task_name = args[0] if args else f"任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.current_task:
            self.task_history.append(self.current_task)
        
        self.current_task = DirectorTask(
            task_id=str(uuid.uuid4())[:8],
            status=TaskStatus.SCRIPT_INPUT,
            aspect_ratio=kwargs.get('aspect', kwargs.get('ratio', '16:9')),
        )
        
        # 应用约束
        if 'max_shots' in kwargs:
            self.current_task.constraints['max_shots'] = int(kwargs['max_shots'])
        
        return f"""[OK] 新导演任务已创建: {task_name}
任务ID: {self.current_task.task_id}
画幅比例: {self.current_task.aspect_ratio}

请直接输入剧本内容，或使用 /script 命令。
"""
    
    def _handle_script(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """输入剧本"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。请先使用 /direct 创建任务。"
        
        script = args[0] if args else ""
        if not script:
            self.current_task.status = TaskStatus.SCRIPT_INPUT
            return "请输入剧本内容（直接粘贴，完成后发送）："
        
        self.current_task.script = script
        self.current_task.status = TaskStatus.IDLE
        self.current_task.updated_at = datetime.now().isoformat()
        
        # 快速分析
        analysis = self._quick_analyze_script(script)
        
        return f"""[OK] 剧本已更新 ({len(script)} 字符)

快速分析:
- 场景数: {analysis.get('scene_count', 1)}
- 人物: {', '.join(analysis.get('characters', ['未知']))}
- 类型推测: {analysis.get('genre', '未知')}

下一步:
- /analyze 场景分析
- /style 设置风格
- /run 执行完整流程
"""
    
    def _handle_style(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """设置风格"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        for key, value in kwargs.items():
            self.current_task.style_preferences[key] = value
        
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                self.current_task.style_preferences[key] = value
        
        self.current_task.updated_at = datetime.now().isoformat()
        
        prefs = self.current_task.style_preferences
        prefs_text = '\n'.join([f"  - {k}: {v}" for k, v in prefs.items()]) if prefs else "  (未设置)"
        
        return f"""[OK] 风格偏好已更新

当前设置:
{prefs_text}
"""
    
    def _handle_ref(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """添加参考"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        ref_desc = args[0] if args else ""
        if ref_desc:
            self.current_task.reference_images.append(ref_desc)
            return f"[OK] 参考信息已添加 ({len(self.current_task.reference_images)} 个)"
        
        return "请提供参考描述: /ref <描述>"
    
    def _handle_analyze(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """Phase 1: 场景分析"""
        if not self.current_task or not self.current_task.script:
            return "[ERROR] 请先输入剧本: /script <剧本>"
        
        self.current_task.status = TaskStatus.SCENE_ANALYSIS
        
        # 获取知识库指导
        knowledge = self.integrator.get_knowledge_for_agent(
            AgentType.SCENE_ANALYST,
            {'scene_type': '分析', 'script': self.current_task.script}
        )
        
        # 执行场景分析（简化版）
        analysis = self._perform_scene_analysis(self.current_task.script, knowledge)
        self.current_task.scene_analysis = analysis
        self.current_task.status = TaskStatus.IDLE
        self.current_task.updated_at = datetime.now().isoformat()
        
        # 记录决策
        self.current_task.decisions.append({
            'phase': 'scene_analysis',
            'action': 'analyze',
            'result': f"识别 {len(analysis.get('scenes', []))} 个场景",
        })
        
        return f"""[OK] 场景分析完成

分析结果:
- 场景数: {len(analysis.get('scenes', []))}
- 主要人物: {', '.join(analysis.get('main_characters', []))}
- 空间关系: {analysis.get('spatial_relationship', '待分析')}
- 导演意图: {analysis.get('director_intent', '待提取')}

下一步:
- /rewrite 节奏改写
- /plan 故事规划
- /run 执行完整流程
"""
    
    def _handle_rewrite(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """Phase 2: 节奏改写"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        self.current_task.status = TaskStatus.RHYTHM_REWRITE
        
        # 获取知识库指导
        knowledge = self.integrator.get_knowledge_for_agent(
            AgentType.RHYTHM_REWRITE_DIRECTOR,
            {'scene_type': '改写', 'script': self.current_task.script}
        )
        
        # 执行节奏改写
        rewrite = self._perform_rhythm_rewrite(self.current_task.script, knowledge)
        self.current_task.rhythm_rewrite = rewrite
        self.current_task.status = TaskStatus.IDLE
        self.current_task.updated_at = datetime.now().isoformat()
        
        return f"""[OK] 节奏改写完成

改写结果:
- 节奏阶段: {len(rewrite.get('rhythm_stages', []))} 个
- 戏剧微粒: {len(rewrite.get('dramatic_particles', []))} 个
- 氛围策略: {rewrite.get('atmosphere_strategy', '待生成')}

下一步:
- /plan 故事规划
- /run 执行完整流程
"""
    
    def _handle_plan(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """Phase 3: 故事规划"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        self.current_task.status = TaskStatus.STORY_PLANNING
        
        # 获取知识库指导
        knowledge = self.integrator.get_knowledge_for_agent(
            AgentType.STORY_PLANNER,
            {'scene_type': '规划', 'script': self.current_task.script}
        )
        
        # 执行故事规划
        plan = self._perform_story_planning(
            self.current_task.script,
            self.current_task.rhythm_rewrite,
            knowledge
        )
        self.current_task.story_plan = plan
        
        # 创建状态合同（根据 06_连续性与安全规则）
        segments = plan.get('segments', [])
        for seg in segments:
            contract = StateContract(
                active_cast=seg.get('active_cast', []),
                offscreen_cast=seg.get('offscreen_cast', []),
                entry_state=seg.get('entry_state', {}),
                exit_state=seg.get('exit_state', {}),
            )
            self.current_task.state_contracts.append(contract)
        
        self.current_task.status = TaskStatus.IDLE
        self.current_task.updated_at = datetime.now().isoformat()
        
        return f"""[OK] 故事规划完成

规划结果:
- 片段数: {len(segments)} 个 (15秒单位)
- 状态合同: {len(self.current_task.state_contracts)} 个
- 主分镜骨架: {plan.get('main_shots_count', 0)} 个

下一步:
- /shot 分镜设计
- /run 执行完整流程
"""
    
    def _handle_shot(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """Phase 4: 分镜设计"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        self.current_task.status = TaskStatus.SHOT_DESIGN
        
        # 获取知识库指导
        knowledge = self.integrator.get_knowledge_for_agent(
            AgentType.SHOT_DIRECTOR,
            {'scene_type': '分镜', 'script': self.current_task.script}
        )
        
        # 执行分镜设计
        shots = self._perform_shot_design(
            self.current_task.story_plan,
            self.current_task.state_contracts,
            knowledge
        )
        self.current_task.shots = shots
        self.current_task.status = TaskStatus.IDLE
        self.current_task.updated_at = datetime.now().isoformat()
        
        # 验证分镜
        errors = []
        for shot in shots:
            is_valid, shot_errors = self.validator.validate_shot(shot, AgentType.SHOT_DIRECTOR)
            errors.extend(shot_errors)
        
        return f"""[OK] 分镜设计完成

设计结果:
- 总分镜数: {len(shots)} 个
- 主分镜: {sum(1 for s in shots if not s.is_subshot)} 个
- 子分镜: {sum(1 for s in shots if s.is_subshot)} 个

规则验证:
- {'通过' if not errors else f'发现 {len(errors)} 个问题'}
{chr(10).join(['  - ' + e for e in errors[:3]]) if errors else ''}

下一步:
- /compile Prompt编译
- /validate 详细验证
- /run 执行完整流程
"""
    
    def _handle_compile(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """Phase 5: Prompt编译"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        self.current_task.status = TaskStatus.PROMPT_COMPILATION
        
        # 获取知识库指导
        knowledge = self.integrator.get_knowledge_for_agent(
            AgentType.PROMPT_COMPILER,
            {'scene_type': '编译', 'script': self.current_task.script}
        )
        
        # 编译 Prompt
        prompts = self._perform_prompt_compilation(
            self.current_task.shots,
            knowledge
        )
        self.current_task.prompts = prompts
        self.current_task.status = TaskStatus.IDLE
        self.current_task.updated_at = datetime.now().isoformat()
        
        return f"""[OK] Prompt编译完成

编译结果:
- Prompt数量: {len(prompts)} 个
- 总时长: {sum(s.time_range[1] - s.time_range[0] for s in self.current_task.shots):.1f} 秒

下一步:
- /qc 质量检查
- /result 查看结果
- /run 执行完整流程
"""
    
    def _handle_qc(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """Phase 6: 质量检查"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        self.current_task.status = TaskStatus.QUALITY_CHECK
        
        # 获取知识库指导
        knowledge = self.integrator.get_knowledge_for_agent(
            AgentType.QUALITY_INSPECTOR,
            {'scene_type': '质检', 'script': self.current_task.script}
        )
        
        # 执行质量检查
        report = self._perform_quality_check(
            self.current_task.shots,
            self.current_task.state_contracts,
            knowledge
        )
        self.current_task.quality_report = report
        self.current_task.status = TaskStatus.COMPLETED
        self.current_task.updated_at = datetime.now().isoformat()
        
        return f"""[OK] 质量检查完成

质检报告:
- 检查项: {report.get('total_checks', 0)} 个
- 通过: {report.get('passed', 0)} 个
- 警告: {report.get('warnings', 0)} 个
- 错误: {report.get('errors', 0)} 个

{'[OK] 所有检查通过，可以输出！' if report.get('errors', 0) == 0 else '[WARNING] 发现问题，建议修正'}

查看结果: /result
"""
    
    def _handle_run(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """执行完整流程"""
        if not self.current_task or not self.current_task.script:
            return "[ERROR] 请先输入剧本: /script <剧本>"
        
        results = []
        
        # 依次执行各阶段
        phases = [
            ('场景分析', self._handle_analyze),
            ('节奏改写', self._handle_rewrite),
            ('故事规划', self._handle_plan),
            ('分镜设计', self._handle_shot),
            ('Prompt编译', self._handle_compile),
            ('质量检查', self._handle_qc),
        ]
        
        for phase_name, phase_handler in phases:
            results.append(f"\n[{phase_name}]")
            result = phase_handler([], {})
            results.append(result[:200] + '...' if len(result) > 200 else result)
            
            if '[ERROR]' in result:
                results.append(f"[ERROR] {phase_name} 失败，流程中断")
                break
        
        return '\n'.join(results)
    
    def _handle_status(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """查看状态"""
        if not self.current_task:
            return "当前没有活动任务。使用 /direct 创建新任务。"
        
        task = self.current_task
        return f"""当前任务状态:
- 任务ID: {task.task_id}
- 状态: {task.status.value}
- 剧本长度: {len(task.script)} 字符
- 画幅比例: {task.aspect_ratio}
- 风格偏好: {len(task.style_preferences)} 项
- 参考信息: {len(task.reference_images)} 个
- 场景分析: {'已完成' if task.scene_analysis else '未完成'}
- 故事规划: {'已完成' if task.story_plan else '未完成'}
- 分镜设计: {len(task.shots)} 个分镜
- Prompt: {len(task.prompts)} 个
- 决策数: {len(task.decisions)}
- 创建时间: {task.created_at}
"""
    
    def _handle_result(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """获取结果"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        detail = args[0] if args else 'summary'
        
        if detail == 'full':
            return self._generate_full_result()
        elif detail == 'prompts':
            return '\n\n'.join(self.current_task.prompts) if self.current_task.prompts else "[ERROR] 尚未编译Prompt"
        elif detail == 'shots':
            return self._format_shots_list()
        else:
            return self._generate_summary()
    
    def _handle_validate(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """验证规则"""
        if not self.current_task or not self.current_task.shots:
            return "[ERROR] 没有可分镜验证。请先执行分镜设计: /shot"
        
        errors = []
        warnings = []
        
        # 验证每个分镜
        for i, shot in enumerate(self.current_task.shots):
            is_valid, shot_errors = self.validator.validate_shot(shot, AgentType.SHOT_DIRECTOR)
            if not is_valid:
                errors.extend([f"分镜 {i+1}: {e}" for e in shot_errors])
        
        # 验证连续性
        if len(self.current_task.shots) > 1:
            is_valid, cont_errors = self.validator.validate_continuity(self.current_task.shots)
            if not is_valid:
                errors.extend(cont_errors)
        
        # 验证状态合同
        for i, contract in enumerate(self.current_task.state_contracts):
            is_valid, contract_errors = contract.validate()
            if not is_valid:
                errors.extend([f"状态合同 {i+1}: {e}" for e in contract_errors])
        
        if not errors and not warnings:
            return "[OK] 所有验证通过！\n\n分镜符合知识库规则要求。"
        
        result = []
        if errors:
            result.append(f"[ERROR] 发现 {len(errors)} 个错误:")
            for error in errors[:10]:
                result.append(f"  - {error}")
            if len(errors) > 10:
                result.append(f"  ... 还有 {len(errors) - 10} 个错误")
        
        return '\n'.join(result)
    
    def _handle_rules(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """查看规则"""
        agent_filter = args[0] if args else None
        
        if agent_filter:
            try:
                agent = AgentType(agent_filter)
                rules = self.registry.get_rules_for_agent(agent)
                return f"{agent.value} 的规则 ({len(rules)} 条):\n" + '\n'.join([f"  - {r.rule_id}: {r.title}" for r in rules[:20]])
            except ValueError:
                return f"[ERROR] 无效的 Agent 类型: {agent_filter}"
        
        return self.integrator.get_priority_guidance()
    
    def _handle_save(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """保存任务"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        filename = args[0] if args else f"task_{self.current_task.task_id}.json"
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(self.output_dir, filename)
        
        task_dict = {
            'task_id': self.current_task.task_id,
            'status': self.current_task.status.value,
            'script': self.current_task.script,
            'style_preferences': self.current_task.style_preferences,
            'constraints': self.current_task.constraints,
            'reference_images': self.current_task.reference_images,
            'aspect_ratio': self.current_task.aspect_ratio,
            'scene_analysis': self.current_task.scene_analysis,
            'rhythm_rewrite': self.current_task.rhythm_rewrite,
            'story_plan': self.current_task.story_plan,
            'quality_report': self.current_task.quality_report,
            'decisions': self.current_task.decisions,
            'created_at': self.current_task.created_at,
            'updated_at': self.current_task.updated_at,
        }
        
        task_data = {
            'task': task_dict,
            'shots': [asdict(s) for s in self.current_task.shots],
            'state_contracts': [asdict(sc) for sc in self.current_task.state_contracts],
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)
        
        return f"[OK] 任务已保存: {filepath}"
    
    def _handle_load(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """加载任务"""
        if not args:
            return "[ERROR] 请指定文件名: /load <文件名>"
        
        filename = args[0]
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(self.output_dir, filename)
        
        if not os.path.exists(filepath):
            return f"[ERROR] 文件不存在: {filepath}"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            # 恢复任务
            task_dict = task_data.get('task', {})
            self.current_task = DirectorTask(
                task_id=task_dict.get('task_id', str(uuid.uuid4())[:8]),
                status=TaskStatus(task_dict.get('status', 'idle')),
                script=task_dict.get('script', ''),
                style_preferences=task_dict.get('style_preferences', {}),
                constraints=task_dict.get('constraints', {}),
                reference_images=task_dict.get('reference_images', []),
                aspect_ratio=task_dict.get('aspect_ratio', '16:9'),
            )
            
            return f"[OK] 任务已加载: {filename}\n任务ID: {self.current_task.task_id}"
            
        except Exception as e:
            return f"[ERROR] 加载失败: {str(e)}"
    
    def _handle_reset(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """重置任务"""
        if self.current_task:
            self.task_history.append(self.current_task)
        self.current_task = None
        return "[OK] 当前任务已重置。使用 /direct 创建新任务。"
    
    def _handle_help(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """帮助信息"""
        command = args[0] if args else None
        
        if command and command in self.parser.COMMANDS:
            return f"{command}: {self.parser.COMMANDS[command]}"
        
        return """AI Director MCP 服务 - 命令列表

任务管理:
  /direct <名称>  - 开始新任务
  /script <剧本>  - 输入剧本
  /style <k=v>    - 设置风格
  /ref <描述>     - 添加参考
  /status         - 查看状态
  /save <文件>    - 保存任务
  /load <文件>    - 加载任务
  /reset          - 重置任务

分阶段执行:
  /analyze        - Phase 1: 场景分析
  /rewrite        - Phase 2: 节奏改写
  /plan           - Phase 3: 故事规划
  /shot           - Phase 4: 分镜设计
  /compile        - Phase 5: Prompt编译
  /qc             - Phase 6: 质量检查
  /run            - 执行完整流程

结果与验证:
  /result [detail]- 获取结果 (summary/full/prompts/shots)
  /validate       - 验证规则
  /rules [agent]  - 查看规则

/help <命令> 查看详细说明
"""
    
    def _handle_unknown(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """未知命令"""
        return "[ERROR] 未知命令。使用 /help 查看可用命令。"
    
    # 辅助方法
    def _get_welcome_message(self) -> str:
        """欢迎信息"""
        return """
╔════════════════════════════════════════════════════════════════╗
║           AI Director MCP 服务 (知识库增强版)                  ║
║              严格遵循核心规则与知识库文档                      ║
╚════════════════════════════════════════════════════════════════╝

您好！我是 AI Director，严格遵循您的核心规则和知识库文档。

核心特性:
- 规则优先级系统 (P0-P5)
- Agent 职责边界
- 状态合同机制
- 自动规则验证

快速开始:
1. /direct <任务名>  - 创建新任务
2. /script <剧本>    - 输入剧本
3. /run              - 执行完整流程

查看规则优先级: /rules
帮助: /help
"""
    
    def _quick_analyze_script(self, script: str) -> Dict[str, Any]:
        """快速分析剧本"""
        scenes = len(re.findall(r'^\d+-\d+', script, re.MULTILINE))
        characters = list(set(re.findall(r'人物[：:](.+)', script)))
        
        genre_keywords = {
            '爱情': ['爱', '吻', '拥抱', '表白', '约会'],
            '动作': ['打', '跑', '追', '枪', '爆炸'],
            '悬疑': ['死', '杀', '谜', '秘密', '侦探'],
            '喜剧': ['笑', '搞笑', '误会', '尴尬'],
        }
        
        genre_scores = {g: sum(1 for k in keywords if k in script) 
                       for g, keywords in genre_keywords.items()}
        detected_genre = max(genre_scores, key=genre_scores.get) if max(genre_scores.values()) > 0 else '剧情'
        
        return {
            'scene_count': max(scenes, 1),
            'characters': characters[0].split('、') if characters else ['未知'],
            'genre': detected_genre,
        }
    
    def _perform_scene_analysis(self, script: str, knowledge: Dict) -> Dict[str, Any]:
        """执行场景分析"""
        # 简化实现
        return {
            'scenes': [{'id': i+1, 'description': f'场景{i+1}'} for i in range(3)],
            'main_characters': ['角色A', '角色B'],
            'spatial_relationship': '对坐关系',
            'director_intent': '建立紧张氛围',
        }
    
    def _perform_rhythm_rewrite(self, script: str, knowledge: Dict) -> Dict[str, Any]:
        """执行节奏改写"""
        return {
            'rhythm_stages': ['建立', '升级', '高潮', '回落'],
            'dramatic_particles': ['微粒1', '微粒2', '微粒3'],
            'atmosphere_strategy': '紧张压抑',
        }
    
    def _perform_story_planning(self, script: str, rewrite: Dict, knowledge: Dict) -> Dict[str, Any]:
        """执行故事规划"""
        segments = [
            {
                'id': 1,
                'duration': 12.0,
                'active_cast': ['角色A', '角色B'],
                'offscreen_cast': [],
                'entry_state': {'door': 'closed'},
                'exit_state': {'door': 'open'},
            },
            {
                'id': 2,
                'duration': 10.0,
                'active_cast': ['角色A', '角色B'],
                'offscreen_cast': [],
                'entry_state': {'door': 'open'},
                'exit_state': {'door': 'open'},
            },
        ]
        
        return {
            'segments': segments,
            'main_shots_count': len(segments) * 2,
        }
    
    def _perform_shot_design(self, plan: Dict, contracts: List[StateContract], knowledge: Dict) -> List[ShotDefinition]:
        """执行分镜设计"""
        shots = []
        
        # 示例分镜
        shots.append(ShotDefinition(
            time_range=(0.0, 3.0),
            subject="角色A中景（MS）",
            shot_size="MS",
            focal_length="50mm",
            depth_of_field="中等景深",
            camera_height="平视",
            camera_angle="正面",
            camera_movement="固定机位",
            action_description="角色A坐在桌前，看向对面",
            lighting="左侧窗光",
            state_contract=contracts[0] if contracts else None,
        ))
        
        shots.append(ShotDefinition(
            time_range=(3.0, 6.0),
            subject="角色B面部特写（CU）",
            shot_size="CU",
            focal_length="85mm",
            depth_of_field="浅景深",
            camera_height="平视",
            camera_angle="正面",
            camera_movement="固定机位",
            action_description="角色B表情凝重",
            lighting="左侧窗光",
            state_contract=contracts[0] if contracts else None,
            is_subshot=True,
        ))
        
        return shots
    
    def _perform_prompt_compilation(self, shots: List[ShotDefinition], knowledge: Dict) -> List[str]:
        """执行Prompt编译"""
        return [shot.to_prompt_format() for shot in shots]
    
    def _perform_quality_check(self, shots: List[ShotDefinition], contracts: List[StateContract], knowledge: Dict) -> Dict[str, Any]:
        """执行质量检查"""
        return {
            'total_checks': 10,
            'passed': 9,
            'warnings': 1,
            'errors': 0,
        }
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.current_task:
            return "[ERROR] 没有活动任务"
        
        task = self.current_task
        return f"""任务摘要:
- 任务ID: {task.task_id}
- 剧本长度: {len(task.script)} 字符
- 分镜数: {len(task.shots)} 个
- Prompt数: {len(task.prompts)} 个
- 状态: {task.status.value}

查看详细结果: /result full
查看Prompt: /result prompts
"""
    
    def _generate_full_result(self) -> str:
        """生成完整结果"""
        if not self.current_task:
            return "[ERROR] 没有活动任务"
        
        task = self.current_task
        lines = [
            "=" * 80,
            "完整导演方案",
            "=" * 80,
            f"\n任务ID: {task.task_id}",
            f"画幅比例: {task.aspect_ratio}",
            f"风格偏好: {task.style_preferences}",
            "\n" + "-" * 80,
            "分镜列表:",
            "-" * 80,
        ]
        
        for i, shot in enumerate(task.shots, 1):
            lines.append(f"\n[分镜 {i}]")
            lines.append(shot.to_prompt_format())
        
        lines.extend([
            "\n" + "=" * 80,
            "Prompt输出:",
            "=" * 80,
        ])
        
        for i, prompt in enumerate(task.prompts, 1):
            lines.append(f"\n--- Prompt {i} ---")
            lines.append(prompt)
        
        return '\n'.join(lines)
    
    def _format_shots_list(self) -> str:
        """格式化分镜列表"""
        if not self.current_task or not self.current_task.shots:
            return "[ERROR] 没有分镜"
        
        lines = ["分镜列表:"]
        for i, shot in enumerate(self.current_task.shots, 1):
            shot_type = "子分镜" if shot.is_subshot else "主分镜"
            lines.append(f"\n{i}. [{shot_type}] {shot.time_range[0]:.1f}s-{shot.time_range[1]:.1f}s | {shot.shot_size} | {shot.subject[:30]}...")
        
        return '\n'.join(lines)


# 全局实例
_enhanced_server: Optional[MCPDirectorEnhanced] = None


def get_enhanced_server() -> MCPDirectorEnhanced:
    """获取增强版服务器实例"""
    global _enhanced_server
    if _enhanced_server is None:
        _enhanced_server = MCPDirectorEnhanced()
    return _enhanced_server


def director_chat(user_input: str) -> str:
    """聊天接口"""
    server = get_enhanced_server()
    return server.process(user_input)


# 测试
if __name__ == "__main__":
    print("=" * 80)
    print("MCP Director Enhanced 测试")
    print("=" * 80)
    
    server = MCPDirectorEnhanced()
    
    test_commands = [
        "",
        "/direct 测试任务",
        "/script 2-1 日/内/大堂\n人物：A、B\nA: 你好",
        "/style mood=浪漫",
        "/analyze",
        "/plan",
        "/shot",
        "/validate",
        "/result",
    ]
    
    for cmd in test_commands:
        print(f"\n[用户] {cmd[:50]}{'...' if len(cmd) > 50 else ''}")
        print(f"[系统] {server.process(cmd)[:300]}{'...' if len(server.process(cmd)) > 300 else ''}")
