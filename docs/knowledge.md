# Knowledge 模块

Knowledge 负责把一批 case 变化整理成可审计的分区级知识 mutation。

## 主链路

```text
BacklogBatch
  -> BatchWorkingSetBuilder
  -> statistics snapshot
  -> Governance preparation
  -> schema proposal
  -> Runtime / LLM（有 proposal 时）
  -> validation
  -> ProjectionService
  -> KnowledgeMutationPlan
  -> KnowledgeMutationExecutor
  -> partition Git transaction
```

## 模块职责

| 模块 | 输入 | 输出 |
| --- | --- | --- |
| `batch` | `BacklogBatch` | `BatchWorkingSet` |
| `statistics` | case/query observation | snapshot、统计查询、支持 case 查询 |
| `governance/preparation` | `BatchWorkingSet`、partition 数据 | `GovernancePreparation` |
| `governance/proposal` | Preparation context | `GovernanceProposalReport` |
| `governance/validation` | candidate schema、statistics | validation report |
| `governance` | preparation、proposal、validation、Runtime 结果 | `GovernanceResult` |
| `projection` | accepted schema、case ids | `ProjectionPlan` |
| `execution` | `KnowledgeMutationPlan` | 文件变更和更新路径 |
| `decision` | drain 输入、治理阶段、裁决和执行审计 | `KnowledgeDecisionRecord` |
| `workflow` | 上述模块 | `KnowledgeWorkflowResult` |

详细策略和参数见 [`governance.md`](governance.md)。

## Governance 结果

- `no_change`：当前结构无需调整，流程完成。
- `requires_review`：保存完整现场，冻结新的 Knowledge drain，等待人工处理。
- `accepted`：进入 projection 和 execution。

`GovernanceService` 只读分析和裁决，不修改文件。只有生成 accepted schema 后，流程才进入 projection 和 execution。

## Decision 审计记录

每次 drain 生成一个 `audit/decisions/{decision_id}.json`。它不是多个阶段的无结构快照
拼接，而是按以下边界记录：

```text
input
  -> stages.preparation
  -> stages.proposal
  -> stages.runtime       （没有调用时不生成）
  -> stages.validation    （没有执行时不生成）
  -> stages.projection
  -> stages.mutation_plan
  -> stages.apply
  -> outcome / execution
```

- `input`：drain 开始时冻结的 `base_revision`、statistics fingerprint、statistics snapshot 和 working set。
- `stages`：每个实际执行阶段的 `status`、输入、输出、原因、错误和采集时间；未发生的阶段不写空对象。
- `outcome`：Governance 的业务裁决，包括 `no_change`、`accepted`、`requires_review` 或 `failed`，以及 accepted schema 和详细原因。
- `execution`：mutation plan、计划路径、实际路径、更新的 case、Git revision、rollback 和错误；它只描述实际执行，不把计划误当成结果。
- `status_history`：完整状态转换，例如 `accepted -> applying -> applied`，或 `accepted -> applying -> failed`。

Decision 状态不再使用无意义的默认 `proposed`。每条记录创建时必须明确状态：

```text
no_change         没有有效 schema proposal，流程无需 mutation
requires_review   治理阻断或需要人工处理
accepted          治理接受结果，尚未开始写入
applying          已进入 mutation apply
applied           mutation 和 Git commit 均完成
failed            apply、validation 或其他阶段失败
```

Runtime 的 prompt、response、tool、skill 和每轮 trace 仍由 Runtime trace 保存；Decision
通过 stage output 中的 `run_id` 或 metadata 关联它们，不重复保存完整 Runtime 现场。

## Projection 与 execution

`ProjectionService` 只计算 case facet 应有的变化：

```text
current case + accepted schema -> CaseProjectionChange
```

`KnowledgeMutationExecutor` 才写入 case/schema 文件。执行前记录实际路径，失败时回滚；成功后由 `VersionCommitCoordinator` 提交分区 Git。

## Knowledge 不负责

- 修改 case 原文
- 直接调用 Git
- 直接调用 LLM 修改文件
- 把 query 统计直接转成 facet 变化
- 在 workflow 中实现收敛算法
