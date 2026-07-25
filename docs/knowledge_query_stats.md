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
- `query_temporal_windows`
- `query_alias_observations`

当前实现只保留 query 的计数、key/value 频次，不维护 supporting-case index。

## 5. 统计快照与 Git

case 与 query 使用不同的快照模型和存储路径：

```text
knowledge_statistics/{partition}/snapshot.json
runtime_statistics/query/{partition}/snapshot.json
```

`CaseStatisticsSnapshot` 由 Knowledge 使用并纳入 Git；`QueryStatisticsSnapshot` 只属于运行期 telemetry，由 `.gitignore` 排除，不参与 facet/schema 收敛。

Knowledge mutation 开始时记录 `base_revision`。case 统计快照的 `source_revision` 表示：

> 该快照基于哪个 Git revision 开始计算。

它不是包含该快照的最终 commit hash，避免 commit hash 自引用。

## 6. 当前幂等边界

statistics snapshot 不保存 `applied_observation_ids`，因此：

- `append` 是非幂等的，重复调用会重复计数
- case update 必须使用显式 `replace(old, new)`
- case delete 必须使用显式 `remove(old)`
- case 生命周期服务负责避免重复 mutation
- query 统计按请求计数，不做幂等去重

当前不引入 Redis。未来引入 Redis 后，幂等状态应放在 case/application mutation 层，而不是 snapshot 内部。

建议使用简单的 mutation 状态：

```text
无记录       -> 执行并标记 processing
processing   -> 未超时时返回处理中
processing   -> 超时后允许接管
completed    -> 直接返回幂等成功
```

Redis 可以防止同一个 delete mutation 重复扣减 statistics，但不能单独保证 Redis、case 文件、snapshot 和 Git commit 的事务一致性；Git transaction 仍负责本地文件提交和回滚。

## 7. 统计更新事务

Knowledge case mutation 的提交边界为：

```text
检查 workspace clean
  -> 记录 base_revision
  -> 修改 case / statistics / schema
  -> 失败则 rollback
  -> 收集实际 changed paths
  -> 一次 Git commit
```

query 统计不进入这个 Knowledge transaction。query 统计写入失败时只记录日志，不阻断用户查询。

## 8. 与 case 统计的关系

- case 统计是生产侧真相统计
- query 统计是消费侧需求统计
- 两者都进入 knowledge 统计层
- 但只有 case 统计参与 v1 的 facet/schema 收敛

## 9. 对代码结构的影响

建议由 `internal/knowledge/statistics/` 统一接收两类输入：

- `case_statistics_ingestor`
- `query_statistics_ingestor`
- `semantic_observation_normalizer`

其中：

- case ingestion 接收 `domain/case` 已经产出的结构化字段
- query ingestion 接收 query 侧并行计算产出的结构化字段
- 两者都不在 ingestion 内重新做原文抽取
