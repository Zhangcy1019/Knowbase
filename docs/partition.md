# Partition

`partition` 是知识、统计、任务、并发和版本控制的共同边界。

## 文件布局

```text
local_root/
  partitions/
    CI/
      .git/
      partition.json
      facet_schema.json
      facet_index.json
      semantic_index.json
      cases/*.json
  knowledge_statistics/CI/snapshot.json
  runtime_statistics/query/CI/snapshot.json
  events/*.json
  audit/decisions/*.json
  runs/...
```

分区 Git 只管理知识文件：case、schema、index 和 partition 配置。statistics、audit、logs、runs 不进入分区 Git。

## Git 生命周期

分区创建时：

1. 创建分区文件和默认 profile 文件。
2. 初始化 `partitions/{partition}` Git 仓库。
3. 将初始文件提交为 baseline。

每次 mutation 前：

1. 检查仓库存在且 clean。
2. 记录 `base_revision`。
3. 修改文件。
4. 收集实际 changed paths。
5. 成功则 commit，失败则 rollback。

已有仓库有未提交内容时，操作拒绝并要求人工处理。

## 并发

- 同一 partition 的 task FIFO 串行。
- 文件/Git mutation 使用 `PartitionMutationLock`。
- 不同 partition 可以并行。
- review lock 只阻止新的 Knowledge drain，不阻止 case 输入。
