# Partition 设计

`partition` 是当前系统最重要的作用域对象。

它不是简单的数据分类字段，而是整个系统的边界定义。

## partition 的四个角色

当前一个 partition 同时承担：

- 知识隔离边界
- semantic index 统计边界
- facet schema 正式结构边界
- runtime / backlog / run 的治理边界

因此：

- ingest 必须显式指定 partition
- query 默认在单个 partition 内完成
- backlog drain 默认按 partition 组织
- run 审计天然按 partition 聚合

## partition 与 case

关系是：

```text
Partition
  -> many Cases
```

每个 case：

- 归属一个 partition
- 保存自己的开放 `semantic_profile`
- 在当前 partition facet schema 下投影出 `facets`

## partition 与 semantic index

每个 partition 都维护自己的 `PartitionSemanticIndex`。

这个 index 保存的不是 case 原文，而是 partition 范围内的统计认知：

- 高频 key
- 高频 value
- 覆盖度
- aliases 候选
- 治理信号

这意味着 partition 还是：

- 开放语义统计边界

## partition 与 facet schema

每个 partition 都维护自己的 `PartitionFacetSchema`。

当前 facet schema 只管理：

- 哪些 key 是正式 facet
- 每个 key 的展示名和说明
- 是否启用

当前不再在 partition 层维护：

- value 闭集
- 强 canonical value list

## partition 与后台治理

当前后台治理链路里，partition 还是：

- backlog 过滤边界
- working set 组装边界
- semantic index refresh 边界
- facet 演化边界
- skill 副作用边界

这样做的直接好处是：

- 影响范围可解释
- rebuild 范围更容易控
- query 与治理上下文一致

## partition 与 query

query 默认只 consult 当前 partition：

- 当前 semantic index
- 当前 facet schema
- 当前 cases

所以 partition 决定的不只是“搜索范围”，还决定：

- query 的语义参考系
- query 的正式结构约束

## partition 后续可以继续承载什么

未来更合理继续挂在 partition 上的内容包括：

- 默认 backlog / runtime policy
- 默认 proposal mode
- 默认 budgets
- 默认 semantic index refresh 策略

## 一句话总结

当前 partition 的正确理解是：

`知识作用域 + 统计作用域 + 正式结构作用域 + 治理作用域。`
