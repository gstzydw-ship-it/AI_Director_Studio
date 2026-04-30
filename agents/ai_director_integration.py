"""
AI Director Integration - 将 AI Director Core 集成到现有工作流

这个模块提供了 AI Director Core 与现有 LangGraph 工作流的无缝集成。
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

# 导入 AI Director Core
from agents.ai_director_core import (
    AIDirectorCore,
    create_ai_director,
    direct_script,
    ScriptAnalysis,
    DirectorDecision,
)

# 导入现有工作流组件
try:
    from agents.director_graph import (
        DirectorState,
        call_llm,
        PHASE_1_AGENTS,
        PHASE_2_AGENTS,
        PHASE_3_AGENTS,
        PHASE_4_AGENTS,
    )
except ImportError:
    # 如果导入失败，定义占位符
    DirectorState = dict
    PHASE_1_AGENTS = []
    PHASE_2_AGENTS = []
    PHASE_3_AGENTS = []
    PHASE_4_AGENTS = []


class AIDirectorNode:
    """
    AI Director 节点包装器
    
    将 AI Director Core 包装成 LangGraph 可用的节点
    """
    
    def __init__(self, ai_director: Optional[AIDirectorCore] = None):
        self.ai_director = ai_director or create_ai_director()
        self.node_name = "ai_director_core"
    
    def __call__(self, state: DirectorState) -> DirectorState:
        """
        节点执行入口
        
        根据当前状态决定执行哪个阶段的协调
        """
        current_phase = state.get('current_phase', 'phase1')
        
        # 构建上下文
        context = self._build_context(state)
        
        # 执行对应阶段的协调
        if current_phase == 'phase1':
            result = self._coordinate_phase1(context, state)
        elif current_phase == 'phase2':
            result = self._coordinate_phase2(context, state)
        elif current_phase == 'phase3':
            result = self._coordinate_phase3(context, state)
        elif current_phase == 'phase4':
            result = self._coordinate_phase4(context, state)
        else:
            result = {'error': f'Unknown phase: {current_phase}'}
        
        # 更新状态
        new_state = dict(state)
        new_state['ai_director_result'] = result
        new_state['ai_director_decisions'] = self._collect_decisions()
        
        return new_state
    
    def _build_context(self, state: DirectorState) -> Dict[str, Any]:
        """从状态构建上下文"""
        return {
            'script': state.get('script', ''),
            'aspect_ratio': state.get('aspect_ratio', '16:9'),
            'reference_images': state.get('reference_images', []),
            'style_preferences': state.get('style_preferences', {}),
            'previous_outputs': state.get('agent_outputs', {}),
            'current_phase': state.get('current_phase', 'phase1'),
        }
    
    def _coordinate_phase1(self, context: Dict, state: DirectorState) -> Dict:
        """协调 Phase 1"""
        coordinator = self.ai_director.phase_coordinators['phase1']
        
        # 执行分析
        result = coordinator.coordinate(context)
        
        # 将分析结果注入到状态中
        analysis = result['analysis']
        
        return {
            'phase': 'phase1',
            'analysis': {
                'genre': analysis.genre,
                'mood': analysis.mood,
                'pacing': analysis.pacing,
                'key_themes': analysis.key_themes,
                'scene_types': analysis.scene_types,
            },
            'knowledge': result['knowledge'],
            'segmentation_strategy': result['segmentation_strategy'],
            'decisions': [self._decision_to_dict(d) for d in result['decisions']]
        }
    
    def _coordinate_phase2(self, context: Dict, state: DirectorState) -> Dict:
        """协调 Phase 2"""
        coordinator = self.ai_director.phase_coordinators['phase2']
        
        # 从 Phase 1 获取分析结果
        analysis_data = state.get('ai_director_result', {}).get('analysis', {})
        analysis = ScriptAnalysis(
            genre=analysis_data.get('genre', 'general'),
            mood=analysis_data.get('mood', 'neutral'),
            pacing=analysis_data.get('pacing', 'moderate'),
            key_themes=analysis_data.get('key_themes', []),
            character_relationships={},
            scene_types=analysis_data.get('scene_types', []),
            emotional_arc=[],
            visual_style_hints=[]
        )
        
        context['analysis'] = analysis
        context['segments'] = state.get('segments', [])
        
        result = coordinator.coordinate(context)
        
        return {
            'phase': 'phase2',
            'shot_strategies': result['shot_strategies'],
            'knowledge': result['knowledge'],
            'decisions': [self._decision_to_dict(d) for d in result['decisions']]
        }
    
    def _coordinate_phase3(self, context: Dict, state: DirectorState) -> Dict:
        """协调 Phase 3"""
        coordinator = self.ai_director.phase_coordinators['phase3']
        
        result = coordinator.coordinate(context)
        
        return {
            'phase': 'phase3',
            'optimization_rules': result['optimization_rules'],
            'knowledge': result['knowledge'],
            'decisions': [self._decision_to_dict(d) for d in result['decisions']]
        }
    
    def _coordinate_phase4(self, context: Dict, state: DirectorState) -> Dict:
        """协调 Phase 4"""
        coordinator = self.ai_director.phase_coordinators['phase4']
        
        result = coordinator.coordinate(context)
        
        return {
            'phase': 'phase4',
            'qc_strategy': result['qc_strategy'],
            'checklist': result['checklist'],
            'knowledge': result['knowledge'],
            'decisions': [self._decision_to_dict(d) for d in result['decisions']]
        }
    
    def _collect_decisions(self) -> List[Dict]:
        """收集所有决策"""
        decisions = []
        for coordinator in self.ai_director.phase_coordinators.values():
            for decision in coordinator.decisions:
                decisions.append(self._decision_to_dict(decision))
        return decisions
    
    def _decision_to_dict(self, decision: DirectorDecision) -> Dict:
        """将决策转换为字典"""
        return {
            'phase': decision.phase,
            'decision_type': decision.decision_type,
            'selected_option': decision.selected_option,
            'reasoning': decision.reasoning,
            'confidence': decision.confidence,
            'alternatives': decision.alternatives_considered,
            'timestamp': decision.timestamp,
        }


class AIDirectorEnhancedWorkflow:
    """
    AI Director 增强工作流
    
    在现有工作流基础上增加 AI Director 的智能协调层
    """
    
    def __init__(self):
        self.ai_director = create_ai_director()
        self.ai_node = AIDirectorNode(self.ai_director)
    
    def run_with_ai_director(
        self,
        script: str,
        aspect_ratio: str = "16:9",
        reference_images: Optional[List[str]] = None,
        enable_ai_coordination: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用 AI Director 增强的工作流
        
        Args:
            script: 剧本内容
            aspect_ratio: 画幅比例
            reference_images: 参考图片
            enable_ai_coordination: 是否启用 AI Director 协调
            **kwargs: 其他参数
            
        Returns:
            包含 AI Director 决策的完整结果
        """
        if not enable_ai_coordination:
            # 回退到标准工作流
            from agents.director_graph import run_phase_1_planning
            return run_phase_1_planning(
                script=script,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
                **kwargs
            )
        
        # 使用 AI Director Core 进行全流程导演
        result = self.ai_director.direct(
            script=script,
            aspect_ratio=aspect_ratio,
            reference_images=reference_images,
            **kwargs
        )
        
        # 生成决策报告
        decision_report = self.ai_director.get_decision_report()
        
        return {
            **result,
            'decision_report': decision_report,
            'ai_director_version': '1.0.0',
        }


