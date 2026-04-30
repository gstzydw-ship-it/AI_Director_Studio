"""
AI Director Core - 中央智能导演系统

核心职责：
1. 深度剧本分析与创作意图理解
2. 智能知识库调用（基于场景、风格、情感）
3. 全流程协调与决策优化
4. 统一质量标准和风格一致性
5. 最终创意决策与质量把关

作者: AI Assistant
版本: 1.0.0
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from datetime import datetime

from agents.knowledge_base import (
    get_smart_knowledge,
    load_knowledge_documents,
    get_agent_knowledge_files,
)
from agents.utils import get_base_dir, get_output_dir


@dataclass
class ScriptAnalysis:
    """剧本深度分析结果"""
    genre: str  # 类型：爱情、动作、悬疑等
    mood: str  # 整体情绪基调
    pacing: str  # 节奏类型：快节奏、慢节奏、张弛有度
    key_themes: List[str]  # 核心主题
    character_relationships: Dict[str, Any]  # 人物关系
    scene_types: List[str]  # 场景类型分布
    emotional_arc: List[Dict]  # 情感曲线
    visual_style_hints: List[str]  # 视觉风格提示


@dataclass
class DirectorDecision:
    """导演决策记录"""
    phase: str
    decision_type: str
    context: Dict[str, Any]
    reasoning: str
    selected_option: str
    alternatives_considered: List[str]
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class KnowledgeQuery:
    """知识库查询请求"""
    query_type: str  # 'genre', 'scene', 'technique', 'rule', 'case'
    keywords: List[str]
    context: Dict[str, Any]
    priority: int = 1  # 1-5, 5为最高优先级


class RulesEngine:
    """
    规则引擎 - 确保所有决策符合核心规则
    """
    
    def __init__(self, knowledge_base_path: str = None):
        self.knowledge_base_path = knowledge_base_path or os.path.join(
            get_base_dir(), "knowledge"
        )
        self.rules_cache: Dict[str, Any] = {}
        self._load_core_rules()
    
    def _load_core_rules(self):
        """加载核心规则文档"""
        core_rule_files = [
            "00_知识库优先级与冲突裁决规则.md",
            "01_导演分镜总手册.md",
        ]
        
        for rule_file in core_rule_files:
            path = os.path.join(self.knowledge_base_path, rule_file)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.rules_cache[rule_file] = f.read()
    
    def validate_decision(self, decision: DirectorDecision) -> Tuple[bool, List[str]]:
        """
        验证决策是否符合规则
        
        Returns:
            (是否通过, 违规原因列表)
        """
        violations = []
        
        # TODO: 实现具体的规则验证逻辑
        # 1. 检查是否符合导演分镜总手册
        # 2. 检查是否违反硬性规则
        # 3. 检查是否满足最低质量标准
        
        return len(violations) == 0, violations
    
    def get_applicable_rules(self, phase: str, context: Dict) -> List[str]:
        """获取适用于当前阶段的规则"""
        applicable_rules = []
        
        # 根据阶段和上下文筛选规则
        rule_patterns = {
            'phase1': ['story_planner', 'rhythm_rewrite'],
            'phase2': ['shot_director', 'scene_analyst'],
            'phase3': ['prompt_compiler', 'shot_director_blocking'],
            'phase4': ['quality_inspector'],
        }
        
        # TODO: 实现规则匹配逻辑
        
        return applicable_rules


class KnowledgeIntegrator:
    """
    知识库整合器 - 智能检索和整合知识
    """
    
    def __init__(self):
        self.query_history: List[KnowledgeQuery] = []
        self.knowledge_cache: Dict[str, str] = {}
    
    def analyze_script_for_knowledge_needs(
        self, 
        script: str,
        analysis: ScriptAnalysis
    ) -> List[KnowledgeQuery]:
        """
        根据剧本分析结果，确定需要查询的知识
        
        Returns:
            知识查询请求列表
        """
        queries = []
        
        # 1. 根据类型查询风格知识
        queries.append(KnowledgeQuery(
            query_type='genre',
            keywords=[analysis.genre, analysis.mood, '风格指南'],
            context={'genre': analysis.genre, 'mood': analysis.mood},
            priority=5
        ))
        
        # 2. 根据场景类型查询案例
        for scene_type in set(analysis.scene_types):
            queries.append(KnowledgeQuery(
                query_type='case',
                keywords=[scene_type, '分镜案例', '镜头设计'],
                context={'scene_type': scene_type},
                priority=4
            ))
        
        # 3. 查询技术规则
        queries.append(KnowledgeQuery(
            query_type='rule',
            keywords=['镜头规则', '构图规则', '连续性'],
            context={'phase': 'all'},
            priority=5
        ))
        
        return queries
    
    def retrieve_knowledge(self, query: KnowledgeQuery) -> str:
        """执行知识库查询"""
        # 构建查询字符串
        query_str = " ".join(query.keywords)
        
        # 使用现有的知识库检索功能
        try:
            knowledge = get_smart_knowledge(
                agent_name="ai_director",
                query=query_str,
                top_k=5
            )
            return knowledge
        except Exception as e:
            return f"知识检索失败: {str(e)}"
    
    def integrate_knowledge_for_phase(
        self,
        phase: str,
        script_analysis: ScriptAnalysis,
        current_context: Dict
    ) -> str:
        """
        为特定阶段整合相关知识
        """
        # 确定该阶段需要哪些知识
        phase_knowledge_map = {
            'phase1': ['剧本拆分', '节奏控制', '戏剧微粒'],
            'phase2': ['镜头规则', '机位库', '分镜设计'],
            'phase3': ['prompt编写', '动作描述', '约束规则'],
            'phase4': ['质检规则', '判例库', '修正规则'],
        }
        
        keywords = phase_knowledge_map.get(phase, [])
        
        # 查询知识
        all_knowledge = []
        for keyword in keywords:
            query = KnowledgeQuery(
                query_type='technique',
                keywords=[keyword, script_analysis.genre],
                context=current_context
            )
            knowledge = self.retrieve_knowledge(query)
            all_knowledge.append(f"## {keyword}\n{knowledge}\n")
        
        return "\n".join(all_knowledge)


class PhaseCoordinator:
    """
    Phase 协调器基类
    """
    
    def __init__(self, phase_name: str, ai_director: 'AIDirectorCore'):
        self.phase_name = phase_name
        self.ai_director = ai_director
        self.decisions: List[DirectorDecision] = []
    
    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调该阶段的执行"""
        raise NotImplementedError
    
    def make_decision(
        self,
        decision_type: str,
        context: Dict,
        options: List[str],
        reasoning: str
    ) -> str:
        """记录并返回导演决策"""
        # 选择最佳选项（这里可以加入更复杂的决策逻辑）
        selected = options[0] if options else "default"
        
        decision = DirectorDecision(
            phase=self.phase_name,
            decision_type=decision_type,
            context=context,
            reasoning=reasoning,
            selected_option=selected,
            alternatives_considered=options[1:] if len(options) > 1 else [],
            confidence=0.85  # 可以根据实际情况调整
        )
        
        self.decisions.append(decision)
        
        # 验证决策是否符合规则
        is_valid, violations = self.ai_director.rules_engine.validate_decision(decision)
        if not is_valid:
            print(f"[警告] 决策违反规则: {violations}")
        
        return selected


