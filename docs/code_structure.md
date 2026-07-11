# 代码结构

本文档说明当前 Knowbase 推荐收敛的代码结构。

## 顶层结构

```text
knowbase/
  main.py
  bootstrap.py
  config/
  docs/
  internal/
  tests/
  ui/
```

- `main.py`
  统一启动入口，负责加载配置、初始化日志、启动服务。
- `bootstrap.py`
  应用装配入口，负责创建 FastAPI app、注册路由、挂载 UI。
- `internal/`
  所有后端内部实现。

## internal 分层

```text
internal/
  api/
  agents/
    product/
  application/
  backlog/
    planning/
  connectors/
    es/
  domain/
    case/
    event/
    partition/
    run/
  llm/
  models/
  ports/
  product/
    ingest/
    query/
  runtime/
  skills/
    case/
    partition/
  tools/
    case/
    partition/
  utils/
```

## 模块职责

### `api`

HTTP 适配层。

- route 注册
- request / response schema
- route 级依赖装配

不承载核心业务编排。

### `application`

应用装配层。

- 构建 container
- 装配 providers / registries / modules
- 暴露启动所需的 facade

### `product`

在线主流程层。

- `product/ingest`
- `product/query`

负责用户直接感知的用例编排。

### `backlog`

后台事件编排层。

- backlog queue
- batch working set
- preparation planner
- runtime request dispatch
- worker drain

它负责把事件变成可执行请求，不负责执行 loop。

### `runtime`

agent harness 层。

- request contract
- session / loop state
- memory
- agent decision
- action execution
- termination
- run result assembly

它负责真正执行一次 run。

### `domain`

领域层。

- `case`
- `partition`
- `event`
- `run`

负责核心资源、领域服务、仓储。

### `skills`

有副作用的可执行能力。

例如：

- `case.rebuild_case`
- `case.refresh_case_facets`
- `partition.refresh_selected_cases_facets`

### `tools`

只读观察能力。

例如：

- `case.get`
- `case.list`
- `partition.get`

### `models`

跨层共享的数据结构和持久化模型。

### `ports`

跨模块依赖接口。

所有顶层模块之间的稳定调用关系，尽量通过 `ports` 收口。

## 核心接口

### backlog -> runtime

`BacklogDispatchPort`

- `build_runtime_request(batch: BacklogBatch) -> RuntimeRunRequest`

`RuntimeHarnessPort`

- `run_request(request: RuntimeRunRequest) -> RuntimeRunResult`

### product -> domain

`PartitionAccessPort`

- `get_partition(partition_name: str) -> PartitionDocument | None`
- `get_facet_schema(partition_name: str) -> PartitionFacetSchema | None`
- `get_semantic_index(partition_name: str) -> PartitionSemanticIndex | None`

`CaseStorePort`

- `save(document: KnowbaseCaseDocument) -> KnowbaseCaseDocument`

`CaseReadPort`

- `get(case_id: str) -> KnowbaseCaseDocument | None`
- `list_by_partition(partition_name: str) -> list[KnowbaseCaseDocument]`

### runtime -> capabilities

`SkillExecutionPort`

- `resolve_spec(skill_id: str) -> SkillSpec | None`
- `execute(invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult`

运行时内部也会直接使用 `ToolRuntime` 执行 tool。

## 当前推荐依赖方向

```text
api -> application / ports
application -> product / backlog / runtime / domain / skills / tools
product -> domain / ports / models
backlog -> ports / models
runtime -> ports / models / tools / skills / domain.run
domain -> models / connectors
skills -> ports / models
tools -> ports / models
```

## 一句话总结

当前结构的重点不是目录多，而是边界清楚：

`product 做在线主流程，backlog 做事件批处理，runtime 做 agent harness。`
