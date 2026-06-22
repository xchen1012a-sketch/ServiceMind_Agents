# 上下文惰性维护

目标：控制长期运行后的上下文膨胀，同时保证规则、计划和验收证据不丢失。

## 1. 惰性触发

日常启动只检查 `business/quick-ref.md` 的 `maintenanceDue` 一行。日期未到且没有硬性超限时，不读取本文件、不扫描其它文档；日期到期后才加载本文件并运行 `scripts/maintain-context.ps1`。

默认周期按项目规模动态计算：tiny/small 为 30 天，medium 为 14 天，large/enterprise 为 7 天。

## 2. 稳定性模式

默认 `autoApply: safe-only`：

- 到期时 AI 自动执行 dry-run；若结果只有明确 completed 的安全归档动作且无冲突，则自动执行 `-Apply`，不重复询问。
- 出现 `COMPACT_REQUIRED`、路径冲突、状态不明或需要语义拆分时，只报告并制定可回滚计划，不自动改写内容。
- 自动动作只包括归档明确标记为 `completed`、且不再被当前计划引用的 Session、Handoff 和阶段文件。
- `active`、`blocked`、abandoned、当前阶段、业务规则、冲突记录、验收证据和源码禁止自动删除。
- 所有自动移动必须进入同类目录下的 `archive/YYYY-MM/`，保留原文件名和 Git 可回滚路径。
- 默认命令只做 dry-run；`-Apply` 才执行安全归档并更新下一次日期。

## 3. 检查顺序

先检查行数、状态和修改时间，不先读取全文：

1. `quick-ref.md`：40 行。
2. `docs/plans/current.md`：80 行。
3. 单个文件需要读取超过 250 行时，先搜索符号、标题或关键词，再分段读取。
4. `business-rules.md`、`project-map.md` 按项目规模使用动态预算；超限只报告 `COMPACT_REQUIRED`。

## 4. 语义压缩

业务规则、项目地图和当前计划禁止机械截断。超限时由 AI：

1. 先复制原文件到同目录 `archive/snapshots/`，形成可回滚快照。
2. 按业务域或模块拆分文件，主文件只保留索引、关键不变量和当前入口。
3. 校验链接、冲突标记、当前计划、验收标准和来源标记仍完整。
4. 真实验证通过后才能更新 `maintenanceDue`。

不得用“总结”替代业务事实，不得删除低频但仍有效的规则。

## 5. 执行

```powershell
# 预览
.\.ai-spec\scripts\maintain-context.ps1

# 只应用 safe-only 动作
.\.ai-spec\scripts\maintain-context.ps1 -Apply
```

路由标记：`workflows/context-maintenance.md`
