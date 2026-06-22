import {
  Bot,
  CheckCircle2,
  CircleAlert,
  Database,
  FileText,
  GitBranch,
  Loader2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

type HealthPayload = {
  status: string;
  service: string;
  version: string;
  environment: string;
};

type TicketListItem = {
  id: string;
  tenant_id: string;
  ticket_no: string;
  title: string;
  category_code: string;
  priority: string;
  risk_level: string;
  status: string;
  source_channel: string;
  requester_name: string | null;
  requester_contact: string | null;
  created_at: string;
  updated_at: string;
};

type TicketMessage = {
  id: string;
  sender_type: string;
  message_text: string;
  message_format: string;
  created_at: string;
};

type TicketStatusEvent = {
  id: string;
  from_status: string | null;
  to_status: string;
  reason_text: string | null;
  changed_by_type: string;
  created_at: string;
};

type TicketDetail = TicketListItem & {
  description_text: string;
  assigned_user_id: string | null;
  created_by_user_id: string | null;
  messages: TicketMessage[];
  status_events: TicketStatusEvent[];
};

type HealthState =
  | { status: "loading" }
  | { status: "ready"; data: HealthPayload }
  | { status: "error"; message: string };

type TicketState =
  | { status: "idle"; tickets: TicketListItem[]; selected: TicketDetail | null; message?: string }
  | { status: "loading"; tickets: TicketListItem[]; selected: TicketDetail | null; message?: string }
  | { status: "error"; tickets: TicketListItem[]; selected: TicketDetail | null; message: string };

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:18080";

const navItems = [
  { label: "工单工作台", icon: FileText },
  { label: "Agent 链路", icon: GitBranch },
  { label: "知识库", icon: Database },
  { label: "MCP 工具", icon: Wrench },
  { label: "审批中心", icon: ShieldCheck },
];

const priorityOptions = ["low", "medium", "high", "urgent"];
const statusActions: Record<string, string[]> = {
  new: ["triaged", "cancelled"],
  triaged: ["in_progress", "cancelled"],
  in_progress: ["waiting_customer", "resolved", "cancelled"],
  waiting_customer: ["in_progress", "resolved", "cancelled"],
  resolved: ["closed", "reopened"],
  reopened: ["in_progress", "cancelled"],
};

function getInitialTenantId() {
  const saved = localStorage.getItem("servicemind.tenant_id");
  if (saved) {
    return saved;
  }
  const generated = crypto.randomUUID();
  localStorage.setItem("servicemind.tenant_id", generated);
  return generated;
}

function getInitialUserId() {
  const saved = localStorage.getItem("servicemind.user_id");
  if (saved) {
    return saved;
  }
  const generated = crypto.randomUUID();
  localStorage.setItem("servicemind.user_id", generated);
  return generated;
}

function contextHeaders(tenantId: string, userId: string, permissions: string) {
  return {
    "X-ServiceMind-Tenant-Id": tenantId,
    "X-ServiceMind-User-Id": userId,
    "X-ServiceMind-Permissions": permissions,
  };
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

function useHealth(): HealthState {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    requestJson<HealthPayload>("/health", { signal: controller.signal })
      .then((data) => setHealth({ status: "ready", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const message = error instanceof Error ? error.message : "unknown error";
        setHealth({ status: "error", message });
      });

    return () => controller.abort();
  }, []);

  return health;
}

export function App() {
  const health = useHealth();
  const [tenantId, setTenantId] = useState(getInitialTenantId);
  const [userId] = useState(getInitialUserId);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [ticketState, setTicketState] = useState<TicketState>({
    status: "idle",
    tickets: [],
    selected: null,
  });

  const healthStatus = useMemo(() => {
    if (health.status === "ready") {
      return { label: "后端在线", tone: "success", icon: CheckCircle2 };
    }
    if (health.status === "error") {
      return { label: "后端未连接", tone: "danger", icon: CircleAlert };
    }
    return { label: "检查中", tone: "pending", icon: Loader2 };
  }, [health]);

  const StatusIcon = healthStatus.icon;

  function persistTenantId(value: string) {
    setTenantId(value);
    localStorage.setItem("servicemind.tenant_id", value);
  }

  async function loadTickets(nextTenantId = tenantId) {
    setTicketState((current) => ({ ...current, status: "loading" }));
    try {
      const headers = contextHeaders(nextTenantId, userId, "tickets:read");
      const tickets = await requestJson<TicketListItem[]>("/api/v1/tickets", { headers });
      const selected =
        ticketState.selected && tickets.some((ticket) => ticket.id === ticketState.selected?.id)
          ? await requestJson<TicketDetail>(`/api/v1/tickets/${ticketState.selected.id}`, {
              headers,
            })
          : null;
      setTicketState({ status: "idle", tickets, selected });
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown error";
      setTicketState((current) => ({ ...current, status: "error", message }));
    }
  }

  async function selectTicket(ticketId: string) {
    setTicketState((current) => ({ ...current, status: "loading" }));
    try {
      const selected = await requestJson<TicketDetail>(`/api/v1/tickets/${ticketId}`, {
        headers: contextHeaders(tenantId, userId, "tickets:read"),
      });
      setTicketState((current) => ({ ...current, status: "idle", selected }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown error";
      setTicketState((current) => ({ ...current, status: "error", message }));
    }
  }

  async function createTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTicketState((current) => ({ ...current, status: "loading" }));
    try {
      const created = await requestJson<TicketDetail>("/api/v1/tickets", {
        method: "POST",
        headers: contextHeaders(tenantId, userId, "tickets:create,tickets:read"),
        body: JSON.stringify({
          title,
          description_text: description,
          category_code: "general",
          priority,
          risk_level: priority === "urgent" ? "high" : "low",
          source_channel: "web",
        }),
      });
      const tickets = await requestJson<TicketListItem[]>("/api/v1/tickets", {
        headers: contextHeaders(tenantId, userId, "tickets:read"),
      });
      setTitle("");
      setDescription("");
      setTicketState({ status: "idle", tickets, selected: created, message: "工单已创建" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown error";
      setTicketState((current) => ({ ...current, status: "error", message }));
    }
  }

  async function changeStatus(toStatus: string) {
    if (!ticketState.selected) {
      return;
    }
    setTicketState((current) => ({ ...current, status: "loading" }));
    try {
      const selected = await requestJson<TicketDetail>(
        `/api/v1/tickets/${ticketState.selected.id}/status`,
        {
          method: "POST",
          headers: contextHeaders(tenantId, userId, "tickets:update,tickets:read"),
          body: JSON.stringify({
            to_status: toStatus,
            reason_text: `frontend transition to ${toStatus}`,
          }),
        },
      );
      const tickets = await requestJson<TicketListItem[]>("/api/v1/tickets", {
        headers: contextHeaders(tenantId, userId, "tickets:read"),
      });
      setTicketState({ status: "idle", tickets, selected, message: "状态已更新" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown error";
      setTicketState((current) => ({ ...current, status: "error", message }));
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <div className="brandMark">
            <Bot size={24} aria-hidden="true" />
          </div>
          <div>
            <strong>ServiceMind</strong>
            <span>Agents Console</span>
          </div>
        </div>
        <nav className="navList">
          {navItems.map((item) => (
            <a href="/" className="navItem" key={item.label}>
              <item.icon size={18} aria-hidden="true" />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">阶段 03</p>
            <h1>工单工作台</h1>
          </div>
          <div className={`statusPill ${healthStatus.tone}`}>
            <StatusIcon
              size={18}
              aria-hidden="true"
              className={health.status === "loading" ? "spin" : ""}
            />
            <span>{healthStatus.label}</span>
          </div>
        </header>

        <section className="ticketGrid" aria-label="工单工作台">
          <section className="panel stackPanel">
            <div className="panelHeader">
              <FileText size={20} aria-hidden="true" />
              <h2>创建工单</h2>
            </div>
            <label className="field">
              <span>Tenant ID</span>
              <input value={tenantId} onChange={(event) => persistTenantId(event.target.value)} />
            </label>
            <form className="ticketForm" onSubmit={createTicket}>
              <label className="field">
                <span>标题</span>
                <input value={title} onChange={(event) => setTitle(event.target.value)} required />
              </label>
              <label className="field">
                <span>描述</span>
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  required
                  rows={5}
                />
              </label>
              <label className="field">
                <span>优先级</span>
                <select value={priority} onChange={(event) => setPriority(event.target.value)}>
                  {priorityOptions.map((option) => (
                    <option value={option} key={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <button className="primaryButton" type="submit" disabled={ticketState.status === "loading"}>
                <Plus size={18} aria-hidden="true" />
                <span>创建</span>
              </button>
            </form>
          </section>

          <section className="panel stackPanel">
            <div className="panelHeader splitHeader">
              <div className="inlineTitle">
                <RefreshCw size={20} aria-hidden="true" />
                <h2>工单列表</h2>
              </div>
              <button
                className="iconButton"
                type="button"
                onClick={() => void loadTickets()}
                aria-label="刷新工单列表"
                title="刷新"
              >
                <RefreshCw size={18} aria-hidden="true" />
              </button>
            </div>
            <div className="ticketList">
              {ticketState.tickets.map((ticket) => (
                <button
                  className={`ticketRow ${ticketState.selected?.id === ticket.id ? "active" : ""}`}
                  type="button"
                  key={ticket.id}
                  onClick={() => void selectTicket(ticket.id)}
                >
                  <span>
                    <strong>{ticket.title}</strong>
                    <small>{ticket.ticket_no}</small>
                  </span>
                  <em>{ticket.status}</em>
                </button>
              ))}
              {ticketState.tickets.length === 0 ? (
                <div className="emptyBlock">暂无工单</div>
              ) : null}
            </div>
          </section>

          <section className="panel detailPanel">
            <div className="panelHeader">
              <GitBranch size={20} aria-hidden="true" />
              <h2>详情与流转</h2>
            </div>
            {ticketState.selected ? (
              <div className="detailStack">
                <div>
                  <strong className="detailTitle">{ticketState.selected.title}</strong>
                  <p>{ticketState.selected.description_text}</p>
                </div>
                <div className="metaGrid">
                  <span>状态：{ticketState.selected.status}</span>
                  <span>优先级：{ticketState.selected.priority}</span>
                  <span>风险：{ticketState.selected.risk_level}</span>
                  <span>来源：{ticketState.selected.source_channel}</span>
                </div>
                <div className="actionRow">
                  {(statusActions[ticketState.selected.status] ?? []).map((status) => (
                    <button
                      className="secondaryButton"
                      type="button"
                      key={status}
                      onClick={() => void changeStatus(status)}
                    >
                      {status}
                    </button>
                  ))}
                </div>
                <div className="eventList">
                  {ticketState.selected.status_events.map((event) => (
                    <div className="eventRow" key={event.id}>
                      <span>
                        {event.from_status ?? "none"}
                        {" -> "}
                        {event.to_status}
                      </span>
                      <small>{event.reason_text ?? event.changed_by_type}</small>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="emptyBlock">请选择工单</div>
            )}
          </section>
        </section>

        {ticketState.status === "error" || ticketState.message ? (
          <div className={`toast ${ticketState.status === "error" ? "danger" : "success"}`}>
            {ticketState.status === "error" ? ticketState.message : ticketState.message}
          </div>
        ) : null}
      </section>
    </main>
  );
}
