# 数据库 Schema：ServiceMind Agents

## 设计基线

- 数据库：PostgreSQL。
- 向量扩展：pgvector。
- ORM：SQLAlchemy 2.0 declarative。
- 迁移：Alembic。
- 主键：`UUID`。
- 时间：`TIMESTAMPTZ`，统一字段 `created_at`、`updated_at`，业务主表加 `deleted_at`。
- 多租户：核心业务表必须包含 `tenant_id UUID NOT NULL`。
- 命名：全库 `snake_case`，外键字段使用完整语义，例如 `created_by_user_id`、`approved_by_user_id`。
- JSON：仅用于 payload、schema、metadata、快照；可筛选、排序、统计的字段必须原子化。
- 金额：`NUMERIC(18, 4)`。
- 状态：`status TEXT NOT NULL`，状态枚举由应用层和文档约束。

## 首批表清单

### 租户与权限

#### tenants

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK | 租户 ID |
| name | TEXT | NOT NULL | 租户名称 |
| slug | TEXT | NOT NULL, UNIQUE | 租户唯一标识 |
| status | TEXT | NOT NULL | active / suspended / archived |
| created_at | TIMESTAMPTZ | NOT NULL | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新时间 |
| deleted_at | TIMESTAMPTZ | NULL | 软删除时间 |

#### users

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK | 用户 ID |
| tenant_id | UUID | FK tenants.id, NOT NULL | 租户 |
| email | TEXT | NOT NULL | 登录邮箱 |
| display_name | TEXT | NOT NULL | 显示名 |
| password_hash | TEXT | NOT NULL | 密码哈希 |
| status | TEXT | NOT NULL | active / disabled |
| last_login_at | TIMESTAMPTZ | NULL | 最近登录 |
| created_at | TIMESTAMPTZ | NOT NULL | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新时间 |
| deleted_at | TIMESTAMPTZ | NULL | 软删除时间 |

唯一约束：`uq_users_tenant_email(tenant_id, email)`。

#### roles / permissions / role_permissions / user_roles

- `roles`：`id`、`tenant_id`、`code`、`name`、`description`、`status`、时间字段。
- `permissions`：`id`、`code`、`name`、`description`、`resource_type`、`action`、时间字段。
- `role_permissions`：`id`、`tenant_id`、`role_id`、`permission_id`、`created_at`。
- `user_roles`：`id`、`tenant_id`、`user_id`、`role_id`、`assigned_by_user_id`、`created_at`。

唯一约束：

- `uq_roles_tenant_code(tenant_id, code)`
- `uq_permissions_code(code)`
- `uq_role_permissions(role_id, permission_id)`
- `uq_user_roles(user_id, role_id)`

### 工单

#### tickets

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK | 工单 ID |
| tenant_id | UUID | FK tenants.id, NOT NULL | 租户 |
| ticket_no | TEXT | NOT NULL | 租户内工单编号 |
| title | TEXT | NOT NULL | 标题 |
| description_text | TEXT | NOT NULL | 原始描述 |
| category_code | TEXT | NOT NULL | 分类 |
| priority | TEXT | NOT NULL | low / medium / high / urgent |
| risk_level | TEXT | NOT NULL | low / medium / high / critical |
| status | TEXT | NOT NULL | 当前状态 |
| source_channel | TEXT | NOT NULL | web / api / email / import |
| requester_name | TEXT | NULL | 请求人名称 |
| requester_contact | TEXT | NULL | 请求人联系方式 |
| assigned_user_id | UUID | FK users.id, NULL | 负责人 |
| created_by_user_id | UUID | FK users.id, NULL | 创建人 |
| created_at | TIMESTAMPTZ | NOT NULL | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新时间 |
| deleted_at | TIMESTAMPTZ | NULL | 软删除时间 |

唯一约束：`uq_tickets_tenant_ticket_no(tenant_id, ticket_no)`。

#### ticket_messages

