# Knowledge 模块

Knowledge 负责把一批 case 变化整理成可审计的分区级知识 mutation。

## 主链路

```text
BacklogBatch
  -> BatchWorkingSetBuilder
  -> statistics snapshot
  -> FacetGovernanceService
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
| `facet_governance` | snapshot、current schema、working set | `FacetGovernanceResult` |
| `projection` | accepted schema、case ids | `ProjectionPlan` |
| `execution` | `KnowledgeMutationPlan` | 文件变更和更新路径 |
| `decision` | workflow 结论 | `KnowledgeDecisionRecord` |
| `workflow` | 上述模块 | `KnowledgeWorkflowResult` |

## Governance 结果

- `no_change`：当前结构无需调整，流程完成。
- `requires_review`：保存完整现场，冻结新的 Knowledge drain，等待人工处理。
- `accepted`：进入 projection 和 execution。

当前 `FacetGovernanceService.assess()` 仍是骨架；它的职责是只读分析和裁决，不修改文件。

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
