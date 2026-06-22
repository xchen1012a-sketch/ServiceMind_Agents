# Agent 运行时决策：LangGraph + Deep Agents 扩展边界

## 决策摘要

- 第一版核心工单流程使用 LangGraph。
- Deep Agents 不作为第一版主流程编排层。
- 通过 `AgentRuntime` 抽象预留 Deep Agents 和 custom runtime。

## 依据

- LangGraph 定位为 Agent orchestration runtime，适合 durable execution、streaming、human-in-the-loop 和 persistence。
- Deep Agents 是构建在 LangGraph 之上的高层 agent harness，适合 planning、subagents、filesystem tools 和 context management。
- 本项目核心诉求是工单状态可控、审批可中断、运行轨迹可审计、前端链路可回放，因此主流程需要显式状态机。

## 推荐架构

```text
AgentRuntime
├─ LangGraphRuntime        # 第一版核心实现
├─ DeepAgentsRuntime       # 后续高级任务实现
└─ CustomRuntime           # 预留实验或自研 runtime
```

## 核心流程

```text
ticket_intake
-> classify_ticket
-> retrieve_knowledge
-> call_tools
-> risk_review
-> approval_gate
-> generate_resolution
-> create_summary
-> knowledge_reflection
```

每个节点都必须写入 `agent_run_steps`。

## 数据库预留

- `agent_graph_versions.runtime_type`：`langgraph`、`deepagents`、`custom`。
- `agent_runs.runtime_type`：标记本次运行的实现。
- `agent_run_steps.external_step_ref`：保存外部 runtime 的节点或任务引用。
- `agent_run_steps.input_payload/output_payload`：保存节点级输入输出。

## Deep Agents 适用场景

- 复杂工单根因调查。
- 多步骤研究任务。
- 知识库自动整理。
- 生成排障报告。
- 长任务规划和子 Agent 协作。

## 禁止事项

- 不允许 Deep Agents 绕过审批模块直接执行高风险工具。
- 不允许将不可审计的长任务结果直接写入工单最终结论。
- 不允许只存最终回答而丢失步骤级运行轨迹。
