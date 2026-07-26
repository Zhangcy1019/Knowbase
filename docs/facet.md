# Facet 与 Semantic Profile

## 层次

```text
case 原文
  -> semantic_profile（开放语义）
  -> PartitionSemanticIndex（分区统计）
  -> PartitionFacetSchema（正式结构）
  -> case.facets（正式视图）
```

`case` 原文是事实源；`semantic_profile` 保留开放表达；`facets` 必须服从当前 partition facet schema。

## Facet Schema

当前 schema 主要描述：

- key
- display name
- description
- examples
- enabled

它不是完整的 value 闭集，也不是原文的替代品。

## 治理原则

- 优先评估 facet key，再评估 value。
- promote 需要长期统计、覆盖率和语义稳定性证据。
- 单个 batch 的偶然信号不足以改变主轴。
- 高风险变化经过 freeze/circuit-breaker 后才能 accepted。
- governance 只返回结论，不写文件。

schema accepted 后，`ProjectionService` 为受影响 case 生成 facet changes；execution 再统一落盘。
