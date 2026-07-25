# Knowledge Facet 收敛算法（v1）

本文档定义 Knowledge v1 的核心算法：`partition facet key convergence`。

目标：在不修改 case 原文的前提下，稳定收敛分区级 facet key，再据此重投影 case facet。

## 1. v1 只解决什么问题

v1 只处理：

- `partition facet key` 的 promotion / demotion
- 新 schema 下受影响 case 的 facet refit

v1 暂不处理：

- 文档主轴重组
- semantic_fields 反向回写
- 开放词表 value 收敛
- 高复杂度 value schema 维护

## 2. 输入

facet 收敛算法输入为：

- `current partition facet schema`
- `PartitionSemanticIndex`
- `affected case set`
- `partition description`
- `global / partition level policy config`

## 3. 输出

输出为一个候选 schema proposal：

- `promoted_keys`
- `demoted_keys`
- `unchanged_keys`
- `risk_summary`
- `estimated_coverage_gain`
- `estimated_migration_cost`

最终转为：

- `PartitionFacetSchemaPatch`

## 4. promotion 判定

一个候选 `canonical_key` 升格为 facet key，建议至少满足以下条件：

1. `case_support_count >= min_case_support`
2. `consecutive_support_batches >= min_support_batches`
3. `value_entropy <= max_entropy`
4. `confidence_mean >= min_confidence`
5. `coverage_gain >= min_coverage_gain`
6. 不在冻结窗口内

说明：

- `support` 解决“是否广泛存在”
- `stability` 解决“是否只是短期噪声”
- `entropy` 解决“是否适合做 facet”
- `coverage_gain` 解决“升格是否值得”

## 5. demotion 判定

一个已有 facet key 可降级，建议至少满足：

1. `case_support_count <= max_case_support_for_demote`
2. 连续多个窗口低支持或长期无支持
3. `coverage_loss_if_removed <= max_allowed_loss`
4. 不在冷却窗口内

说明：

- demotion 必须比 promotion 更保守
- 高风险结构不允许轻易撤销

## 6. 冻结与冷却规则

为了避免 schema 抖动，v1 必须有冻结算法。

建议规则：

### 6.1 冻结窗口

- 新升格的 key 在 `cooldown_batches` 内不可降级
- 新降级的 key 在 `cooldown_batches` 内不可重新升格

### 6.2 变更上限

- 单 batch 最多允许 `N` 个高风险 facet key 变化

### 6.3 批次门槛

- 候选 key 至少连续 `M` 个 batch 满足 promotion 条件，才允许正式升格

## 7. v1 的量化指标

建议 v1 先使用以下四个核心量。

### 7.1 case_support_count

定义：

- 支持该 `canonical_key` 的不同 case 数量

### 7.2 consecutive_support_batches

定义：

- 该 key 连续多少个 batch 都出现

### 7.3 value_entropy

定义：

- 该 key 的 value 分布熵

### 7.4 coverage_gain

定义：

- 升格该 key 后，多解释多少 case

## 8. partition_fit_score

v1 需要定义一个最小可计算的 `partition_fit_score`。

建议定义：

```text
partition_fit_score =
  covered_case_count / active_case_count
```

其中：

- `covered_case_count`：至少命中一个当前 partition facet key 的 case 数
- `active_case_count`：当前活跃 case 总数

更细版本可后续升级为加权拟合度，但 v1 先用简单覆盖率即可。

## 9. coverage_gain

建议定义：

```text
coverage_gain(candidate_key) =
  covered_case_count_after_promote(candidate_key)
  - covered_case_count_before
```

也可以归一化为：

```text
normalized_coverage_gain =
  coverage_gain / active_case_count
```

## 10. 熔断前模拟

在正式输出 patch 前，必须先做模拟评估。

至少评估：

- `partition_fit_score_before`
- `partition_fit_score_after`
- `coverage_gain`
- `affected_case_count`
- `added_facet_key_count`
- `removed_facet_key_count`

只有通过熔断评估，schema proposal 才能转为正式 patch。

## 11. case facet refit

一旦 facet schema 通过，就进入第二阶段：

- 用新的 partition facet schema
- 遍历受影响 case
- 重新投影 case facet

这个阶段应尽量保持简单：

- 输入：case 原文 + current semantic candidates + new facet schema
- 输出：新的 case facet

这里不要求重新整理 semantic_fields。

## 12. v1 结论

Facet 收敛算法 v1 的本质是：

- 用分区语义统计判断哪些 key 值得稳定化
- 用冻结算法防止抖动
- 用拟合率与影响规模做熔断
- 通过后再重投影 case facet

也就是说：

- `schema convergence` 是第一核心算法
- `case facet refit` 是紧随其后的执行性算法
