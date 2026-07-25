# Knowledge 语义统计与索引设计（v1）

本文档定义 Knowledge v1 的统计与索引基础：`PartitionSemanticIndex`。

目标：让分区 facet 收敛建立在可量化、可查询、可回溯的统计层之上，而不是直接依赖单轮 LLM 输出。

补充边界：

- case 侧的 `facet / semantic_profile` 在 `domain/case` 输入阶段完成
- knowledge 只接收这些结构化结果进入统计层
- query 也按类似模式进入统计层
- query 当前只做统计，不参与 facet/schema 自动决策

## 1. 为什么需要语义统计与索引

facet key 的变更属于高风险结构性修改，不能直接由某一轮模型判断驱动。

在 v1 中，partition 需要先维护一份稳定的语义统计和反向索引，用于回答：

- 哪些 key 经常出现
- 哪些 key 持续出现
- 哪些 key 的 value 过散
- 某个候选 key 升为 facet 后能解释多少 case
- 某个已有 facet key 降级后会损失多少覆盖
- 某个 key/value 实际影响哪些 case

## 2. 核心对象

## 2.1 CaseSemanticCandidate

`CaseSemanticCandidate` 是观测层对象，不是真相层对象。

建议字段：

- `case_id`
- `partition`
- `key`
- `canonical_key`
- `value`
- `canonical_value`
- `confidence`
- `evidence_spans`
- `source_excerpt_hash`
- `extraction_version`
- `observed_at`
- `batch_id`

约束：

- 允许多个候选同时存在
- 允许低置信候选进入统计，但后续判定时要降权
- 必须保留 evidence，避免无支撑归纳

## 2.2 QuerySemanticObservation

`QuerySemanticObservation` 是 query 消费侧统计对象。

建议字段：

- `query_id`
- `partition`
- `facts`
- `semantic_profile`
- `issued_at`
- `source_kind`

约束：

- 仅进入统计层
- 不直接驱动 facet/schema 演化
- 后续若用于 query 优化，应单独建立决策链路

## 2.3 PartitionSemanticIndex

`StatisticsSnapshot` 是 partition 级当前统计文件，对应
`statistics/{partition}/snapshot.json`。它只表示当前工作状态，历史版本由
Knowledge patch 的 Git commit 管理。

建议字段：

- `partition`
- `generated_at`
- `source_revision`
- `source_case_count`
- `batch_cursor`
- `key_stats`
- `key_value_stats`
- `key_alias_clusters`
- `case_support_index`
- `value_support_index`
- `temporal_support_windows`
- `query_key_stats`
- `query_value_stats`
- `query_support_index`

## 3. 最小统计集合

v1 建议先维护四组统计。

### 3.1 key 覆盖统计

按 `canonical_key` 聚合：

- `case_support_count`
- `batch_support_count`
- `window_support_ratio`

用途：

- 判断这个 key 是否广泛存在
- 判断这个 key 是否只是单批次噪声

### 3.2 key 稳定性统计

按 `canonical_key` 聚合：

- `consecutive_support_batches`
- `support_streak_broken_count`
- `first_seen_batch`
- `last_seen_batch`

用途：

- 判断是否满足“稳定化”而不是短期爆发
- 支撑冻结与冷却策略

### 3.3 value 分布统计

按 `canonical_key -> canonical_value` 聚合：

- `case_support_count`
- `confidence_mean`

按 `canonical_key` 额外计算：

- `value_entropy`
- `distinct_value_count`

用途：

- 判断某个 key 是否适合作为 facet key
- 判断 value 是否适合后续进入闭集或同义归并

### 3.4 反向索引

必须维护：

- `canonical_key -> [case_ids]`
- `canonical_key -> canonical_value -> [case_ids]`
- `canonical_key -> [raw_key_aliases]`

用途：

- 快速找到 patch 影响范围
- 支撑覆盖收益和迁移成本计算

### 3.5 query 统计

按 `partition -> query semantic profile` 聚合：

- `query_key_support_count`
- `query_value_support_count`
- `query_window_support_ratio`
- `query_support_index`

用途：

- 记录消费侧长期关注维度
- 为未来 query 优化提供基础数据
- 当前不进入 facet/schema 自动收敛判定

## 4. v1 关键指标定义

## 4.1 case_support_count

含义：

- 至少被多少个不同 case 支持

定义：

- 同一个 case 对同一 `canonical_key` 只计一次

## 4.2 consecutive_support_batches

含义：

- 在最近连续多少个 batch 中，该 key 都有支持

用途：

- 判断稳定性

## 4.3 value_entropy

含义：

- 某个 key 的 value 分布是否过散

用途：

- 高频但高熵的 key 不适合作为稳定 facet key

## 4.4 confidence_mean

含义：

- 候选提取的平均置信度

用途：

- 避免低质量抽取直接进入 schema

## 4.5 coverage_gain

含义：

- 若某个候选 key 升为 facet key，能额外解释多少 case

依赖：

- 当前 facet schema
- 当前 case semantic candidates
- case support index

## 5. canonicalization 规则

v1 需要至少支持：

- `raw key -> canonical key`
- `raw value -> canonical value`

建议采用：

1. 规则词典优先
2. LLM 提案作为补充
3. 低置信合并不自动进入正式 alias cluster

典型例子：

- `repo`
- `repo_name`
- `repository`

都可映射为 `repository`

## 6. 持久化建议

既然当前系统以本地文件为主，建议：

- 每个 partition 一份最新聚合索引文件
- 每个 batch 一份增量统计产物
- 保留历史版本，方便回溯

建议文件形态：

```text
workspace/knowledge/
  partitions/{partition}/
    semantic_index.json
    semantic_index_history/
      {batch_id}.json
```

## 7. 与后续模块的关系

`PartitionSemanticIndex` 是以下模块的输入：

- `facet key convergence`
- `fit metric evaluation`
- `circuit breaker`
- `KnowledgePatch` 影响范围分析

query 统计当前只作为索引内容存在，不接入上述自动决策链。

没有这层，facet 收敛只能基于即时启发，无法稳定。

## 8. v1 结论

Knowledge v1 的统计基础不是简单计数，而是：

- case / query 统计输入
- 统计聚合
- 反向索引
- 时间稳定性记录
- alias cluster 归并

这一层必须先建稳，facet 收敛算法才能真正可量化。
