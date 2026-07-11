# Runtime Agent Harness

本文档说明 `internal/runtime` 的定位和主链路。

## runtime 是什么

`runtime` 是一次受控执行框架。

它接收结构化 `RuntimeRunRequest`，围绕一个目标运行 agent loop，并沉淀完整审计结果。

它不是：

- HTTP 层
- backlog 队列层
- 领域模型层

它是：

- request-driven agent harness

## runtime 输入

runtime 的统一输入是 `RuntimeRunRequest`。

典型字段：

- `request_id`
- `source_type`
- `partition`
- `objective`
- `prompt`
- `context`
- `allowed_tools`
- `allowed_skills`
- `max_steps`
- `max_tool_calls`
- `max_skill_calls`
- `risk_level`

这些输入可以来自：

- backlog dispatch
- 手动 maintenance
- API 调用
- 定时任务

## runtime 输出

runtime 的统一输出是 `RuntimeRunResult`。

它包含：

- `run_id`
- `status`
- `final_summary`
- `reasoning_summary`
- `steps`
- `artifacts`
- `tool_results`
- `skill_results`

## 核心对象

### `RuntimeSession`

描述这次 run 的静态上下文：

- 当前 `AgentRun`
- 当前 `RuntimeRunRequest`

### `RuntimeLoopState`

描述 loop 过程中的运行状态：

- 已产出的 decisions
- 已执行的 tool / skill results
- applied actions
- failure messages
- response messages
- 当前 artifacts

### `RuntimeWorkingMemory`

描述提供给 agent 的工作记忆：

- facts
- observations

### `RuntimeTurnInput`

每轮传给 agent 的结构化输入：

- objective
- prompt
- context
- memory
- prior decisions
- budgets

### `RuntimeDecision`

agent 每轮输出的决策：

- `reasoning_summary`
- `actions`
- `should_stop`

### `RuntimeAction`

可执行原子动作：

- `tool_call`
- `skill_call`
- `respond`
- `stop`

## 主链路

```text
RuntimeRunRequest
  -> create AgentRun
  -> create RuntimeSession
  -> initialize RuntimeLoopState
  -> initialize RuntimeWorkingMemory
  -> loop:
       build RuntimeTurnInput
       agent.decide()
       persist decision step
       check termination
       execute actions
       update loop state
  -> build final summary
  -> persist final run
  -> return RuntimeRunResult
```

## 关键模块

### `service.py`

runtime 外部服务入口。

- 校验 partition
- 创建 `AgentRun`
- 初始化 engine
- 汇总最终结果

### `engine.py`

loop orchestrator。

负责驱动一轮又一轮：

- build context
- decide
- execute
- terminate

### `agent.py`

agent protocol 和当前默认 agent。

### `executor.py`

负责真实执行：

- step 持久化
- tool 调用
- skill 调用

### `action_executor.py`

负责把一轮 `RuntimeDecision` 编排成实际 action 执行。

### `memory.py`

负责：

- 初始 memory
- turn input memory snapshot
- reasoning summary
- final summary

### `termination.py`

负责 stop 判定：

- step budget
- tool budget
- skill budget
- no action
- explicit stop

## 和 backlog 的关系

关系很明确：

- `backlog` 负责组装 `RuntimeRunRequest`
- `runtime` 负责执行这个 request

也就是说：

```text
backlog = trigger + request compiler
runtime = loop executor + audit
```

## 和 skill / tool 的关系

### tool

用于只读观察。

### skill

用于副作用执行。

runtime 不直接把业务逻辑写死在 loop 里，而是通过 tool / skill 扩展能力。

## 后续演进方向

后续如果引入真正的 LLM agent loop，应继续沿着当前接口扩展：

- 替换或增强 `RuntimeAgentPort`
- 保留 `RuntimeRunRequest`
- 保留 `RuntimeDecision`
- 保留 `RuntimeAction`
- 保留 `RuntimeRunResult`

这样外部模块不需要跟着大改。

## 一句话总结

`runtime` 是 Knowbase 的 agent harness，负责把一次结构化任务请求执行成一条可审计的 run。 
