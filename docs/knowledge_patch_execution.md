# Knowledge Patch 与执行链路（v1）

本文档定义 Knowledge v1 中 patch 的语义模型、git 执行方式、熔断、提交、回滚与封存链路。

目标：让知识整理结果既有结构化语义，又能充分利用本地文件与 git 的版本化能力。

## 1. 为什么不能只用 git diff

git 很适合处理：

- commit
- branch
- revert
- 审计
- 历史对比

但 git diff 不能直接承担 Knowledge 算法语义层。

Knowledge 仍然需要自己的 patch 对象，用来表达：

- 这次变更改了哪些 facet key
- 影响了哪些 case
- 风险等级是什么
- 是否可逆
- 熔断评估结果是什么

因此需要分层：

- `KnowledgePatch`: 语义层
- `GitPatchEnvelope`: 存储与执行层

## 2. KnowledgePatch 建议结构

建议至少包含：

- `patch_id`
- `batch_id`
- `partition`
- `created_at`
- `risk_level`
- `reversible`
- `partition_facet_schema_patch`
- `case_facet_patches`
- `metrics_snapshot`
- `circuit_breaker_report`
- `affected_case_ids`
- `summary`

## 3. 子 patch 类型

v1 至少需要两类 patch。

### 3.1 PartitionFacetSchemaPatch

字段建议：

- `added_keys`
- `removed_keys`
- `renamed_keys`
- `frozen_keys`
- `before_schema_version`
- `after_schema_version`

### 3.2 CaseFacetPatch

字段建议：

- `case_id`
- `added_facets`
- `removed_facets`
- `updated_facets`
- `schema_version`

## 4. 可逆性约束

KnowledgePatch 必须满足：

- 所有操作都可逆
- 回滚粒度为 batch
- 不允许不可逆操作直接落盘执行

如果某个候选 patch 无法明确逆操作：

- 直接拒绝执行
- 进入封存分析

## 5. 熔断评估

在 patch 提交前，必须先生成 `CircuitBreakerReport`。

建议至少包含：

- `fit_score_before`
- `fit_score_after`
- `fit_score_delta`
- `affected_case_count`
- `added_facet_key_count`
- `removed_facet_key_count`
- `triggered_rules`
- `passed`

典型熔断条件：

- 拟合率显著下降
- 变更 case 数过大
- 单批次高风险 key 变化过多
- promotion / demotion 命中冻结规则

## 6. git 执行链路

建议流程：

1. 生成 `KnowledgePatch`
2. 通过熔断评估
3. 为该 batch 建立临时执行分支
4. 将 patch 落地为本地文件变更
5. 生成 git diff
6. commit
7. 标记该 batch 已提交

回滚时：

1. 根据 `patch_id` / `commit_id` 定位目标
2. 执行 git revert 或等价逆 patch
3. 写入回滚审计记录
4. 将 batch 标记为“已回滚封存”

## 7. 状态机建议

批次至少建议包含：

- `proposed`
- `blocked_by_circuit_breaker`
- `committed`
- `rolled_back`
- `archived`

语义要求：

- `blocked_by_circuit_breaker` 不可直接重试执行
- `rolled_back` 不可直接再次应用原 patch
- `archived` 只能重新 drain 生成新 patch

## 8. 人工分析边界

人工只做：

- 阅读 patch
- 阅读熔断报告
- 分析失败原因
- 决定是否重新 drain

人工不直接修补 patch 本身。

## 9. 与 runtime 的关系

KnowledgePatch 可以由 runtime 执行，但 patch 语义仍属于 knowledge。

关系如下：

- knowledge 生成 `KnowledgePatch`
- dispatch 将 patch 应用任务装入 `RuntimeRunRequest`
- runtime 调用具体 tool / skill 执行 patch
- runtime 返回运行轨迹与结果
- knowledge 负责记录是否提交 / 回滚 / 封存

## 10. 本地文件建议

既然当前系统以本地文件为主，建议保留以下目录：

```text
workspace/knowledge/
  partitions/{partition}/
    semantic_index.json
    facet_schema.json
    patches/
      {patch_id}.json
    patch_reports/
      {patch_id}.json
```

其中：

- `patches/` 存 `KnowledgePatch`
- `patch_reports/` 存熔断与提交报告

## 11. v1 结论

Knowledge v1 不应把 git 当成算法本体，而应：

- 先构建 `KnowledgePatch`
- 再用 git 管理其落盘执行

这样才能同时满足：

- 可逆
- 可审计
- 可熔断
- 可回滚
- 可做结构化人工分析