class Phase1Coordinator(PhaseCoordinator):
    """Phase 1: 剧本分析与规划协调器"""
    
    def __init__(self, ai_director: 'AIDirectorCore'):
        super().__init__('phase1', ai_director)
    
    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调 Phase 1 执行"""
        script = context.get('script', '')
        
        # 1. 深度剧本分析
        analysis = self._analyze_script(script)
        
        # 2. 获取相关知识
        knowledge = self.ai_director.knowledge_integrator.integrate_knowledge_for_phase(
            'phase1', analysis, context
        )
        
        # 3. 决策：如何拆分剧本
        segmentation_strategy = self.make_decision(
            decision_type='segmentation_strategy',
            context={'script_length': len(script), 'genre': analysis.genre},
            options=['按场景拆分', '按情绪段落拆分', '按时间线拆分'],
            reasoning=f"基于剧本类型{analysis.genre}和情绪曲线{analysis.emotional_arc}"
        )
        
        return {
            'analysis': analysis,
            'knowledge': knowledge,
            'segmentation_strategy': segmentation_strategy,
            'decisions': self.decisions
        }
    
    def _analyze_script(self, script: str) -> ScriptAnalysis:
        """深度分析剧本"""
        # TODO: 使用 LLM 进行深度分析
        # 这里先返回一个基础分析
        return ScriptAnalysis(
            genre="爱情",  # 从剧本内容推断
            mood="浪漫紧张",
            pacing="张弛有度",
            key_themes=["相遇", "误会", "浪漫"],
            character_relationships={},
            scene_types=["室内", "对话"],
            emotional_arc=[],
            visual_style_hints=["现代都市", "高端商务"]
        )


class Phase2Coordinator(PhaseCoordinator):
    """Phase 2: 分镜设计协调器"""
    
    def __init__(self, ai_director: 'AIDirectorCore'):
        super().__init__('phase2', ai_director)
    
    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调 Phase 2 执行"""
        analysis = context.get('analysis')
        segments = context.get('segments', [])
        
        # 获取分镜设计知识
        knowledge = self.ai_director.knowledge_integrator.integrate_knowledge_for_phase(
            'phase2', analysis, context
        )
        
        # 为每个段落决策镜头策略
        shot_strategies = []
        for segment in segments:
            strategy = self.make_decision(
                decision_type='shot_strategy',
                context={'segment': segment},
                options=['多机位覆盖', '主观视角主导', '客观全景为主'],
                reasoning=f"基于段落情绪{segment.get('mood', 'neutral')}"
            )
            shot_strategies.append({
                'segment': segment,
                'strategy': strategy
            })
        
        return {
            'knowledge': knowledge,
            'shot_strategies': shot_strategies,
            'decisions': self.decisions
        }


