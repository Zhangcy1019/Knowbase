# Runtime Harness

`internal/runtime` 是通用的受控 agent 执行底座。它不拥有 Knowledge 业务规则。

## 输入

核心输入是 `RuntimeRunRequest`，包含：

- objective / task description
- input context
- allowed tools
- allowed skills
- step、tool、skill budgets
- verification profile（如调用方需要）

调用方通过 request 注入能力和边界，runtime 不自行扩大权限。

## 执行链路

```text
RuntimeRunRequest
  -> create run
  -> initialize loop state
  -> generate decision
  -> validate and normalize actions
  -> execute tool / skill
  -> record observation and trace
  -> repeat or stop
  -> finalize RuntimeRunResult
```

每一轮都重新生成 decision。`should_stop=false` 只表示当前 decision 仍有后续工作，不代表 runtime 可以跳过下一轮；最终终止由 loop、budget、review 或 acceptance 共同决定。

## 能力模型

- tool：只读观察或查询
- skill：受 schema 约束的能力调用，可产生副作用
- subrun：受限的子 runtime；子 run 不能派生新的 child run

runtime 负责校验 allowed list、输入 schema、budget 和审计；业务模块负责注册具体 tool/skill。

## 输出

`RuntimeRunResult` 包含：

- run status
- applied actions
- tool results
- skill results
- failure information
- trace references

run、step、artifact 属于运行审计数据，不纳入 partition Git。
