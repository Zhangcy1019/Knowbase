# Governance

Governance 是 Knowledge drain 的只读分析与裁决层，不直接修改 case、schema 或 Git。

## 主链路

```text
BatchWorkingSet
  -> preparation
  -> proposal plugins
  -> Runtime / LLM（仅当存在有效 proposal）
  -> validation plugins
  -> GovernanceResult
```

## Preparation

位置：`internal/knowledge/governance/preparation`

| 组件 | 作用 |
| --- | --- |
| `GovernanceEvidenceLoader` | 一次读取 statistics snapshot、partition、facet schema、受影响 case、facet index、semantic index |
| `GovernanceSignalCollector` | 生成 key 统计和治理信号 |
| `EvidenceConsistency` | 比较 snapshot 和两个 partition index 的 case/key 统计 |
| `CoverageEvaluator` | 计算 coverage assessment |
| `GovernanceActionPlanner` | 生成 case refresh candidate 和 rebuild recommendation |
| `GovernanceContextBuilder` | 编排以上组件并生成 `GovernancePreparation` |

当前信号：

- `missing_key_signal`：semantic profile 发生变化但 case 没有 facet。
- `stable_key_gap`：已有 facet key 在局部 case、全局 semantic index、全局 facet index 中都没有支持。
- `coverage_score`：治理证据分数，不单独触发 Runtime。

Coverage 计算：

```text
初始分数 = 1.0
每个 missing signal 扣 0.1，最多扣 0.4
每个没有 semantic index 支持的已有 key 扣 0.05，最多扣 0.3
有受影响 case 但 semantic index 为空时扣 0.2
最终分数不低于 0，保留两位小数
```

Preparation 在 drain 开始时冻结 statistics snapshot、facet index、semantic index、schema 和 affected cases。
snapshot 是全局计数、支持比例和阈值的主要依据；index 用于物化查询、supporting case 定位和交叉验证。
两者不一致时，Preparation 会阻断 Proposal，并记录具体 mismatch。

两个 materialized index 由 case 生命周期维护：case 创建、更新、删除后会基于当前
case 集合重建 `facet_index.json` 和 `semantic_index.json`，并与 case 文件一起提交
到分区 Git。启动阶段不会修改分区文件，也不会自动生成修复 commit；如果发现历史
状态不一致，Preparation 会阻断 Proposal，并要求显式 refresh/rebuild。若分区 Git
启动时已有未提交内容，仍先按 Git 启动保护阻断，不会覆盖或自动处理用户现场。

## Proposal

位置：`internal/knowledge/governance/proposal`

Proposal 只消费 Preparation 生成的 `GovernanceProposalContext`，不直接读取文件或存储。
它先发现 key 候选，value proposal 作为后续扩展点；它不生成 accepted schema，也不执行 mutation。

默认注册三个 key 插件：

| 插件 | 生效条件 | 输出 |
| --- | --- | --- |
| `semantic_key_promotion` | 新 key 不在 schema，且 snapshot 支持数达到阈值 | `suggested_new_keys` |
| `facet_key_demotion` | 已有 key 未被触碰，snapshot 中 semantic/facet 支持都为 0 | `suggested_removed_keys` |
| `facet_key_review` | 已有 key 被触碰，且存在 missing signal 或 stable gap | `suggested_updated_keys` |

### 三个 Proposal 插件的算法

三个插件都是确定性的候选发现器。它们只读取被冻结的
`GovernanceProposalContext`，不读取文件、不调用 Runtime、不修改 schema。
每个插件都会返回候选 key、触发原因、证据和 metrics；pipeline 再统一合并结果。

#### 1. `semantic_key_promotion`

目标是发现“已经在多个 case 的 semantic profile 中稳定出现，但还没有进入 facet
schema”的 key。

计算步骤：

1. 优先使用本次 drain 冻结的 `statistics_snapshot.semantic_key_counts` 和
   `statistics_snapshot.case_count`；没有快照时才使用 context 中的兼容性回退字段。
2. 从 semantic key 统计中排除 `existing_facet_keys`，避免重复提议已有 facet key。
3. 对每个剩余 key 计算支持数 `support_count`。
4. 只有满足以下阈值的 key 才会进入 `suggested_new_keys`：

   ```text
   support_count >= max(2, floor(case_count * 0.30))
   ```

因此，它表达的是“该 key 足够稳定，值得交给 Runtime 进一步分析”，不是“直接将
该 key 加入 schema”。当 `case_count` 为 0，阈值为 0，但没有统计候选时不会产生
有效 proposal。

输出证据包括：候选 key 的支持数、统计 case 总数、实际 promotion 阈值和当前
existing keys。

#### 2. `facet_key_demotion`

目标是发现可能已经失去实际意义的旧 facet key，避免仅因为某次 case 变化就删除
仍然有用的 key。

一个 key 必须同时满足以下条件才会进入 `suggested_removed_keys`：

- key 已经存在于当前 facet schema；
- key 不在本批次 `touched_facet_keys` 中；
- snapshot 中 semantic 支持数为 0；
- snapshot 中 facet 支持数也为 0。

