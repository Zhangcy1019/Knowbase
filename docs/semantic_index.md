# Statistics 与 Semantic Index

## 定位

`PartitionSemanticIndex` 是开放语义的分区级统计层，位于 case semantic profile 和正式 facet schema 之间。

它提供：

- key/value 频次
- 覆盖率和 case count
- alias / support 参考
- query 对齐参考
- facet governance 证据

它不是事实源，也不是强约束 schema。

## 两类统计

### Case statistics

来源是 `domain/case` 已经生成的 facet 和 semantic profile，存储为：

```text
knowledge_statistics/{partition}/snapshot.json
```

### Query statistics

query 的 facts/semantic profile 独立存储：

```text
runtime_statistics/query/{partition}/snapshot.json
```

query 当前只做统计，不直接影响 facet/schema 收敛。

## 更新方式

- case create：append observation
- case update：replace old observation with new observation
- case delete：remove old observation
- query：append query observation
- snapshot 文件使用临时文件替换，并按 partition 加锁

当前 snapshot 不保存历史 observation id，因此生命周期服务必须保证 update/delete 的调用语义正确。Redis 幂等层暂未接入。

## Drain 快照

Knowledge drain 开始时读取一次当前 statistics，作为本轮治理输入；完整现场写入 `KnowledgeDecisionRecord` 用于复盘。治理过程中不重新读取 live snapshot。
