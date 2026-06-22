import uuid

import pytest
from tickets.fakes import InMemoryTicketRepository

from app.modules.tickets.schemas import TicketCreate, TicketStatusChange
from app.modules.tickets.service import (
    INITIAL_STATUS,
    TicketService,
    TicketStateTransitionError,
)


def test_create_ticket_writes_initial_message_and_status_event() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryTicketRepository()
    service = TicketService(repository)

    ticket = service.create_ticket(
        TicketCreate(
            tenant_id=tenant_id,
            title="订单退款咨询",
            description_text="客户询问退款进度",
            category_code="refund",
            priority="high",
            risk_level="medium",
        )
    )

    assert ticket.status == INITIAL_STATUS
    assert ticket.messages[0].message_text == "客户询问退款进度"
    assert ticket.status_events[0].from_status is None
    assert ticket.status_events[0].to_status == INITIAL_STATUS
    assert repository.commits == 1


def test_change_status_writes_status_event() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryTicketRepository()
    service = TicketService(repository)
    ticket = service.create_ticket(
        TicketCreate(
            tenant_id=tenant_id,
            title="账号登录失败",
            description_text="用户无法登录后台",
        )
    )

    updated = service.change_status(
        ticket.id,
        TicketStatusChange(
            tenant_id=tenant_id,
            to_status="triaged",
            reason_text="已完成人工分诊",
        ),
    )

    assert updated.status == "triaged"
    assert updated.status_events[-1].from_status == INITIAL_STATUS
    assert updated.status_events[-1].to_status == "triaged"
    assert updated.status_events[-1].reason_text == "已完成人工分诊"


def test_illegal_status_transition_is_rejected() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryTicketRepository()
    service = TicketService(repository)
    ticket = service.create_ticket(
        TicketCreate(
            tenant_id=tenant_id,
            title="状态非法跳转",
            description_text="新工单不能直接关闭",
        )
    )

    with pytest.raises(TicketStateTransitionError):
        service.change_status(
            ticket.id,
            TicketStatusChange(tenant_id=tenant_id, to_status="closed"),
        )

    assert repository.status_events[-1].to_status == INITIAL_STATUS
