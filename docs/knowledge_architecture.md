# Knowledge 模块总方案（v1）

本文档定义 Knowbase `knowledge` 模块的 v1 总体架构。

目标：围绕 `case 原文 -> case 结构化结果 -> knowledge 统计索引 -> 分区 facet 收敛 -> case facet 重投影 -> 可逆 patch 执行` 建立一条稳定、可解释、可回滚的知识整理主线。

## 1. 核心边界

### 1.1 真相边界

- `case` 原文是唯一真相
- `case` 原文不可修改
- 所有结构化整理结果都必须从 `case` 原文推导出来

### 1.2 收敛边界

Knowledge v1 的主目标不是直接整理文档，而是先稳定分区级 schema：

1. `partition facet key` 收敛
2. `partition facet value` 收敛
3. `case facet` 在当前分区 facet 约束下重投影

其中：

- `facet` 是强约束、稳定化后的知识分类主轴
- `semantic candidates / semantic_profile` 是弱约束统计层
- `document convergence` 后置，不进入 v1 主闭环

### 1.3 模块边界

- `knowledge` 负责：
  - 接收 case / query 的结构化统计输入
  - 分区统计与索引
  - facet 收敛判定
  - patch 生成
  - 熔断评估
- `runtime` 负责：
  - 接收知识任务
  - 调用 tool / skill 落地执行
  - 记录运行轨迹
  - 做执行期验证

## 2. v1 单向算法链

Knowledge v1 必须保持单向计算，不允许形成统计自举回路。

统一链路如下：

1. case 写入时，由 `domain/case` 完成 `facet` 和 `semantic_profile`
2. knowledge 接收 case 的结构化增量，写入分区统计层
3. query 到来时，可并行生成 query 的 `facts / semantic_profile`，并仅写入 knowledge 统计层
4. `drain backlog` 生成 batch
5. 从 batch 中确定受影响 case 集
6. 基于当前分区统计与索引，构建本轮 `BatchPreparation`
7. 基于当前 `PartitionSemanticIndex + 当前 facet schema` 进行 `facet key convergence`
8. 若 facet schema proposal 通过熔断评估，则生成新的 partition facet schema
9. 使用新的 facet schema 对受影响 case 重新投影 `case facet`
10. 输出一个批次级 `KnowledgePatch`
11. 通过 git 管理的 patch 执行链进行提交 / 回滚 / 封存

## 3. 分层模型

### 3.1 原始层

- case title
- case content
- case metadata

### 3.2 统计输入层

- `case facet / semantic_profile` 的增量写入
- `query facts / semantic_profile` 的增量写入
- 面向统计与发现，不面向直接治理

### 3.3 收敛层

- `partition facet schema`
- `partition facet values`
- `case facet`

### 3.4 执行层

- `KnowledgePatch`
- git commit / branch / revert / archive

## 4. v1 明确不做的事情

v1 不进入以下能力：

- 文档主轴重组
- 多文档合并 / 拆分
- `case semantic_fields` 反向重写
- 开放词表 value 的自动收敛
- 一个 batch 内多个高风险 facet key 同时自动调整
- 自动修补失败 patch

## 5. v1 的功能模块

目录按稳定的功能边界划分，不按执行顺序划分。执行顺序由顶层 workflow 负责。

### 5.1 Domain Model

定义 Knowledge 的领域对象：case/query observation、partition statistics、facet schema、convergence proposal、batch 和 `KnowledgePatch`。不负责外部读写和 runtime 调用。

### 5.2 Statistics

职责：

- knowledge 不负责单 case 原文抽取
- 接收 `domain/case` 已经产出的 `facet / semantic_profile`
- 接收 query 侧并行产出的 `facts / semantic_profile`
- 做规范化、聚合、反向索引以及统计快照读写

约束：

- query 当前只进入统计层
- query 当前不参与 facet/schema 自动决策
- case 使用 `CaseStatisticsSnapshot` 并纳入 Git
- query 使用独立的 `QueryStatisticsSnapshot`，写入 `runtime_statistics/query`，不纳入 Git
- snapshot 不保存 observation 历史 ID；case mutation 的幂等由生命周期层负责

### 5.3 Schema

职责：

- 分析 facet schema 的覆盖率和稳定性
- 提出 facet key/value 变化
- 执行冻结、冷却和熔断判断
- 只输出 proposal/decision，不直接修改数据

### 5.4 Projection

职责：

- 使用已确定的 facet schema 重新投影受影响 case
- 计算 case facet 变化
- 输出 projection change
- 不负责决定 schema 是否变化

### 5.5 Patch

职责：

- 生成可逆 `KnowledgePatch`
- 保存 patch 和快照
- 通过 Git 执行提交、回滚与封存

### 5.6 Integrations

负责 backlog、case、partition 和 runtime 的边界适配，不承载 Knowledge 算法。

### 5.7 Workflow

`KnowledgeDrainWorkflow` 是顶层编排者，负责串联 batch、statistics、schema、projection、patch 和 runtime request，但不实现这些模块内部的算法。

Backlog 只向 Knowledge 投递 batch，不等待 runtime 结果。Knowledge service 将 batch 放入自己的后台处理任务，由该任务独立调用 runtime 一次或多次，并在最终完成后通过 `EventBacklogPort` 更新 backlog 状态。backlog port 只负责 batch 生命周期，不暴露 runtime 执行接口。

```text
KnowledgeDrainWorkflow
  -> batch resolver
  -> StatisticsService
  -> SchemaService
  -> ProjectionService
  -> PatchService
  -> RuntimeRequestFactory
```

### 5.8 Capability Registration

Knowledge 的 skill/tool 只作为能力声明或注册适配。具体能力注册和执行仍由 runtime 负责，不属于 Knowledge 主领域链路。

## 6. v1 设计原则

1. `case` 是唯一真相，不改原文
2. `facet` 是主轴，`semantic candidates` 是统计中间层
3. 先收敛 key，再考虑 value
4. 先稳定 schema，再做 case refit
5. 只允许可逆 patch
6. 任何高风险结构变更都必须经过熔断评估
7. 无法安全自动执行时，整批封存而不是部分提交

## 7. 代码结构建议

建议拆成以下目录：

```text
internal/knowledge/
  model/
  ports/
  batch/
  statistics/
  facet_governance/
  schema/
  projection/
  patch/
  integrations/
  workflow/
  service.py
```

对应关系：

- `model/`: Knowledge 私有领域对象；跨模块共享对象仍放在 `internal/models`
- `ports/`: Knowledge 内部组合边界；跨模块稳定 port 统一定义在 `internal/ports`
- `batch/`: backlog batch 的工作集解析与准备
- `statistics/`: 统计输入、聚合、索引与快照
- `facet_governance/`: facet schema 分析、收敛与安全策略；对外通过 `assess()` 提供统一治理入口
- `projection/`: case facet 重投影
- `patch/`: KnowledgePatch 生成、持久化与 Git 应用
- `integrations/`: case、partition、runtime 边界适配
- `workflow/`: 顶层 Knowledge 编排
- `service.py`: Knowledge 对外统一入口，支持 batch、手动 API 等多种触发源

## 8. 作为实现依据的主结论

Knowledge v1 的主闭环是：

- `case raw text`
- `case / query statistics ingestion`
- `partition semantic index`
- `facet key convergence`
- `case facet refit`
- `KnowledgePatch`
- `runtime execution`

这一闭环先于文档整理与更高层知识主轴管理。目录表达功能边界，实际执行顺序只存在于 `workflow/`。
