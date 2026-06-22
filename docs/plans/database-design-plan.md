# 数据库设计计划：ServiceMind Agents

## 1. 设计目标

数据库是本项目的长期地基，需要同时支撑：

- 工单业务状态。
- Agent 编排运行轨迹。
- RAG 文档、chunk、embedding 和检索命中。
- MCP 工具注册与调用审计。
- 高风险动作人工审批。
- Prompt、模型、风险策略版本化。
- 离线评估和指标追踪。
- 审计、异步任务和 outbox 事件。

## 2. 基础规范

- 数据库：PostgreSQL。
- 向量能力：pgvector。
- 迁移工具：Alembic。
- 主键：`id UUID PRIMARY KEY`。
- 多租户：核心业务表统一带 `tenant_id UUID NOT NULL`。
- 时间字段：`created_at TIMESTAMPTZ NOT NULL`、`updated_at TIMESTAMPTZ NOT NULL`。
- 删除策略：业务主表使用 `deleted_at TIMESTAMPTZ` 软删除。
- 审计字段：涉及人工动作的表增加 `created_by_user_id`、`decided_by_user_id`、`changed_by_user_id` 等明确字段。
- 状态字段：统一使用 `status TEXT NOT NULL`，状态枚举由应用层和文档约束。
- 金额字段：统一使用 `NUMERIC(18, 4)`。
- JSON 字段：只用于 AI 输入输出、工具 payload、扩展 metadata；需要筛选、排序、统计的字段必须原子化拆列。
- 命名：全库 `snake_case`；外键字段写完整语义，例如 `approved_by_user_id`，不用模糊的 `user_id`。
- 禁止泛化字段：避免无语义的 `data`、`info`、`content`、`result`；必须使用领域前缀，例如 `message_text`、`response_payload`、`metric_detail_json`。

## 3. 表分组与表结构

### 3.1 租户、用户、权限

#### tenants

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| name | TEXT | 租户名称 |
| slug | TEXT | 租户唯一标识 |
| status | TEXT | active / suspended / archived |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |
| deleted_at | TIMESTAMPTZ | 软删除时间 |

#### users

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| tenant_id | UUID | 租户 |
| email | TEXT | 登录邮箱 |
| display_name | TEXT | 显示名 |
| password_hash | TEXT | 密码哈希 |
| status | TEXT | active / disabled |
| last_login_at | TIMESTAMPTZ | 最近登录 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |
| deleted_at | TIMESTAMPTZ | 软删除时间 |

#### roles / permissions / role_permissions / user_roles

用于 RBAC。`permissions.code` 全局唯一，`roles.code` 在租户内唯一。

### 3.2 工单主域

#### tickets

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| tenant_id | UUID | 租户 |
| ticket_no | TEXT | 工单编号，租户内唯一 |
| title | TEXT | 标题 |
| description | TEXT | 原始描述 |
| category_code | TEXT | 分类 |
| priority | TEXT | low / medium / high / urgent |
| risk_level | TEXT | low / medium / high / critical |
| status | TEXT | 当前状态 |
| source_channel | TEXT | web / api / email / import |
| requester_name | TEXT | 请求人名称 |
| requester_contact | TEXT | 请求人联系方式 |
| assigned_user_id | UUID | 负责人 |
| created_by_user_id | UUID | 创建人 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |
| deleted_at | TIMESTAMPTZ | 软删除时间 |

#### ticket_messages

用于保存用户、客户、Agent、系统消息。

字段：`id`、`tenant_id`、`ticket_id`、`sender_type`、`sender_user_id`、`message_text`、`message_format`、`created_at`。

#### ticket_status_events

用于保存状态历史，不把历史塞进 `tickets`。

字段：`id`、`tenant_id`、`ticket_id`、`from_status`、`to_status`、`reason`、`changed_by_type`、`changed_by_user_id`、`agent_run_id`、`created_at`。

### 3.3 Agent 编排与运行记录

#### agent_graph_versions

字段：`id`、`tenant_id`、`runtime_type`、`graph_name`、`graph_version`、`definition_hash`、`definition_json`、`is_active`、`created_at`。

`runtime_type` 预留：`langgraph`、`deepagents`、`custom`。

#### agent_runs

字段：`id`、`tenant_id`、`ticket_id`、`runtime_type`、`graph_version_id`、`status`、`started_at`、`finished_at`、`total_latency_ms`、`total_prompt_tokens`、`total_completion_tokens`、`total_cost_amount`、`error_code`、`error_message`、`created_at`。

#### agent_run_steps

字段：`id`、`tenant_id`、`agent_run_id`、`step_name`、`step_type`、`step_order`、`external_step_ref`、`status`、`input_payload`、`output_payload`、`latency_ms`、`prompt_tokens`、`completion_tokens`、`error_code`、`error_message`、`started_at`、`finished_at`、`created_at`。

#### model_invocations

字段：`id`、`tenant_id`、`agent_run_id`、`agent_run_step_id`、`provider_code`、`model_name`、`prompt_version_id`、`request_payload`、`response_payload`、`prompt_tokens`、`completion_tokens`、`latency_ms`、`cost_amount`、`status`、`created_at`。

### 3.4 知识库与 RAG

#### knowledge_spaces

