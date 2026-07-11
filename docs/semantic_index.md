# Semantic Index 设计

`PartitionSemanticIndex` 是当前系统最关键的统计中间层。

## 为什么需要 semantic index

如果只有开放 `semantic_profile`，会遇到两个问题：

- query 不知道库里常见的表达方式
- 后台结构治理没有长期统计依据

semantic index 的出现，就是为了解决这两个问题。

## semantic index 的定位

它位于：

- case 开放语义层
- facet 正式结构层

之间。

它既不保存原始事实，也不直接代表正式 schema。

## semantic index 的职责

核心职责：

- 聚合 case 的开放语义
- 统计高频 key / value
- 为 query 提供对齐参考
- 为 facet 演化提供证据
- 为新 case 写入提供偏置参考

## semantic index 不是做什么的

它不应：

- 替代 case 原始事实
- 成为强校验器
- 限制开放 `semantic_profile`
- 等价于 facet schema

所以它是：

- 统计层
- 参考层
- 检索增强层

不是：

- 强约束层

## 当前建议维护的信息

一个 `PartitionSemanticIndex` 可以维护：

- 高频 key
- 高频 value
- key 覆盖度
- aliases 候选
- 治理候选信号

后续如有必要，再逐步增加：

- co-occurrence
- query utility signals
- dormant key signals

## 它在三条主流程里的作用

### 1. 写入

新 case 在生成 `semantic_profile` 时参考 semantic index，可以：

- 尽量复用已有表达
- 降低无意义新 key / 新 value 的数量

### 2. query

query consult semantic index，可以：

- key alignment
- value alignment
- alias resolution
- retrieval expansion

### 3. backlog / runtime 治理

后台治理 consult semantic index，可以：

- 发现 promote 候选
- 发现 demote 候选
- 发现冗余 key
- 生成治理解释

## 当前与 backlog / runtime 的关系

semantic index 是 backlog preparation 和 runtime request context 的重要输入之一。

后台链路不应该直接“凭感觉”做 facet 调整，而应该基于：

- semantic index snapshot
- 当前 facet schema
- 当前 batch working set

来给出 preparation assessment 和 action hints。

## 一句话总结

`PartitionSemanticIndex` 是当前系统的语义统计认知层，是 query 对齐和结构治理的共同基础。
