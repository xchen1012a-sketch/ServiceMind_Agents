# 多 AI 会话协调

触发条件：用户要求多个 AI 并行、当前任务会修改文件，或检测到 `.ai-spec/sessions/` 已存在。

注意：工具不会自动执行锁。Claude Code、Codex、Cursor 等都必须按本文件主动读写 session 文件；没有读写就不存在并行保护。

文件路径：`.ai-spec/sessions/{ai-tool}-{timestamp}.md`

## 启动协议

1. 读取 `.ai-spec/sessions/` 下所有 `active` 状态文件。
2. 声明本次将修改的文件路径，写入自己的 session 文件。
3. 与已有 active session 逐文件比对。
4. 命中同名文件冲突时停止，并向用户报告。
5. 无冲突时继续执行任务。
6. 完成后将 session 标记为 `completed`，或删除自己的 session 文件。

## Session 文件格式

```markdown
# Active Session
- ai: Codex
- branch: feature/example
- started: 2026-06-19T15:30:00+08:00
- status: active
- files:
  - src/example.ts
- note: 修改示例模块
```

## 冲突报告

表格最多 3 列；详细说明放在表格下方。

| 冲突文件 | 占用者 | 状态 |
| --- | --- | --- |
| src/example.ts | Claude Code | active |

建议：

1. 等待对方完成。
2. 让用户确认是否释放 abandoned session。
3. 调整本次任务范围，避开冲突文件。

## 安全规则

- 同名文件冲突是硬阻止。
- 用户可手动删除 abandoned session，但必须确认对方已停止。
- `.ai-spec/sessions/` 不入 git。
- 分支切换或 stash/pop 后必须重新检查。

路由标记：`workflows/session-coordination.md`
