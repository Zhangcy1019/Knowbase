# Knowbase 总览

Knowbase 是一个以 `case` 为事实源、以 `partition` 为隔离边界的知识库系统。

## 核心对象

| 对象 | 作用 |
| --- | --- |
| `Partition` | 知识、统计、Git、任务和治理边界 |
| `KnowbaseCaseDocument` | 不可替代的原始事实及其结构化表示 |
| `PartitionFacetSchema` | 分区级正式 facet 结构 |
| `PartitionSemanticIndex` | 分区级开放语义统计和索引 |
| `KnowbaseEvent` / `EventRecord` | 记录已发生的 case 变化 |
| `BacklogBatch` | 一批待交给 Knowledge 的事件 |
| `RuntimeRunRequest` | 一次受控 agent 执行请求 |
| `KnowledgeDecisionRecord` | 一次 Knowledge 治理结论的审计记录 |

## 三层边界

```text
Product    -> ingest / query
Backlog    -> event backlog / batch / partition task queue
Knowledge  -> statistics / governance / projection / execution
Runtime    -> loop / tool / skill / trace
```

`application` 负责组装这些模块；`domain` 负责资源和生命周期；`infrastructure` 负责本地存储、Git、锁和 AI 适配。

## 核心原则

- case 原文是事实源，不由 Knowledge 改写。
- semantic profile 是开放语义表示；facet 是正式结构视图。
- query 进入独立统计，不直接改变 facet schema。
- LLM 只参与分析和提出方案，不能直接修改 Knowledge 文件。
- 文件 mutation 必须经过 projection、execution 和分区 Git transaction。
- 同一 partition 的文件/Git/statistics mutation 串行执行。

## 当前状态

Knowledge 的 `GovernanceService` 已接入 preparation、proposal、runtime 和 validation 主链路。
当前治理约束只启用 `fit_metrics`；没有有效 proposal 时不会调用 Runtime，也不会产生 mutation。
完整策略见 [`knowledge.md`](knowledge.md) 和 [`governance.md`](governance.md)。
