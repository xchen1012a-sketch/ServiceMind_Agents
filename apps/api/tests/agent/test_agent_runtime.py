from app.modules.agent.runtime import LangGraphTicketRuntime


def test_langgraph_runtime_completes_low_risk_ticket() -> None:
    result = LangGraphTicketRuntime().run(
        {
            "ticket_id": "ticket-1",
            "title": "无法查看订单",
            "category_code": "order",
            "priority": "medium",
            "risk_level": "low",
        }
    )

    assert result.status == "completed"
    assert [step.name for step in result.steps] == [
        "classify_ticket",
        "risk_review",
        "generate_summary",
    ]


def test_langgraph_runtime_pauses_high_risk_ticket() -> None:
    result = LangGraphTicketRuntime().run(
        {
            "ticket_id": "ticket-2",
            "title": "请求删除客户数据",
            "category_code": "privacy",
            "priority": "urgent",
            "risk_level": "high",
        }
    )

    assert result.status == "waiting_approval"
    assert result.steps[-1].name == "approval_gate"
    assert result.steps[-1].status == "waiting_approval"