也就是说，删除候选要求“当前批次没有直接触碰，并且全局两类统计都没有支持”。
插件不会因为单个 index 查询为空就直接删除，而是以快照统计作为判断依据；index
计数会作为交叉证据保存，便于排查 snapshot 与 index 是否一致。

输出证据包括 semantic/facet snapshot 计数、semantic/facet index 计数以及
`touched_in_batch`。只要 key 仍有任意一类统计支持，或者本批次正在处理该 key，
就不会提出删除。

#### 3. `facet_key_review`

目标不是直接提出新增或删除，而是要求重新评估“本批次涉及的已有 key”。它的
触发条件是：

- key 同时存在于 `touched_facet_keys` 和当前 facet schema；
- 本批次至少存在一个 `missing_key_signal` 或 `stable_key_gap`。

满足条件的 key 会进入 `suggested_updated_keys`。当前实现中的 signal 是批次级
证据，因此只要批次存在 coverage 缺口，符合上述条件的受影响已有 key 都会进入
复核候选；插件不会凭空生成新的 value，也不会在这里决定具体的 value 变化。

输出证据包括每个 key 是否为已有 key、是否在本批次被触碰、全部 missing signals
和 stable gaps，以及两类 signal 的数量。后续 Runtime / LLM 根据这些证据决定
是保留 key、调整 key 语义，还是提出具体 schema mutation。

### 合并、冲突和后续决策

Pipeline 会执行全部已注册插件，而不是遇到第一个结果就停止：

1. 对三个插件的候选列表去重，分别合并为新增、更新、删除候选。
2. 计算影响范围，包括受影响 case 数、各类 schema change 数和 conflict 数。
3. 如果同一个 key 同时出现不同动作，例如一个插件提出 `new`，另一个提出
   `update` 或 `remove`，则生成 `GovernanceProposalConflict`，不会静默覆盖。
4. 将每个插件的 root cause、reasons、evidence、metrics 和冲突详情写入
   `GovernanceProposalReport.reason_details`，供 Runtime、审计和 UI 使用。

Proposal 阶段的职责边界是“发现和解释候选”，最终是否接受、如何修改 accepted
schema 仍由只读 Runtime / LLM 决定，并由后续 validation 做硬性门槛校验。当前
三个插件只处理 key 层；`value proposal` 尚未接入，因此报告中的
`value_proposal_count` 固定为 0。

新增 key 阈值：

```text
max(2, floor(statistics_snapshot.case_count * 0.30))
```

Proposal pipeline 会执行全部插件，然后统一合并、去重、检测冲突和评估影响范围。
每个候选都会保存 root cause、evidence、reasons 和 metrics。

Proposal 状态：

```text
no_change  -> 没有有效候选，不调用 Runtime
proposed   -> 存在候选，交给只读 Runtime / LLM 判断
blocked    -> Preparation 证据不一致，禁止继续分析
```

如果多个插件对同一个 key 给出不同动作，不会静默覆盖：

```text
conflict: key=region
actions: new, update
next_action: Runtime / LLM resolve conflict
```

有效 proposal 的判断：

```text
suggested_new_keys 非空
或 suggested_updated_keys 非空
或 suggested_removed_keys 非空
```

没有有效 proposal 时，Governance 直接接受当前 schema，不调用 Runtime。

## Validation

位置：`internal/knowledge/governance/validation`

当前实际注册的插件只有 `fit_metrics`。

默认参数：

| 参数 | 默认值 | 作用 |
| --- | ---: | --- |
| `min_coverage_score` | `0.70` | candidate schema 的统计覆盖率下限 |
| `max_unobserved_keys` | `2` | 允许没有统计支持的 key 数量 |
| `min_key_support` | `2` | 新 key 的最小支持数 |
| `min_key_support_ratio` | `0.30` | 新 key 的最小支持比例 |

新 key 的实际支持阈值：

```text
max(min_key_support, floor(case_count * min_key_support_ratio))
```

Validation pipeline 会执行全部已注册插件；任意插件失败，整体失败。插件异常也按失败处理。

Validation 有两个使用位置：

1. Runtime 内部调用 `governance.validate_candidate`，辅助 LLM 自验证。
2. Runtime 返回 accepted schema 后，`GovernanceService` 再执行一次最终 gating。

## 暂未启用

代码已存在但当前没有注册：

| 插件 | 默认参数 |
| --- | --- |
| `FreezePolicy` | 最多新增 3 个 key，最多删除 1 个 key |
| `CircuitBreaker` | 最多影响 100 个 case，最多产生 5 个 schema change |

因此当前 `policy_evaluations` 为空，freeze 和 circuit breaker 不会阻断流程。

## 结果

```text
无 proposal
  -> accepted current_schema

有 proposal + Runtime accepted + final validation passed
  -> accepted candidate_schema

有 proposal + Runtime no_change
  -> accepted current_schema

Runtime requires_review 或 validation failed
  -> requires_review
```

每次结果同时保存两种原因：

- `reasons`：面向列表和日志的简短结论。
- `reason_details`：结构化决策轨迹，包含阶段、阻断代码、候选变化、插件理由、metrics 和下一步。

例如发现 schema proposal 时，不再只记录“需要 runtime 决策”，还会记录是哪个 proposal 插件提出了哪些 key，以及为什么必须进入只读 Runtime 决策阶段。