- `id`、`tenant_id`、`ticket_id`、`sender_type`、`sender_user_id`、`message_text`、`message_format`、`created_at`。
- `sender_type`：user / requester / agent / system。
- `message_format`：plain / markdown / html。

#### ticket_status_events

- `id`、`tenant_id`、`ticket_id`、`from_status`、`to_status`、`reason_text`、`changed_by_type`、`changed_by_user_id`、`agent_run_id`、`created_at`。
- 状态历史独立保存，不把历史塞进 `tickets`。

### Agent 运行轨迹

#### agent_graph_versions

- `id`、`tenant_id`、`runtime_type`、`graph_name`、`graph_version`、`definition_hash`、`definition_json`、`is_active`、`created_at`。
- `runtime_type`：langgraph / deepagents / custom。
- 唯一约束：`uq_agent_graph_versions(tenant_id, graph_name, graph_version)`。

#### agent_runs

- `id`、`tenant_id`、`ticket_id`、`runtime_type`、`graph_version_id`、`status`、`started_at`、`finished_at`、`total_latency_ms`、`total_prompt_tokens`、`total_completion_tokens`、`total_cost_amount`、`error_code`、`error_message`、`created_at`。

#### agent_run_steps

- `id`、`tenant_id`、`agent_run_id`、`step_name`、`step_type`、`step_order`、`external_step_ref`、`status`、`input_payload`、`output_payload`、`latency_ms`、`prompt_tokens`、`completion_tokens`、`error_code`、`error_message`、`started_at`、`finished_at`、`created_at`。
- 唯一约束：`uq_agent_run_steps_order(agent_run_id, step_order)`。

#### model_invocations

- `id`、`tenant_id`、`agent_run_id`、`agent_run_step_id`、`provider_code`、`model_name`、`prompt_version_id`、`request_payload`、`response_payload`、`prompt_tokens`、`completion_tokens`、`latency_ms`、`cost_amount`、`status`、`created_at`。

### 知识库与 RAG

#### knowledge_spaces

- `id`、`tenant_id`、`name`、`description_text`、`visibility`、`status`、`created_by_user_id`、`created_at`、`updated_at`、`deleted_at`。

#### knowledge_documents

- `id`、`tenant_id`、`knowledge_space_id`、`title`、`source_type`、`source_uri`、`file_name`、`mime_type`、`status`、`current_version_id`、`created_by_user_id`、`created_at`、`updated_at`、`deleted_at`。

#### knowledge_document_versions

- `id`、`tenant_id`、`document_id`、`version_no`、`storage_uri`、`content_hash`、`parser_name`、`parser_version`、`parse_status`、`created_at`。
- 唯一约束：`uq_document_versions(document_id, version_no)`。

#### knowledge_chunks

- `id`、`tenant_id`、`document_version_id`、`chunk_index`、`chunk_text`、`token_count`、`heading_path`、`page_number`、`source_anchor`、`metadata_json`、`created_at`。
- 唯一约束：`uq_knowledge_chunks(document_version_id, chunk_index)`。

#### embedding_models / chunk_embeddings

- `embedding_models`：`id`、`provider_code`、`model_name`、`dimension`、`status`、`created_at`。
- `chunk_embeddings`：`id`、`tenant_id`、`chunk_id`、`embedding_model_id`、`embedding_vector vector`、`embedding_hash`、`created_at`。
- 唯一约束：`uq_chunk_embeddings(chunk_id, embedding_model_id)`。

#### rag_queries / rag_retrieval_hits

- `rag_queries`：`id`、`tenant_id`、`agent_run_id`、`agent_run_step_id`、`query_text`、`retrieval_params_json`、`created_at`。
- `rag_retrieval_hits`：`id`、`tenant_id`、`rag_query_id`、`chunk_id`、`rank_no`、`similarity_score`、`rerank_score`、`used_in_answer`、`created_at`。

### MCP 工具与审批

#### mcp_servers / mcp_tools / tool_calls

