# Agent、Tool、Skill

## Agent

Agent 是 runtime loop 中负责生成下一步 decision 的组件。它不能绕过 runtime 直接写业务文件。

## Tool

tool 是只读能力，例如读取 case、partition 或 statistics。tool 是否可用由 `RuntimeRunRequest.allowed_tools` 决定。

## Skill

skill 是有明确输入 schema 的能力调用，可能产生副作用。skill 是否可用由 `RuntimeRunRequest.allowed_skills` 决定，runtime 负责校验和审计。

## Knowledge 中的约束

Knowledge 的治理阶段原则上使用只读分析能力：

```text
statistics / case / schema
  -> governance decision
  -> projection plan
  -> execution mutation
```

LLM 或 runtime skill 不直接修改 Knowledge 文件。最终修改只能由 `KnowledgeMutationExecutor` 在 Git transaction 中执行。
