from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class TicketAgentState(TypedDict, total=False):
    ticket_id: str
    title: str
    category_code: str
    priority: str
    risk_level: str
    classification: str
    requires_approval: bool
    summary: str


@dataclass(frozen=True)
class RuntimeStep:
    name: str
    step_type: str
    status: str
    input_payload: dict
    output_payload: dict | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class RuntimeResult:
    status: str
    steps: list[RuntimeStep]


class LangGraphTicketRuntime:
    runtime_type = "langgraph"

    def __init__(self) -> None:
        graph = StateGraph(TicketAgentState)
        graph.add_node("classify_ticket", self._classify_ticket)
        graph.add_node("risk_review", self._risk_review)
        graph.add_node("approval_gate", self._approval_gate)
        graph.add_node("generate_summary", self._generate_summary)
        graph.add_edge(START, "classify_ticket")
        graph.add_edge("classify_ticket", "risk_review")
        graph.add_conditional_edges(
            "risk_review",
            self._route_after_risk,
            {
                "approval_gate": "approval_gate",
                "generate_summary": "generate_summary",
            },
        )
        graph.add_edge("approval_gate", END)
        graph.add_edge("generate_summary", END)
        self._graph = graph.compile()

    def run(self, state: TicketAgentState) -> RuntimeResult:
        result = self._graph.invoke(state)
        steps = [
            RuntimeStep(
                name="classify_ticket",
                step_type="classification",
                status="completed",
                input_payload={"title": state["title"], "category_code": state["category_code"]},
                output_payload={"classification": result["classification"]},
            ),
            RuntimeStep(
                name="risk_review",
                step_type="risk",
                status="completed",
                input_payload={
                    "priority": state["priority"],
                    "risk_level": state["risk_level"],
                },
                output_payload={"requires_approval": result["requires_approval"]},
            ),
        ]
        if result["requires_approval"]:
            steps.append(
                RuntimeStep(
                    name="approval_gate",
                    step_type="approval",
                    status="waiting_approval",
                    input_payload={"risk_level": state["risk_level"]},
                    output_payload={"pause_reason": "manual_approval_required"},
                )
            )
            return RuntimeResult(status="waiting_approval", steps=steps)

        steps.append(
            RuntimeStep(
                name="generate_summary",
                step_type="generation",
                status="completed",
                input_payload={"classification": result["classification"]},
                output_payload={"summary": result["summary"]},
            )
        )
        return RuntimeResult(status="completed", steps=steps)

    def _classify_ticket(self, state: TicketAgentState) -> TicketAgentState:
        return {"classification": state["category_code"]}

    def _risk_review(self, state: TicketAgentState) -> TicketAgentState:
        requires_approval = state["priority"] == "urgent" or state["risk_level"] in {
            "high",
            "critical",
        }
        return {"requires_approval": requires_approval}

    def _approval_gate(self, state: TicketAgentState) -> TicketAgentState:
        return {"summary": "manual approval required before continuing"}

    def _generate_summary(self, state: TicketAgentState) -> TicketAgentState:
        return {"summary": f"{state['classification']} ticket is ready for operator review"}

    def _route_after_risk(self, state: TicketAgentState) -> str:
        if state["requires_approval"]:
            return "approval_gate"
        return "generate_summary"
