# Agent 设计

本文档回答一个问题：

`当前 Knowbase 里的 agent 应该放在哪里，负责什么？`

## 结论

当前系统里主要有两类 agent：

1. `product agent`
2. `runtime agent`

不再单独强调一个顶层 `governance agent` 模块。

## Product Agent

`product agent` 服务在线 query。

典型职责：

- query 理解
- 检索结果总结
- 回答生成

它不负责：

- 写 case
- 修改 partition
- 触发后台批处理

当前代码落点主要在：

- `internal/agents/product/`

## Runtime Agent

`runtime agent` 是 runtime harness 内部的决策器。

它的职责是：

- 接收每轮 `RuntimeTurnInput`
- 基于当前 memory / context / budgets 做决策
- 产出 `RuntimeDecision`
- 决定下一步执行哪些 tool / skill

它不直接：

- 写数据库
- 绕过 runtime 执行副作用
- 持久化 run 审计

这些都由 runtime 框架负责。

## Agent 与 Runtime 的边界

### runtime 负责

- session 建立
- memory 维护
- step / artifact 持久化
- tool / skill 调用
- termination 判断

### agent 负责

- 当前回合语义判断
- 生成 decision
- 选择 action

### skill 负责

- 真正的副作用执行

## Agent 与 Tool / Skill 的边界

### Tool

- 只读
- 给 agent 提供观察能力

### Skill

- 可写
- 由 runtime 调用

## 当前实现状态

当前 runtime 默认使用确定性 agent：

- `DeterministicRuntimeAgent`

它会根据 `RuntimeRunRequest` 的显式 action hints 或请求上下文，生成可执行 decision。

后续如果接入 LLM loop agent，也应该继续挂在 `runtime` 内部，而不是绕开 runtime 单独执行。

## 一句话总结

当前 agent 的正确定位是：

`product agent 服务 query，runtime agent 服务受控执行框架。`