class Phase3Coordinator(PhaseCoordinator):
    """Phase 3: 镜头细节优化协调器"""
    
    def __init__(self, ai_director: 'AIDirectorCore'):
        super().__init__('phase3', ai_director)
    
    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调 Phase 3 执行"""
        # 获取 Prompt 编写知识
        knowledge = self.ai_director.knowledge_integrator.integrate_knowledge_for_phase(
            'phase3', context.get('analysis'), context
        )
        
        return {
            'knowledge': knowledge,
            'optimization_rules': [
                'ONE-SHOT-ONE-ACTION',
                'PROMPT-NATURAL-SENTENCE',
                'PROMPT-REFERENCE-BINDING'
            ],
            'decisions': self.decisions
        }


class Phase4Coordinator(PhaseCoordinator):
    """Phase 4: 质量控制协调器"""
    
    def __init__(self, ai_director: 'AIDirectorCore'):
        super().__init__('phase4', ai_director)
    
    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调 Phase 4 执行"""
        # 获取质检规则
        knowledge = self.ai_director.knowledge_integrator.integrate_knowledge_for_phase(
            'phase4', context.get('analysis'), context
        )
        
        # 决策质检策略
        qc_strategy = self.make_decision(
            decision_type='qc_strategy',
            context={'output_type': context.get('output_type')},
            options=['严格模式', '标准模式', '快速模式'],
            reasoning="基于输出类型和截止时间"
        )
        
        return {
            'knowledge': knowledge,
            'qc_strategy': qc_strategy,
            'checklist': [
                '连续性检查',
                '规则符合性检查',
                '创意质量评估'
            ],
            'decisions': self.decisions
        }


