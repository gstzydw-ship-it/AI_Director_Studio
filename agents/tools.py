"""
CrewAI RAG 检索工具
供各 Agent 在执行任务时调用，从向量知识库检索相关导演规则
"""

from crewai.tools import BaseTool
from pydantic import Field
from typing import Type
from pydantic import BaseModel


class DirectorKnowledgeInput(BaseModel):
    """导演知识库检索工具的输入参数"""
    query: str = Field(description="The director knowledge query, e.g. 'close-up shot focal length rules'")


class DirectorKnowledgeTool(BaseTool):
    name: str = "director_knowledge_search"
    description: str = (
        "Search the director knowledge base for relevant rules and cases. "
        "Input a query about directing (e.g. 'focal length rules for close-up', "
        "'how to handle double information bombs'), returns the most relevant knowledge chunks."
    )
    args_schema: Type[BaseModel] = DirectorKnowledgeInput
    agent_name: str = Field(default="", description="Current agent name for filtering relevant knowledge")

    def _run(self, query: str) -> str:
        try:
            from agents.knowledge_base import query_knowledge
            results = query_knowledge(
                query=query,
                agent_name=self.agent_name,
                n_results=5
            )
        except Exception as e:
            return f"Knowledge base query failed: {str(e)}. Please proceed with your professional judgment."

        if not results:
            return "No relevant knowledge found. Please proceed with your professional judgment."

        output_parts = []
        for i, item in enumerate(results, 1):
            output_parts.append(
                f"[Knowledge {i}] (source: {item['source']}, relevance: {item['relevance']:.2f})\n"
                f"{item['text']}\n"
            )

        return "\n---\n".join(output_parts)
