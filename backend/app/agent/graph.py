"""LangGraph assembly of the extraction agent.

Nodes share their logic with the direct runner (single source of truth in
``AgentNodes``). The graph is the agentic representation used for the API /
human-in-the-loop path (the Postgres checkpointer + ``interrupt`` are wired in
the persistence phase).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import AgentNodes
from app.agent.state import PipelineState


def build_graph(nodes: AgentNodes, checkpointer=None):
    g = StateGraph(PipelineState)
    g.add_node("extract", nodes.extract)
    g.add_node("classify_and_assemble", nodes.classify_and_assemble)
    g.add_node("validate", nodes.validate)
    g.add_node("score", nodes.score)
    g.add_node("route", nodes.route)
    g.add_node("finalize", nodes.finalize)

    g.add_edge(START, "extract")
    g.add_edge("extract", "classify_and_assemble")
    g.add_edge("classify_and_assemble", "validate")
    g.add_edge("validate", "score")
    g.add_edge("score", "route")
    g.add_edge("route", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer)
