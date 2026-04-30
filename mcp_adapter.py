"""
MCP Adapter - 聊天界面适配器

将 MCP Director 服务集成到聊天环境中
"""

import sys
import os

# 确保可以导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_director_server import get_mcp_server, process_input


class MCPDirectorChat:
    """
    MCP Director 聊天适配器
    
    提供简洁的聊天界面集成
    """
    
    def __init__(self):
        self.server = get_mcp_server()
        self.welcome_shown = False
    
    def chat(self, user_input: str) -> str:
        """
        处理聊天输入
        
        这是主要的聊天接口
        """
        # 显示欢迎信息（首次）
        if not self.welcome_shown and user_input.strip().lower() in ['', 'hello', 'hi', '你好']:
            self.welcome_shown = True
            return self._get_welcome_message()
        
        # 处理输入
        return self.server.process(user_input)
    
    def _get_welcome_message(self) -> str:
        """获取欢迎信息"""
        return """
╔════════════════════════════════════════════════════════════════╗
║                    AI Director MCP 服务                        ║
║                     导演分镜智能助手                           ║
╚════════════════════════════════════════════════════════════════╝

您好！我是 AI Director，专门帮助您完成导演分镜工作。

快速开始:
1. /direct <任务名>  - 创建新任务
2. /script <剧本>    - 输入剧本
3. /phase all        - 执行导演
4. /result           - 查看结果

帮助: /help

请告诉我您想要导演什么内容？
"""


# 全局实例
_chat_instance: MCPDirectorChat = None


def get_chat() -> MCPDirectorChat:
    """获取聊天实例"""
    global _chat_instance
    if _chat_instance is None:
        _chat_instance = MCPDirectorChat()
    return _chat_instance


def director_chat(user_input: str) -> str:
    """
    导演聊天函数 - 主要入口
    
    在聊天中直接调用此函数即可
    
    Args:
        user_input: 用户输入的文本
        
    Returns:
        系统的响应
        
    示例:
        >>> director_chat("/direct 测试任务")
        >>> director_chat("/help")
    """
    chat = get_chat()
    return chat.chat(user_input)


# 便捷别名
dc = director_chat  # 短别名，方便使用


# 测试
if __name__ == "__main__":
    print("=" * 80)
    print("MCP Director Chat 测试")
    print("=" * 80)
    
    # 模拟对话
    test_conversation = [
        "",
        "/direct 爱情戏",
        "/script 2-1 日/内/大堂\n人物：A、B\nA: 你好",
        "/style mood=浪漫",
        "/phase all",
        "/result",
    ]
    
    for user_input in test_conversation:
        print(f"\n[用户] {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
        response = director_chat(user_input)
        print(f"[系统] {response}")
