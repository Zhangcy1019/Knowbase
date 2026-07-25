# Knowledge Query 统计设计（v1）

本文档定义 query 如何进入 `knowledge` 统计层。

目标很克制：

- 让 query 和 case 一样，进入统一的分区统计体系
- 只做统计沉淀
- 不直接影响知识结构

## 1. 核心原则

1. query 不进入 facet/schema 自动决策
2. query 只进入统计层
3. query 是否用于后续优化，是下一阶段问题

## 2. 主链路位置

query 到来后，除了正常检索主链路外，可并行执行一条轻量统计链：

1. 生成 query 的 `facts`
2. 生成 query 的 `semantic_profile`
3. 将结果写入 knowledge 统计模块
4. 结束

到此为止，不触发：

- facet key promotion
- facet value convergence
- patch 生成
- runtime knowledge maintenance task

## 3. 为什么现在先只做统计

这样做有三个好处：

- 保留未来利用 query 信号的空间
- 不把消费侧噪声直接引入知识主轴
- 不显著增加当前主闭环复杂度

## 4. 建议统计内容

- `query_key_support_count`
- `query_value_support_count`
- `query_support_index`
- `query_temporal_windows`
- `query_alias_observations`

## 5. 与 case 统计的关系

- case 统计是生产侧真相统计
- query 统计是消费侧需求统计
- 两者都进入 knowledge 统计层
- 但只有 case 统计参与 v1 的 facet/schema 收敛

## 6. 对代码结构的影响

建议由 `internal/knowledge/statistics/` 统一接收两类输入：

- `case_statistics_ingestor`
- `query_statistics_ingestor`
- `semantic_observation_normalizer`

其中：

- case ingestion 接收 `domain/case` 已经产出的结构化字段
- query ingestion 接收 query 侧并行计算产出的结构化字段
- 两者都不在 ingestion 内重新做原文抽取
