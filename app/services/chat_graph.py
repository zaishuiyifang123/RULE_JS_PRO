from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.constants import START
from langgraph.graph import END, StateGraph


class IntentGraphState(TypedDict):
    message: str
    history_user_messages: list[str]
    threshold: float
    model_name: str | None
    result: dict[str, Any]


def run_task010_intent_graph(
    message: str,
    history_user_messages: list[str],
    threshold: float,
    model_name: str | None,
    node_executor: Callable[[str, list[str], float, str | None], dict[str, Any]],
    node_io_logger: Callable[[str, dict[str, Any], dict[str, Any] | None, str, str | None], None] | None = None,
) -> dict[str, Any]:
    """执行 TASK010 的单节点 LangGraph。"""
    state: IntentGraphState = {
        "message": message,
        "history_user_messages": history_user_messages,
        "threshold": threshold,
        "model_name": model_name,
        "result": {},
    }

    def intent_node(node_state: IntentGraphState) -> IntentGraphState:
        node_input = {
            "message": node_state["message"],
            "history_user_messages": node_state["history_user_messages"],
            "threshold": node_state["threshold"],
            "model_name": node_state["model_name"],
        }
        try:
            result = node_executor(
                node_state["message"],
                node_state["history_user_messages"],
                node_state["threshold"],
                node_state["model_name"],
            )
            if node_io_logger:
                node_io_logger("intent_recognition", node_input, result, "success", None)
            return {**node_state, "result": result}
        except Exception as exc:
            if node_io_logger:
                node_io_logger("intent_recognition", node_input, None, "failed", str(exc))
            raise

    graph = StateGraph(IntentGraphState)
    graph.add_node("intent_recognition", intent_node)
    graph.add_edge(START, "intent_recognition")
    graph.add_edge("intent_recognition", END)
    app = graph.compile()
    output = app.invoke(state)
    return output["result"]
