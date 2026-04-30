"""
MCP Director Server - AI 导演 MCP 服务

通过聊天界面直接控制导演系统的 MCP 服务。
支持命令式交互，无需 Web UI。

作者: AI Assistant
版本: 1.0.0
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple
from datetime import datetime
from enum import Enum

# 导入 AI Director Core
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.ai_director_core import (
    AIDirectorCore,
    create_ai_director,
    ScriptAnalysis,
    DirectorDecision,
)


class TaskStatus(Enum):
    """任务状态"""
    IDLE = "idle"
    SCRIPT_INPUT = "script_input"
    CONFIGURING = "configuring"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class DirectorTask:
    """导演任务"""
    task_id: str
    status: TaskStatus
    script: str = ""
    style_preferences: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    reference_images: List[str] = field(default_factory=list)
    aspect_ratio: str = "16:9"
    current_phase: str = ""
    results: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'script_length': len(self.script),
            'style_preferences': self.style_preferences,
            'constraints': self.constraints,
            'reference_images_count': len(self.reference_images),
            'aspect_ratio': self.aspect_ratio,
            'current_phase': self.current_phase,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class CommandParser:
    """
    命令解析器
    
    解析用户聊天输入的命令
    """
    
    # 命令定义
    COMMANDS = {
        '/direct': {
            'description': '开始一个新的导演任务',
            'usage': '/direct [任务名称]',
            'example': '/direct 爱情戏导演',
        },
        '/script': {
            'description': '输入或更新剧本',
            'usage': '/script <剧本内容>',
            'example': '/script 2-1 日/内/大堂\n人物：A、B\nA: 你好',
        },
        '/style': {
            'description': '设置风格偏好',
            'usage': '/style <key>=<value>',
            'example': '/style mood=浪漫 visual=电影感',
        },
        '/ref': {
            'description': '添加参考图',
            'usage': '/ref <图片描述>',
            'example': '/ref 主角形象：年轻女性，短发',
        },
        '/phase': {
            'description': '执行特定阶段',
            'usage': '/phase <1|2|3|4|all>',
            'example': '/phase all',
        },
        '/status': {
            'description': '查看当前任务状态',
            'usage': '/status',
        },
        '/result': {
            'description': '获取执行结果',
            'usage': '/result [详细程度]',
            'example': '/result full',
        },
        '/reset': {
            'description': '重置当前任务',
            'usage': '/reset',
        },
        '/help': {
            'description': '显示帮助信息',
            'usage': '/help [命令名]',
            'example': '/help direct',
        },
        '/save': {
            'description': '保存任务到文件',
            'usage': '/save <文件名>',
            'example': '/save 任务1.json',
        },
        '/load': {
            'description': '从文件加载任务',
            'usage': '/load <文件名>',
            'example': '/load 任务1.json',
        },
    }
    
    def parse(self, input_text: str) -> Tuple[str, List[str], Dict[str, str]]:
        """
        解析输入文本
        
        Returns:
            (命令名, 位置参数, 关键字参数)
        """
        lines = input_text.strip().split('\n')
        first_line = lines[0].strip()
        
        # 检查是否是命令
        if not first_line.startswith('/'):
            return 'chat', [input_text], {}
        
        # 解析命令和参数
        parts = first_line.split()
        command = parts[0].lower()
        args = parts[1:]
        
        # 解析关键字参数 (key=value 格式)
        kwargs = {}
        remaining_args = []
        
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                kwargs[key] = value
            else:
                remaining_args.append(arg)
        
        # 如果有后续行，作为最后一个参数
        if len(lines) > 1:
            remaining_content = '\n'.join(lines[1:])
            if remaining_args:
                remaining_args[-1] += '\n' + remaining_content
            else:
                remaining_args.append(remaining_content)
        
        return command, remaining_args, kwargs
    
    def get_help(self, command: Optional[str] = None) -> str:
        """获取帮助信息"""
        if command and command in self.COMMANDS:
            cmd_info = self.COMMANDS[command]
            return f"""
