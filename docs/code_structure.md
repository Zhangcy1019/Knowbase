# 代码结构

## 顶层目录

```text
internal/
  api/                         HTTP routes and schemas
  application/                 dependency assembly
  backlog/
    events/                    event persistence and batch assembly
    tasks/                     partition task queue
  domain/
    case/                      case lifecycle and extraction
    event/                     event publishing
    partition/                 partition lifecycle and profiles
    run/                       run persistence domain
  infrastructure/
    ai/                        LLM and embedding adapters
    coordination/              mutation lock
    persistence/               local / Elasticsearch stores
    version_control/           Git adapter
  knowledge/
    batch/                     working set and preparation inputs
    statistics/                case/query statistics
    facet_governance/          schema governance boundary
    projection/                case facet projection
    execution/                 mutation plan application
    decision/                  decision audit and review lock
    workflow/                  Knowledge top-level orchestration
    capability/                Knowledge tool/skill registration
  models/                      cross-module models
  ports/                       cross-module protocols
  product/
    ingest/                    case input use case
    query/                     query use case
  runtime/                     generic agent harness
  versioning/                  partition Git policy and transactions
```

## 依赖方向

```text
api -> application -> product / backlog / knowledge / runtime
product -> domain / ports / models
backlog -> ports / models
knowledge -> ports / models / domain reads
runtime -> ports / models / capabilities
domain -> models
infrastructure -> ports / models
```

`application` 只组装对象，不实现业务规则。`workflow` 负责串联 Knowledge 模块，不拥有统计、治理或文件写入算法。

## 重要边界

- `backlog/events` 是已发生事件；`backlog/tasks` 是待执行命令，两者不共用状态模型。
- `knowledge/projection` 计算“应该改什么”；`knowledge/execution` 执行已经确认的 mutation plan。
- `runtime` 是通用执行底座；Knowledge 通过受限 request 注入目标和能力。
- `versioning` 管理分区 Git；Knowledge 不直接调用 Git subprocess。