# 便捷函数
def run_with_ai_director(
    script: str,
    **kwargs
) -> Dict[str, Any]:
    """
    使用 AI Director 运行工作流的便捷函数
    
    示例:
        result = run_with_ai_director(
            script="剧本内容...",
            aspect_ratio="16:9",
            style_preferences={"mood": "浪漫"}
        )
        
        # 查看 AI Director 的决策
        print(result['decision_report'])
        
        # 查看最终输出
        print(result['final_output'])
    """
    workflow = AIDirectorEnhancedWorkflow()
    return workflow.run_with_ai_director(script, **kwargs)


def create_ai_director_node() -> AIDirectorNode:
    """创建 AI Director 节点（用于 LangGraph 集成）"""
    return AIDirectorNode()


# 与现有工作流的集成点
def integrate_with_existing_graph(graph_builder: Any) -> Any:
    """
    将 AI Director 集成到现有的 LangGraph 构建器中
    
    示例:
        from langgraph.graph import StateGraph
        from agents.director_graph import DirectorState
        
        builder = StateGraph(DirectorState)
        # ... 添加现有节点 ...
        
        # 集成 AI Director
        builder = integrate_with_existing_graph(builder)
        
        graph = builder.compile()
    """
    ai_node = create_ai_director_node()
    
    # 在每个 Phase 前添加 AI Director 协调节点
    graph_builder.add_node("ai_director_coordination", ai_node)
    
    # 可以在这里添加更多的集成逻辑
    
    return graph_builder


if __name__ == "__main__":
    # 测试集成
    print("=" * 80)
    print("AI Director Integration Test")
    print("=" * 80)
    
    test_script = """2-1 日/内/天御集团大堂
人物：乔熙、商北琛
▲商北琛迈步走进大堂，锐利的眸子淡淡扫过两边的人群。
乔熙：Wait a second!
▲乔熙像风一般冲进电梯，一个刹不住整个人直扑到商北琛身上。
"""
    
    print("\n测试 AI Director 增强工作流...")
    result = run_with_ai_director(test_script)
    
    print("\n" + "=" * 80)
    print("执行结果:")
    print(f"状态: {result['status']}")
    print(f"执行时间: {result['execution_time']:.1f}s")
    print(f"决策数量: {len(result.get('all_decisions', []))}")
    
    print("\n决策报告预览:")
    report = result.get('decision_report', '')
    print(report[:500] + "..." if len(report) > 500 else report)
