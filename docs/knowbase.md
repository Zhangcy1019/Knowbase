# Knowbase 总体设计

`Knowbase` 是一个 case-centric 的知识库系统。

当前方案的核心判断很简单：

- `case` 是事实源
- `semantic_profile` 是开放语义层
- `PartitionSemanticIndex` 是统计认知层
- `PartitionFacetSchema` 是少量正式结构层
- `backlog` 负责事件积压和批处理触发
- `runtime` 负责 agent harness 执行与审计

## 核心对象

- `Partition`
- `PartitionFacetSchema`
- `PartitionSemanticIndex`
- `KnowbaseCaseDocument`
- `KnowbaseEvent`
- `EventRecord`
- `BacklogBatch`
- `AgentRun`
- `RunStep`
- `RunArtifact`

可以把它们分成四层：

### 资源层

- `Partition`
- `PartitionFacetSchema`
- `PartitionSemanticIndex`
- `Case`

### 事件层

- `KnowbaseEvent`
- `EventRecord`
- `BacklogBatch`

### 运行层

- `AgentRun`
- `RunStep`
- `RunArtifact`

### 能力层

- `Tool`
- `Skill`

## 总体分层

```text
Product Layer
  ingest / query

Backlog Layer
  event queue / batch / dispatch

Runtime Layer
  agent harness / loop / audit

Capability Layer
  tools(read) / skills(write)

State Layer
  partition / schema / semantic index / case / event / run
```

### Product Layer

面向用户主流程：

- `ingest`
- `query`

它追求低延迟和确定性，不直接暴露 backlog 和 runtime 内部对象。

### Backlog Layer

面向后台事件治理：

- 接收事件
- 维护队列
- 组装 batch
- 生成 runtime request

它不负责真正执行任务，也不负责 agent loop。

### Runtime Layer

面向一次受控 run：

- 接收 `RuntimeRunRequest`
- 维护 session / memory / loop state
- 调用 agent 做逐轮决策
- 调用 tool / skill 执行动作
- 沉淀 run / step / artifact

### Capability Layer

- `tools` 只读观察
- `skills` 有副作用执行

### State Layer

长期状态都落在这里，而不是散落在临时流程中。

## 两条主链路

### 在线产品链路

```text
request
  -> ingest / query
  -> result
```

### 后台治理链路

```text
case change
  -> event
  -> backlog
  -> batch
  -> runtime request
  -> runtime run
  -> audited result
```

## 当前最重要的边界

### ingest / query

负责稳定主流程，不承担后台重治理。

### backlog

负责把事件整理成一次可执行请求。

### runtime

负责围绕一个目标，在受控 loop 中执行 tool / skill，并沉淀审计结果。

### domain

负责资源和状态本身，不负责系统级总控流程。

## 一句话总结

当前 Knowbase 的主结构是：

`在线主流程保持确定性，后台通过 backlog -> runtime harness 渐进治理。`
