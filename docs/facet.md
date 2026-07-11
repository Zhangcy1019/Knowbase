# Facet 设计

`facet` 是当前系统中的正式结构层，不是完整语义层。

## facet 的定位

当前层次关系是：

- `case` 是事实源
- `semantic_profile` 是开放语义层
- `PartitionSemanticIndex` 是统计归纳层
- `facets` / `PartitionFacetSchema` 是正式结构层

因此 facet 只负责三件事：

- 提供稳定 filter 维度
- 提供稳定聚合和展示字段
- 作为治理输出对象

## facet 与 semantic_profile

当前主规则非常明确：

1. 写入 case 时先生成开放 `semantic_profile`
2. 再根据当前 `PartitionFacetSchema` 从 `semantic_profile` 投影出 `facets`

所以：

- `semantic_profile` 是主语义表达
- `facets` 是正式视图

反过来不成立：

- 不能让 `facets` 完整决定 `semantic_profile`

## facet 与 semantic index

`facet` 的正确来源不是单条 case，而是统计层。

关系应理解为：

```text
case.semantic_profile
  -> partition semantic index
  -> facet evolution
  -> facet schema
```

也就是说：

- case 提供开放信号
- semantic index 提供长期统计
- facet schema 只沉淀少量稳定 key

## facet schema 该管理什么

当前 `PartitionFacetSchema` 只应管理：

- `key`
- `display_name`
- `description`
- `examples`
- `enabled`

不再管理：

- `allowed_values`
- value 闭集
- 强 canonicalization 规则

原因很简单：

- 当前治理重点是 `key`
- value 保持开放更符合知识演化现实

## 哪些 key 适合被提升为 facet

通常应满足：

- 在 semantic index 中持续高频出现
- 覆盖较多 case
- 语义稳定
- 对 query / filter / 展示有价值
- 与已有 facet 不高度重叠

重要原则：

- promote 主要看长期统计
- 不应因为一个 batch 里偶然出现就提升

## 哪些 facet key 适合被降级

应更保守。

通常需要看到：

- 长期覆盖低
- 价值弱
- 与其他 key 高度重复
- 已经不适合作为正式结构维护

降级不等于“这次 batch 没出现”，而是：

- 在长期统计和使用价值上都不值得继续保留

## facet 演化的真实目标

facet 演化不是为了“让所有 case 都变成结构化表单”，而是为了：

- 从开放语义中提炼少量正式结构
- 控制正式结构的膨胀速度
- 让 query 和 UI 有稳定抓手

## facet 变化后 case 是否需要适配

需要，但不应默认全量同步重建。

### 新增 facet key

如果新增一个 facet key：

- 新写入 case 应立即按新 schema 生成该 key 的 `facets`
- 历史 case 需要在后续 rebuild 中逐步补齐 projection

### 删除 facet key

如果删除一个 facet key：

- query / filter / UI 层应立即忽略该 key
- case 存储里的旧 projection 可以延迟清理

也就是说：

- 先逻辑失效
- 再物理收敛

## 为什么不能默认全量重建

如果每次 promote / demote 都要求：

- 全 partition 扫描
- 全量重建 case facets

系统会重新回到旧问题：

- rebuild 成本高
- runtime 太重
- 治理过程不稳定

所以 facet schema 变化后的 case 适配必须依赖最小影响范围判断，而不是默认全量刷新。

## 一句话总结

当前 facet 的正确理解是：

`从开放 semantic_profile 经过 semantic index 归纳后沉淀出来的少量正式结构。`
