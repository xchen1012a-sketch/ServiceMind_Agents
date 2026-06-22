# ServiceMind Agents · AI 协作入口

日常任务先读取 `.ai-spec/business/quick-ref.md`。只有 quick-ref 不是 `GENERATED`、或本次是接入、初始化、完整审计时，才读取 `.ai-spec/AI-START.md`。

默认使用简体中文。不得因为代码、依赖、日志或文档为英文而自行切换语言。

项目画像读取 `.ai-spec/ai-spec.yaml`。项目计划入口为 `docs/plans/current.md`，总计划为 `docs/plans/project-plan.md`。

实施前必须遵守：

- 复杂任务先检查 `docs/plans/current.md`。
- 数据库变更先检查 `docs/plans/database-design-plan.md` 和 `.ai-spec/core/data-migration-standard.md`。
- Agent 运行时变更先检查 `docs/plans/agent-runtime-decision.md`。
- 模块新增或跨模块调用先检查 `docs/architecture/modules.md`。
- 核心链路变更先检查 `docs/quality/regression-checklist.md`。

禁止把密钥、Token、真实客户隐私数据写入仓库。