字段：`id`、`tenant_id`、`name`、`description`、`visibility`、`status`、`created_by_user_id`、`created_at`、`updated_at`、`deleted_at`。

#### knowledge_documents

字段：`id`、`tenant_id`、`knowledge_space_id`、`title`、`source_type`、`source_uri`、`file_name`、`mime_type`、`status`、`current_version_id`、`created_by_user_id`、`created_at`、`updated_at`、`deleted_at`。

#### knowledge_document_versions

字段：`id`、`tenant_id`、`document_id`、`version_no`、`storage_uri`、`content_hash`、`parser_name`、`parser_version`、`parse_status`、`created_at`。

#### knowledge_chunks

字段：`id`、`tenant_id`、`document_version_id`、`chunk_index`、`chunk_text`、`token_count`、`heading_path`、`page_number`、`source_anchor`、`metadata`、`created_at`。

#### embedding_models

字段：`id`、`provider_code`、`model_name`、`dimension`、`status`、`created_at`。

#### chunk_embeddings

字段：`id`、`tenant_id`、`chunk_id`、`embedding_model_id`、`embedding_vector`、`embedding_hash`、`created_at`。

#### rag_queries / rag_retrieval_hits

用于记录查询文本、检索参数、命中 chunk、相似度、rerank 分和是否用于最终回答。

### 3.5 MCP 工具与调用审计

#### mcp_servers

字段：`id`、`tenant_id`、`code`、`name`、`transport_type`、`endpoint_url`、`status`、`created_at`、`updated_at`。

#### mcp_tools

字段：`id`、`tenant_id`、`mcp_server_id`、`tool_name`、`display_name`、`description`、`input_schema_json`、`output_schema_json`、`risk_level`、`requires_approval`、`status`、`created_at`、`updated_at`。

#### tool_calls

字段：`id`、`tenant_id`、`agent_run_id`、`agent_run_step_id`、`mcp_server_id`、`mcp_tool_id`、`status`、`input_payload`、`output_payload`、`error_code`、`error_message`、`latency_ms`、`approval_request_id`、`created_at`。

### 3.6 审批与高风险动作

#### approval_requests

字段：`id`、`tenant_id`、`ticket_id`、`agent_run_id`、`tool_call_id`、`action_type`、`risk_level`、`reason`、`proposed_payload`、`status`、`requested_by_type`、`requested_by_user_id`、`expires_at`、`created_at`、`updated_at`。

#### approval_decisions

字段：`id`、`tenant_id`、`approval_request_id`、`decision`、`decision_reason`、`decided_by_user_id`、`decided_at`、`created_at`。

#### approved_action_executions

字段：`id`、`tenant_id`、`approval_request_id`、`tool_call_id`、`execution_status`、`execution_payload`、`execution_result`、`error_code`、`error_message`、`executed_at`、`created_at`。

### 3.7 Prompt、模型配置和风险策略

表：`prompt_templates`、`prompt_versions`、`risk_policies`、`risk_policy_rules`。

目标：Prompt 和风险策略必须版本化，评估结果必须能复现当时使用的版本。

### 3.8 评估系统

表：`eval_datasets`、`eval_cases`、`eval_runs`、`eval_case_results`、`eval_metric_results`。

目标：评估结果必须关联真实 `agent_run_id`，便于从指标追溯到失败链路。

### 3.9 审计、事件、后台任务

表：`audit_logs`、`outbox_events`、`background_jobs`。

目标：状态变更、审批、工具调用、数据导入和异步任务可追踪、可重试、可审计。

## 4. 索引规划

- `tickets`：`unique(tenant_id, ticket_no)`、`index(tenant_id, status, created_at)`、`index(tenant_id, category_code, created_at)`、`index(tenant_id, risk_level, created_at)`。
- `agent_runs`：`index(tenant_id, ticket_id, created_at)`、`index(tenant_id, status, created_at)`。
- `agent_run_steps`：`index(tenant_id, agent_run_id, step_order)`、`index(tenant_id, step_type, status)`。
- `knowledge_chunks`：`index(tenant_id, document_version_id, chunk_index)`。
- `chunk_embeddings`：`index(chunk_id)`、vector index on `embedding_vector`。
- `tool_calls`：`index(tenant_id, agent_run_id, created_at)`、`index(tenant_id, mcp_tool_id, status)`。
- `approval_requests`：`index(tenant_id, status, created_at)`、`index(tenant_id, ticket_id, created_at)`。
- `audit_logs`：`index(tenant_id, resource_type, resource_id, created_at)`、`index(tenant_id, actor_user_id, created_at)`。

## 5. 迁移策略

- 使用 Alembic。
- 已上线迁移不得修改，只能新增迁移。
- 新增 NOT NULL 字段必须分三步：先 nullable、回填、再改 NOT NULL。
- 删除字段必须走灰度：新字段、双写、切读、观察、删除。
- 回填必须幂等、分批、可重跑。
- 高风险 DDL 必须有回滚或前向恢复方案。

## 6. 第一批落地顺序

1. 租户、用户、角色、权限。
2. 工单、消息、状态事件。
3. Agent graph、run、step、model invocation。
4. 知识库 document、version、chunk、embedding。
5. MCP server、tool、tool call。
6. 审批请求、审批决策、执行记录。
7. Prompt、风险策略。
8. 评估数据集和结果。
9. 审计、outbox、background job。
