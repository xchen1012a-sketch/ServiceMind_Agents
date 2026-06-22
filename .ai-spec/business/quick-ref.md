# 业务快速参考（AI 实时维护）

> 日常启动唯一入口：普通会话只读本文件；`maintenanceDue` 到期才读 `.ai-spec/workflows/context-maintenance.md`；大文件先搜索并按不超过 250 行分段读取。
> status: GENERATED
> dailyEntry: true
> dynamicContextGate: true
> outputLanguage: zh-CN
> maintenanceDue: 2026-07-06
> projectSize: medium
> sizeStrategy: planned-monorepo
> 模板初始状态为 status: TEMPLATE_PLACEHOLDER；生成后改为 GENERATED。
## 项目定位
- 一句话定位：企业工单与知识库多 Agent 处理平台，覆盖工单接入、LangGraph 编排、RAG、MCP 工具、人工审批、AgentOps 观测和离线评估。
- 项目类型：AI/LLM 全栈应用，计划采用 monorepo。
- 主要入口：`docs/plans/current.md`、`docs/plans/project-plan.md`、`docs/plans/database-design-plan.md`
## 核心业务域
| 业务域 | 说明 |
|---|---|
| 工单处理 | 工单、消息、状态流转和处理记录 |
| Agent 编排 | LangGraph 主流程、运行轨迹、节点步骤和模型调用 |
| 知识库 RAG | 文档、版本、chunk、embedding、检索命中和引用来源 |
| MCP 工具与审批 | 受控工具调用、高风险动作审批和执行审计 |
| AgentOps 与评估 | 链路观测、失败原因、离线评估指标 |
## 关键不变量
- 高风险工具调用必须进入人工审批，审批通过前不得执行写动作。
- Agent 与业务系统只能通过受控 MCP 工具交互。
- 每次运行必须写入 `agent_runs`，每个节点必须写入 `agent_run_steps`。
- RAG 回答必须追溯到文档版本、chunk 和检索命中。
## 动态上下文门禁
| 任务等级 | 默认读取 | 升级条件 |
|---|---|---|
| L0/L1 | 本文件 + 命中文件片段 | 影响行为时升 L2 |
| L2 | 本文件 + `core-lite/delivery-lite.md` + 相关源码 | 涉及测试/安全加 core-lite |
| L3/L4 | 相关 contracts/core/stacks + 计划文件 | API/DB/权限/安全/完整审计 |
## 实施硬门禁
计划自动触发门禁：项目级/分阶段、多模块验收或跨接口/数据/权限/安全/进程边界时读 `.ai-spec/workflows/project-planning.md`，无需用户额外提醒；先恢复 `docs/plans/current.md`，必要时读 `docs/plans/project-plan.md`。
新增/调整模块、目录、共享抽象或跨模块调用时检查 `docs/architecture/modules.md`；缺失则用 `.ai-spec/governance/module-contract-template.md`。
改 API/DTO/DB/权限/页面/进程/外部系统时填写影响矩阵；核心链路检查 `docs/quality/regression-checklist.md`，缺失则用 `.ai-spec/governance/regression-checklist-template.md`。