命令: {command}
描述: {cmd_info['description']}
用法: {cmd_info['usage']}
示例: {cmd_info['example']}
"""
        
        # 返回所有命令列表
        help_text = ["可用命令:"]
        for cmd, info in self.COMMANDS.items():
            help_text.append(f"  {cmd} - {info['description']}")
        help_text.append("\n使用 /help <命令名> 查看详细说明")
        return '\n'.join(help_text)


class MCPDirectorServer:
    """
    MCP Director Server
    
    提供聊天界面的导演服务
    """
    
    def __init__(self):
        self.parser = CommandParser()
        self.ai_director = create_ai_director()
        self.current_task: Optional[DirectorTask] = None
        self.task_history: List[DirectorTask] = []
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output', 'mcp_tasks')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def process(self, user_input: str) -> str:
        """
        处理用户输入
        
        这是主要的入口点，接收用户聊天输入并返回响应
        """
        command, args, kwargs = self.parser.parse(user_input)
        
        # 命令分发
        handlers = {
            'chat': self._handle_chat,
            '/direct': self._handle_direct,
            '/script': self._handle_script,
            '/style': self._handle_style,
            '/ref': self._handle_ref,
            '/phase': self._handle_phase,
            '/status': self._handle_status,
            '/result': self._handle_result,
            '/reset': self._handle_reset,
            '/help': self._handle_help,
            '/save': self._handle_save,
            '/load': self._handle_load,
        }
        
        handler = handlers.get(command, self._handle_unknown)
        
        try:
            return handler(args, kwargs)
        except Exception as e:
            return f"[ERROR] 执行命令失败: {str(e)}\n{self._get_error_hint()}"
    
    def _handle_chat(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """处理普通聊天输入"""
        text = args[0] if args else ""
        
        # 如果没有当前任务，提示用户开始
        if not self.current_task:
            return f"""您好！我是 AI Director，可以帮助您完成导演分镜工作。

{text}

要开始一个新任务，请使用: /direct <任务名称>
或者查看帮助: /help
"""
        
        # 如果有任务，根据状态处理
        if self.current_task.status == TaskStatus.SCRIPT_INPUT:
            # 将聊天内容作为剧本
            self.current_task.script = text
            self.current_task.status = TaskStatus.CONFIGURING
            self.current_task.updated_at = datetime.now().isoformat()
            return f"""[OK] 剧本已接收 (长度: {len(text)} 字符)

现在您可以:
- 设置风格: /style mood=浪漫 visual=电影感
- 添加参考: /ref 主角形象描述
- 开始执行: /phase all
- 查看状态: /status
"""
        
        # 其他状态，提供通用响应
        return f"""收到: {text[:100]}{'...' if len(text) > 100 else ''}

当前任务状态: {self.current_task.status.value if self.current_task else '无'}
使用 /help 查看可用命令
"""
    
    def _handle_direct(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """开始新任务"""
        task_name = args[0] if args else f"任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 保存当前任务到历史
        if self.current_task:
            self.task_history.append(self.current_task)
        
        # 创建新任务
        self.current_task = DirectorTask(
            task_id=str(uuid.uuid4())[:8],
            status=TaskStatus.SCRIPT_INPUT,
        )
        
        # 应用 kwargs 中的配置
        if 'aspect' in kwargs:
            self.current_task.aspect_ratio = kwargs['aspect']
        if 'ratio' in kwargs:
            self.current_task.aspect_ratio = kwargs['ratio']
        
        return f"""[OK] 新导演任务已创建: {task_name}
任务ID: {self.current_task.task_id}