- `mcp_servers`：`id`、`tenant_id`、`code`、`name`、`transport_type`、`endpoint_url`、`status`、`created_at`、`updated_at`。
- `mcp_tools`：`id`、`tenant_id`、`mcp_server_id`、`tool_name`、`display_name`、`description_text`、`input_schema_json`、`output_schema_json`、`risk_level`、`requires_approval`、`status`、`created_at`、`updated_at`。
- `tool_calls`：`id`、`tenant_id`、`agent_run_id`、`agent_run_step_id`、`mcp_server_id`、`mcp_tool_id`、`status`、`input_payload`、`output_payload`、`error_code`、`error_message`、`latency_ms`、`approval_request_id`、`created_at`。
- 高风险工具调用必须先生成 `approval_requests`，审批通过前不得执行写动作。

#### approval_requests / approval_decisions / approved_action_executions

- `approval_requests`：`id`、`tenant_id`、`ticket_id`、`agent_run_id`、`tool_call_id`、`action_type`、`risk_level`、`reason_text`、`proposed_payload`、`status`、`requested_by_type`、`requested_by_user_id`、`expires_at`、`created_at`、`updated_at`。
- `approval_decisions`：`id`、`tenant_id`、`approval_request_id`、`decision`、`decision_reason`、`decided_by_user_id`、`decided_at`、`created_at`。
- `approved_action_executions`：`id`、`tenant_id`、`approval_request_id`、`tool_call_id`、`execution_status`、`execution_payload`、`execution_result_payload`、`error_code`、`error_message`、`executed_at`、`created_at`。

### Prompt、评估与审计

- `prompt_templates`：Prompt 逻辑名和用途。
- `prompt_versions`：版本化内容、hash、状态和发布时间。
- `risk_policies` / `risk_policy_rules`：风险策略版本与规则。
- `eval_datasets` / `eval_cases` / `eval_runs` / `eval_case_results` / `eval_metric_results`：离线评估。
- `audit_logs`：关键操作审计，不保存密钥、Token 或完整敏感请求体。
- `outbox_events`：事务外发事件。
- `background_jobs`：后台任务、重试和失败原因。

## 关键索引

- `tickets`：`(tenant_id, status, created_at)`、`(tenant_id, category_code, created_at)`、`(tenant_id, risk_level, created_at)`。
- `agent_runs`：`(tenant_id, ticket_id, created_at)`、`(tenant_id, status, created_at)`。
- `agent_run_steps`：`(tenant_id, agent_run_id, step_order)`、`(tenant_id, step_type, status)`。
- `knowledge_chunks`：`(tenant_id, document_version_id, chunk_index)`。
- `chunk_embeddings`：`(chunk_id)`、`embedding_vector` ivfflat/hnsw 向量索引，按 pgvector 版本选择。
- `tool_calls`：`(tenant_id, agent_run_id, created_at)`、`(tenant_id, mcp_tool_id, status)`。
- `approval_requests`：`(tenant_id, status, created_at)`、`(tenant_id, ticket_id, created_at)`。
- `audit_logs`：`(tenant_id, resource_type, resource_id, created_at)`、`(tenant_id, actor_user_id, created_at)`。

## 迁移顺序

1. 启用扩展：`pgcrypto`、`vector`。
2. 租户、用户、角色、权限。
3. 工单、消息、状态事件。
4. Agent graph、run、step、model invocation。
5. 知识库、文档版本、chunk、embedding。
6. MCP server、tool、tool call。
7. 审批请求、审批决策、审批后执行。
8. Prompt、风险策略、评估。
9. 审计、outbox、background jobs。

## 迁移规范

- 已上线迁移不得修改，只能新增迁移。
- 新增 NOT NULL 字段先可空、回填、再约束。
- 删除字段或改字段类型必须走新字段、双写、切读、观察、清理。
- 数据回填必须幂等、分批、可重跑。
- 高风险 DDL 需要恢复策略或前向修复方案。
