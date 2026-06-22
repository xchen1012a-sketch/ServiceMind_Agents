# 模块契约：ServiceMind Agents

## 总体依赖方向

```text
apps/web -> apps/api -> application services -> domain services -> repositories -> database
                                      |
                                      -> agent runtime -> MCP tools / model providers / RAG
```

## 模块边界

### ticket

- 职责：工单、消息、状态事件、工单工作台。
- 禁止：直接调用模型、MCP 工具或向量数据库。

### agent

- 职责：Agent graph、run、step、模型调用、运行时抽象。
- 禁止：绕过 approval 直接执行高风险业务动作。

### knowledge

- 职责：知识空间、文档、版本、chunk、embedding、检索命中。
- 禁止：直接修改工单状态。

### mcp_tools

- 职责：MCP server/tool 注册、tool call、工具输入输出 schema。
- 禁止：把工具权限判断放到前端。

### approval

- 职责：高风险动作审批、决策、审批后执行记录。
- 禁止：审批通过和执行成功混为一个状态。

### evaluation

- 职责：评估数据集、样本、运行、指标、失败样本分析。
- 禁止：脱离真实 `agent_run_id` 记录孤立指标。

### audit

- 职责：审计日志、outbox 事件、后台任务。
- 禁止：保存密钥、Token、完整敏感请求体。

## 新增模块规则

- 必须说明不能复用现有模块的原因。
- 必须定义数据所有权、入口 API、依赖方向和回归范围。
- 不能把入口层逻辑、数据访问、外部接入和核心业务混写在同一文件。