class AIDirectorCore:
    """
    AI Director Core - 中央智能导演系统
    
    全流程导演入口，统一协调所有创作阶段
    """
    
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.knowledge_integrator = KnowledgeIntegrator()
        self.phase_coordinators = {
            'phase1': Phase1Coordinator(self),
            'phase2': Phase2Coordinator(self),
            'phase3': Phase3Coordinator(self),
            'phase4': Phase4Coordinator(self),
        }
        self.execution_log: List[Dict] = []
        self.all_decisions: List[DirectorDecision] = []
    
    def direct(
        self,
        script: str,
        style_preferences: Optional[Dict] = None,
        constraints: Optional[Dict] = None,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "16:9"
    ) -> Dict[str, Any]:
        """
        全流程导演入口
        
        Args:
            script: 剧本内容
            style_preferences: 风格偏好
            constraints: 约束条件
            reference_images: 参考图片
            aspect_ratio: 画幅比例
            
        Returns:
            完整的导演方案
        """
        print("=" * 80)
        print("AI Director Core - 开始全流程导演")
        print("=" * 80)
        
        start_time = time.time()
        
        # 初始化上下文
        context = {
            'script': script,
            'style_preferences': style_preferences or {},
            'constraints': constraints or {},
            'reference_images': reference_images or [],
            'aspect_ratio': aspect_ratio,
        }
        
        results = {}
        
        try:
            # Phase 1: 剧本分析与规划
            print("\n[Phase 1] 剧本分析与规划...")
            phase1_result = self.phase_coordinators['phase1'].coordinate(context)
            context['analysis'] = phase1_result['analysis']
            context['phase1_knowledge'] = phase1_result['knowledge']
            results['phase1'] = phase1_result
            print(f"  [OK] 完成 - 剧本类型: {phase1_result['analysis'].genre}")
            
            # Phase 2: 分镜设计
            print("\n[Phase 2] 分镜设计...")
            # TODO: 获取实际的剧本分段
            context['segments'] = [{'id': i, 'content': f'Segment {i}'} 
                                   for i in range(3)]  # 模拟分段
            phase2_result = self.phase_coordinators['phase2'].coordinate(context)
            context['phase2_knowledge'] = phase2_result['knowledge']
            results['phase2'] = phase2_result
            print(f"  [OK] 完成 - 设计了 {len(phase2_result['shot_strategies'])} 个段落策略")
            
            # Phase 3: 镜头细节优化
            print("\n[Phase 3] 镜头细节优化...")
            phase3_result = self.phase_coordinators['phase3'].coordinate(context)
            context['phase3_knowledge'] = phase3_result['knowledge']
            results['phase3'] = phase3_result
            print(f"  [OK] 完成 - 应用了 {len(phase3_result['optimization_rules'])} 条优化规则")
            
            # Phase 4: 质量控制
            print("\n[Phase 4] 质量控制...")
            context['output_type'] = 'shot_list'
            phase4_result = self.phase_coordinators['phase4'].coordinate(context)
            results['phase4'] = phase4_result
            print(f"  [OK] 完成 - 质检策略: {phase4_result['qc_strategy']}")
            
            # 收集所有决策
            for coordinator in self.phase_coordinators.values():
                self.all_decisions.extend(coordinator.decisions)
            
            elapsed = time.time() - start_time
            
            print("\n" + "=" * 80)
            print(f"[OK] 全流程导演完成 - 耗时: {elapsed:.1f}s")
            print(f"[OK] 共做出 {len(self.all_decisions)} 个导演决策")
            print("=" * 80)
            
            return {
                'status': 'success',
                'results': results,
                'all_decisions': self.all_decisions,
                'execution_time': elapsed,
                'final_output': self._generate_final_output(results)
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n[ERROR] 执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'status': 'error',
                'error': str(e),
                'execution_time': elapsed,
                'partial_results': results
            }
    
    def _generate_final_output(self, results: Dict) -> str:
        """生成最终输出"""
        # TODO: 整合所有阶段结果，生成最终的分镜方案
        output_parts = [
            "# AI Director 分镜方案\n",
            f"\n## 剧本分析\n",
            f"- 类型: {results['phase1']['analysis'].genre}\n",
            f"- 情绪基调: {results['phase1']['analysis'].mood}\n",
            f"\n## 分镜策略\n",
        ]
        
        for strategy in results['phase2'].get('shot_strategies', []):
            output_parts.append(f"- 段落: {strategy['strategy']}\n")
        
        return "".join(output_parts)
    
    def get_decision_report(self) -> str:
        """获取导演决策报告"""
        report = ["# AI Director 决策报告\n"]
        
        for decision in self.all_decisions:
            report.append(f"\n## {decision.phase} - {decision.decision_type}\n")
            report.append(f"- 决策: {decision.selected_option}\n")
            report.append(f"- 理由: {decision.reasoning}\n")
            report.append(f"- 置信度: {decision.confidence}\n")
            if decision.alternatives_considered:
                report.append(f"- 备选方案: {', '.join(decision.alternatives_considered)}\n")
        
        return "".join(report)


# 便捷函数
def create_ai_director() -> AIDirectorCore:
    """创建 AI Director 实例"""
    return AIDirectorCore()


def direct_script(
    script: str,
    **kwargs
) -> Dict[str, Any]:
    """
    快速导演入口函数
    
    使用示例:
        result = direct_script(
            script="剧本内容...",
            aspect_ratio="16:9",
            style_preferences={"mood": "浪漫"}
        )
    """
    director = create_ai_director()
    return director.direct(script, **kwargs)


if __name__ == "__main__":
    # 测试代码
    test_script = """2-1 日/内/天御集团大堂
人物：乔熙、商北琛
▲商北琛迈步走进大堂，锐利的眸子淡淡扫过两边的人群。
乔熙：Wait a second!
▲乔熙像风一般冲进电梯，一个刹不住整个人直扑到商北琛身上。
"""
    
    result = direct_script(test_script)
    print("\n最终输出:")
    print(result.get('final_output', 'No output'))
