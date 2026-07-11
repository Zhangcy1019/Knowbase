# 主流程

本文档描述当前 Knowbase 的真实主流程。

## 总体主链路

```text
在线产品链路:
  request -> ingest/query -> result

后台治理链路:
  event -> backlog -> runtime -> audited result
```

## 1. 在线写入主流程

当前写入链路的目标是：

- case 尽快入库
- case 立刻可搜索
- case 拥有基础语义表示
- 不阻塞在后台治理上

### case create / update

```text
create or update case
  -> validate request
  -> load partition
  -> load facet schema
  -> load semantic index
  -> build case draft
  -> generate summary_text
  -> generate semantic_profile
  -> project facets
  -> build retrieval representation
  -> persist case
  -> emit event
  -> return success
```

同步阶段应完成：

- `summary_text`
- `semantic_profile`
- `facets`
- 搜索表示 / 向量
- case 持久化

同步阶段不应完成：

- semantic index 全量刷新
- backlog drain
- 批量 rebuild

## 2. Query 主流程

```text
query request
  -> normalize query
  -> parse query semantic profile
  -> consult partition semantic index
  -> align likely keys / values / aliases
  -> retrieval
  -> rerank
  -> answer synthesis
  -> return result
```

semantic index 在 query 中提供：

- key alignment
- value alignment
- alias resolution
- retrieval expansion

## 3. 事件与 backlog 主流程

case 写入成功后，会生成 `KnowbaseEvent`。

```text
case change
  -> KnowbaseEvent
  -> EventRecord
  -> backlog
```

这里的意义是：

- 解耦在线写入和后台治理
- 提供统一审计入口
- 支持手动或定时 drain

## 4. Backlog Drain 主流程

```text
select ready events
  -> assemble BacklogBatch
  -> build BatchWorkingSet
  -> build preparation
  -> build RuntimeRunRequest
  -> runtime.run_request
```

当前 `backlog` 的责任到此为止。

它只负责：

- 队列维护
- batch 组装
- preparation summary
- action hint 下发

它不负责 loop 执行。

## 5. Runtime 主流程

当前 runtime 已经是 agent harness，而不是旧的三段式 execution plan。

```text
runtime request
  -> create run
  -> create runtime session
  -> initialize memory
  -> loop:
       build turn input
       agent decide
       evaluate termination
       execute actions
       update memory / loop state
  -> finalize run
  -> persist run summary / steps / artifacts
```

### runtime request 输入

- `objective`
- `prompt`
- `context`
- `allowed_tools`
- `allowed_skills`
- `max_steps`
- `max_tool_calls`
- `max_skill_calls`

### runtime loop 输出

- `RuntimeRunResult`
- `AgentRun`
- `RunStep`
- `RunArtifact`
- `ToolResult`
- `SkillResult`

## 6. 从 backlog 到 runtime 的闭环

以一次 backlog drain 为例：

```text
event backlog
  -> assemble batch
  -> build working set
  -> build preparation
  -> compile runtime request
  -> runtime loop execution
  -> run audited
  -> mark batch completed or failed
```

## 7. 当前系统最重要的边界

### 在线写入边界

- 让 case 可写、可搜

### backlog 边界

- 让事件变成一次结构化 runtime request

### runtime 边界

- 让受控 agent loop 完成一次 run

### 审计边界

- 所有后台执行都必须有 run / step / artifact

## 一句话总结

当前主流程不是“每次写入都立刻重治理”，而是：

`在线快速入库，后台通过 event -> backlog -> runtime 渐进处理。`
