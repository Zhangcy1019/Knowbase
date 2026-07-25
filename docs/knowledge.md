# Knowledge 文档入口

原 [knowledge.md](/home/zcy/Project/knowbase/docs/knowledge.md) 中的统一规约已经拆分，避免一份总文档和多份子文档并存导致重复与漂移。

当前请以以下文档为准：

1. [knowledge_architecture.md](/home/zcy/Project/knowbase/docs/knowledge_architecture.md)
说明 Knowledge v1 的总体边界、主链路和模块分层。

2. [knowledge_semantic_index.md](/home/zcy/Project/knowbase/docs/knowledge_semantic_index.md)
说明 `CaseSemanticCandidate`、`PartitionSemanticIndex`、统计量与反向索引。

3. [knowledge_query_stats.md](/home/zcy/Project/knowbase/docs/knowledge_query_stats.md)
说明 query 如何进入 knowledge 统计层，以及为什么当前不参与知识结构决策。

4. [knowledge_facet_convergence.md](/home/zcy/Project/knowbase/docs/knowledge_facet_convergence.md)
说明 `partition facet key convergence`、冻结规则、拟合度与熔断前模拟。

5. [knowledge_mutation_execution.md](/home/zcy/Project/knowbase/docs/knowledge_mutation_execution.md)
说明 `KnowledgeMutationPlan`、执行器、Git 事务、回滚与审计。

当前推荐阅读顺序：

1. 架构总览
2. 语义统计与索引
3. query 统计输入
4. facet 收敛算法
5. mutation 与执行链路
