# Knowledge Mutation 执行链路

本模块不再维护独立的 `KnowledgePatch`。在当前本地文件加 Git 的实现中，patch 只是对已经存在的治理裁决和投影结果做重复包装，既不负责版本控制，也不负责独立审批或传输。

## 核心对象

- `FacetGovernanceResult`：语义分析和稳定性规则共同产生的 schema 裁决；LLM 只参与这一层的分析。
- `ProjectionPlan`：在已接受 schema 下，为指定 case 计算出的确定性 facet 前后差异。
- `KnowledgeMutationPlan`：将一次已接受的 schema 裁决和一个 `ProjectionPlan` 组合为执行输入。
- `KnowledgeMutationExecutor`：唯一允许写入 partition schema 和 case facet 文件的组件。
- `MutationTransaction`：版本控制事务；负责工作区基线、实际变更路径收集、Git commit 和失败回滚。

`KnowledgeMutationPlan` 包含：`plan_id`、batch、partition、accepted schema、case changes、风险等级、原因和摘要。它不复制 Git diff，也不持久化为第二套版本历史。

## 主链路

1. 统计模块提供当前分区的聚合证据。
2. facet governance 生成并接受或拒绝 schema 变化；拒绝或需要人工审查时不进入写入。
3. projection 在 accepted schema 下生成 `ProjectionPlan`。
4. workflow 构造 `KnowledgeMutationPlan`。
5. `MutationTransaction` 记录 Git 基线。
6. `KnowledgeMutationExecutor.apply(plan=...)` 校验 case 当前 facet 与 `before_facets` 一致后写入文件。
7. 执行后运行确定性验证；验证通过才提交 transaction，异常则回滚。

执行器会先校验整个 plan 的 partition、case 存在性和 `before_facets`，再开始任何写入。workflow 会在执行前向 transaction 登记 plan 的全部潜在路径，因此后续 I/O 异常也能按 Git 基线回滚。

## 约束

- LLM 或 runtime skill 不得直接修改 knowledge 文件。
- 执行器必须校验 partition 和 `before_facets`，防止陈旧计划覆盖并发修改。
- Git 是唯一版本历史和回滚机制；mutation plan 只是一次内存中的受控执行输入。
- 如果以后需要跨进程人工审批、计划持久化或导出，才增加独立的 plan repository，而不是恢复 patch 包装层。
