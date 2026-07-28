# 主流程

## 1. Case 输入

```text
request
  -> validate partition
  -> build draft
  -> extract summary / semantic_profile
  -> project facets from current schema
  -> enqueue case_input
  -> return case_id + task_id
```

`case_input` task 在同一 partition worker 中完成：

```text
case_input
  -> acquire mutation lock
  -> write case
  -> update case statistics
  -> Git commit case file
  -> publish KnowbaseEvent
```

只有 case 文件和 Git 提交成功后才发布 event。

## 2. Query

```text
query request
  -> normalize
  -> extract query semantic profile
  -> consult semantic index
  -> retrieve / rank / synthesize answer
  -> asynchronously update query statistics
```

query statistics 不直接触发 Knowledge drain，也不直接修改 facet schema。

## 3. Knowledge drain

```text
EventRecord
  -> assemble BacklogBatch
  -> enqueue knowledge_drain
  -> capture case statistics snapshot
  -> Governance preparation
  -> proposal plugins
  -> Runtime / LLM（有有效 proposal 时）
  -> validation
  -> GovernanceService.assess()
  -> no_change / requires_review / accepted
  -> ProjectionService.plan()
  -> KnowledgeMutationExecutor.apply()
  -> Git commit or rollback
```

`EventWorker` 只提交 batch，立即返回 `accepted`。真正的 Knowledge 处理由 `PartitionTaskQueue` 异步完成。

## 4. 任务串行化

同一 partition 的以下任务按 FIFO 执行：

- `case_input`
- `case_update`
- `case_delete`
- `knowledge_drain`
- `review_apply`
- `partition_disable`
- `partition_delete`

不同 partition 可以并行。文件和 Git 变更另外受 `PartitionMutationLock` 保护。