请直接输入剧本内容，或使用 /script 命令粘贴剧本。
例如:
/script
2-1 日/内/天御集团大堂
人物：乔熙、商北琛
▲商北琛迈步走进大堂...
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
        self.current_task.status = TaskStatus.CONFIGURING
        self.current_task.updated_at = datetime.now().isoformat()
        
        # 自动分析剧本
        analysis = self._quick_analyze(script)
        
        return f"""[OK] 剧本已更新 (长度: {len(script)} 字符)

快速分析:
- 场景数: {analysis.get('scene_count', 1)}
- 人物: {', '.join(analysis.get('characters', ['未知']))}
- 类型推测: {analysis.get('genre', '未知')}

下一步:
- 设置风格: /style mood=浪漫 pacing=快节奏
- 直接执行: /phase all
"""
    
    def _handle_style(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """设置风格"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。请先使用 /direct 创建任务。"
        
        # 更新风格偏好
        for key, value in kwargs.items():
            self.current_task.style_preferences[key] = value
        
        # 也处理位置参数
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

开始执行: /phase all
"""
    
    def _handle_ref(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """添加参考"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。请先使用 /direct 创建任务。"
        
        ref_desc = args[0] if args else ""
        if ref_desc:
            self.current_task.reference_images.append(ref_desc)
            self.current_task.updated_at = datetime.now().isoformat()
            return f"[OK] 参考信息已添加 ({len(self.current_task.reference_images)} 个)"
        
        return "请提供参考描述: /ref <描述>"
    
    def _handle_phase(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """执行阶段"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。请先使用 /direct 创建任务。"
        
        if not self.current_task.script:
            return "[ERROR] 请先输入剧本: /script <剧本内容>"
        
        phase = args[0] if args else 'all'
        
        if phase not in ['1', '2', '3', '4', 'all']:
            return "[ERROR] 阶段必须是 1, 2, 3, 4 或 all"
        
        # 执行任务
        return self._execute_phase(phase)
    
    def _execute_phase(self, phase: str) -> str:
        """执行导演阶段"""
        self.current_task.status = TaskStatus.RUNNING
        
        try:
            # 使用 AI Director Core 执行
            result = self.ai_director.direct(
                script=self.current_task.script,
                aspect_ratio=self.current_task.aspect_ratio,
                style_preferences=self.current_task.style_preferences,
                constraints=self.current_task.constraints,
                reference_images=self.current_task.reference_images,
            )
            
            if result['status'] == 'success':
                self.current_task.results = result['results']
                self.current_task.decisions = result['all_decisions']
                self.current_task.status = TaskStatus.COMPLETED
                self.current_task.updated_at = datetime.now().isoformat()
                
                # 生成结果摘要
                summary = self._generate_result_summary(result)
                
                return f"""[OK] 导演任务执行完成！

{summary}

查看详细结果: /result
保存任务: /save <文件名>
"""
            else:
                self.current_task.status = TaskStatus.ERROR
                return f"[ERROR] 执行失败: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            self.current_task.status = TaskStatus.ERROR
            return f"[ERROR] 执行异常: {str(e)}"
    
    def _handle_status(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """查看状态"""
        if not self.current_task:
            return "当前没有活动任务。使用 /direct 创建新任务。"
        
        task = self.current_task
        status_info = f"""当前任务状态:
- 任务ID: {task.task_id}
- 状态: {task.status.value}
- 剧本长度: {len(task.script)} 字符
- 画幅比例: {task.aspect_ratio}
- 风格偏好: {len(task.style_preferences)} 项
- 参考信息: {len(task.reference_images)} 个
- 创建时间: {task.created_at}
- 更新时间: {task.updated_at}
"""
        
        if task.decisions:
            status_info += f"\n- 决策数量: {len(task.decisions)}"
        
        return status_info
    
    def _handle_result(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """获取结果"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        if not self.current_task.results:
            return "[ERROR] 任务尚未执行。使用 /phase all 开始执行。"
        
        detail_level = args[0] if args else 'summary'
        
        if detail_level == 'full':
            # 返回完整结果
            return self._format_full_result()
        elif detail_level == 'decisions':
            # 只返回决策
            return self.ai_director.get_decision_report()
        else:
            # 返回摘要
            return self._generate_result_summary({
                'results': self.current_task.results,
                'all_decisions': self.current_task.decisions,
            })
    
    def _handle_reset(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """重置任务"""
        if self.current_task:
            self.task_history.append(self.current_task)
        self.current_task = None
        return "[OK] 当前任务已重置。使用 /direct 创建新任务。"
    
    def _handle_help(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """帮助信息"""
        command = args[0] if args else None
        return self.parser.get_help(command)
    
    def _handle_save(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """保存任务"""
        if not self.current_task:
            return "[ERROR] 没有活动任务。"
        
        filename = args[0] if args else f"task_{self.current_task.task_id}.json"
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 保存任务数据
        task_data = {
            'task': self.current_task.__dict__,
            'results': self.current_task.results,
            'decisions': self.current_task.decisions,
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
            self.current_task.results = task_data.get('results', {})
            self.current_task.decisions = task_data.get('decisions', [])
            
            return f"[OK] 任务已加载: {filename}\n任务ID: {self.current_task.task_id}"
            
        except Exception as e:
            return f"[ERROR] 加载失败: {str(e)}"
    
    def _handle_unknown(self, args: List[str], kwargs: Dict[str, str]) -> str:
        """未知命令"""
        return f"[ERROR] 未知命令。使用 /help 查看可用命令。"
    
    def _quick_analyze(self, script: str) -> Dict[str, Any]:
        """快速分析剧本"""
        # 简单的启发式分析
        scenes = len(re.findall(r'^\d+-\d+', script, re.MULTILINE))
        characters = list(set(re.findall(r'人物[：:](.+)', script)))
        
        # 类型推测
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
    
    def _generate_result_summary(self, result: Dict) -> str:
        """生成结果摘要"""
        results = result.get('results', {})
        decisions = result.get('all_decisions', [])
        
        summary = ["执行结果摘要:"]
        
        # Phase 1
        if 'phase1' in results:
            analysis = results['phase1'].get('analysis')
            if analysis:
                summary.append(f"\n[Phase 1] 剧本分析")
                summary.append(f"  - 类型: {analysis.genre}")
                summary.append(f"  - 情绪: {analysis.mood}")
                summary.append(f"  - 节奏: {analysis.pacing}")
        
        # Phase 2
        if 'phase2' in results:
            strategies = results['phase2'].get('shot_strategies', [])
            summary.append(f"\n[Phase 2] 分镜设计")
            summary.append(f"  - 段落策略: {len(strategies)} 个")
        
        # Phase 3
        if 'phase3' in results:
            rules = results['phase3'].get('optimization_rules', [])
            summary.append(f"\n[Phase 3] 细节优化")
            summary.append(f"  - 优化规则: {len(rules)} 条")
        
        # Phase 4
        if 'phase4' in results:
            strategy = results['phase4'].get('qc_strategy', '未知')
            summary.append(f"\n[Phase 4] 质量控制")
            summary.append(f"  - 质检策略: {strategy}")
        
        # 决策统计
        summary.append(f"\n[决策统计]")
        summary.append(f"  - 总决策数: {len(decisions)}")
        
        return '\n'.join(summary)
    
    def _format_full_result(self) -> str:
        """格式化完整结果"""
        if not self.current_task:
            return "[ERROR] 没有活动任务"
        
        result_text = ["=" * 80]
        result_text.append("完整导演方案")
        result_text.append("=" * 80)
        
        # 添加 AI Director 的最终输出
        final_output = self.ai_director._generate_final_output(self.current_task.results)
        result_text.append(final_output)
        
        # 添加决策报告
        result_text.append("\n" + "=" * 80)
        result_text.append("导演决策报告")
        result_text.append("=" * 80)
        result_text.append(self.ai_director.get_decision_report())
        
        return '\n'.join(result_text)
    
    def _get_error_hint(self) -> str:
        """获取错误提示"""
        return """
提示:
- 使用 /help 查看可用命令
- 使用 /status 查看当前任务状态
- 使用 /direct 创建新任务
"""


# 便捷函数
def create_mcp_server() -> MCPDirectorServer:
    """创建 MCP Director Server 实例"""
    return MCPDirectorServer()


# 全局实例（用于保持状态）
_mcp_server_instance: Optional[MCPDirectorServer] = None


def get_mcp_server() -> MCPDirectorServer:
    """获取或创建 MCP Server 实例"""
    global _mcp_server_instance
    if _mcp_server_instance is None:
        _mcp_server_instance = create_mcp_server()
    return _mcp_server_instance


def process_input(user_input: str) -> str:
    """
    处理用户输入的便捷函数
    
    这是主要的入口点，可以直接在聊天中调用
    """
    server = get_mcp_server()
    return server.process(user_input)


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("MCP Director Server 测试")
    print("=" * 80)
    
    server = create_mcp_server()
    
    # 模拟对话
    test_inputs = [
        "/help",
        "/direct 测试任务",
        "/script 2-1 日/内/大堂\n人物：A、B\nA: 你好",
        "/style mood=浪漫",
        "/status",
        "/phase all",
        "/result",
    ]
    
    for user_input in test_inputs:
        print(f"\n用户: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
        print(f"系统: {server.process(user_input)}")
