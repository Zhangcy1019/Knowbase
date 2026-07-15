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

## 目录结构

```text
internal/runtime/
  __init__.py
  contracts.py
  service.py
  core/
    state.py
    memory.py
    policy.py
    termination.py
  llm/
    decision_parser.py
    decisioning.py
    prompt_builder.py
  providers/
    openai_client.py
    openai_runtime_adapter.py
  loop/
    agent.py
    engine.py
    turn_planner.py
    planner_components.py
  actions/
    capability_executor.py
    action_runner.py
```

## 核心对象

### `RuntimeRunRequest`

一次 run 的静态任务定义。

### `RuntimeRunState`

一次 run 的动态运行状态：

- decisions
- tool / skill results
- applied actions
- failure messages
- response messages
- observations / facts
- artifacts

### `RuntimeTurnInput`

每轮传给 agent 的结构化视图：

- `task`
- `memory`
- `bounds`
- `progress`
- `hints`

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
  -> create RuntimeRunState
  -> loop:
       build RuntimeTurnInput
       agent.decide()
       persist decision step
       check termination
       execute actions
       update run state
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

### `loop/agent.py`

loop agent 外壳。

### `loop/turn_planner.py`

每轮 planner 入口。

### `llm/decisioning.py`

decision generator 的输出约束和 draft 归一化层。

当前默认使用 `DefaultRuntimeDecisionGenerator`，它已经打通：

- prompt builder
- model adapter
- decision parser
- decision normalizer

其中 `RuntimeDecisionDraft` 用于承接模型或生成器的候选决策，当前重点字段包括：

- `reasoning_summary`
- `action_plan_summary`
- `actions`
- `should_stop`
- `stop_reason`
- `requires_review`
- `review_reason`
- `notes`

其中 `RuntimeProposedAction` 也已收紧为更明确的 action draft 协议，当前重点约束包括：

- `kind` 只允许 `tool_call / skill_call / respond / stop`
- `summary` 必填
- `tool_call` 必须提供 `tool_id`
- `skill_call` 必须提供 `skill_id`
- `respond` 必须提供 `prompt`

当 stop evaluator 先判定本轮应结束时，generator 也会直接生成 stop decision，而不会继续调用模型。

### `llm/prompt_builder.py`

把 `RuntimePlannerContext` 转成模型输入。

### `providers/openai_runtime_adapter.py`

负责把 runtime prompt 适配到通用 OpenAI 风格接口，并返回结构化 payload。

### `providers/openai_client.py`

定义通用 OpenAI 风格 chat client 协议：

- `OpenAIChatRequest`
- `OpenAIChatResponse`
- `OpenAIClientPort`

当前默认实现使用官方 `openai` Python SDK，并通过应用配置注入：

- `llm.model`
- `llm.temperature`
- `llm.max_output_tokens`
- `llm.timeout_seconds`
- `llm.openai.api_key`
- `llm.openai.base_url`

### `llm/decision_parser.py`

把模型输出转成 `RuntimeDecisionDraft`。

当前 parser 期望模型侧先产出标准 payload，再映射到 draft：

- `RuntimeDecisionPayload`
- `RuntimeDecisionActionPayload`

这份 payload schema 现在集中定义在这里，供 prompt builder、model adapter 和 parser 共享：

- `RUNTIME_DECISION_PAYLOAD_JSON_SCHEMA`
- `build_runtime_decision_payload_schema()`

### `loop/planner_components.py`

planner 内部组件：

- observation assembly
- stop evaluation

### `actions/capability_executor.py`

负责真实执行：

- step 持久化
- tool 调用
- skill 调用

### `actions/action_runner.py`

负责把一轮 `RuntimeDecision` 编排成实际 action 执行。

### `core/memory.py`

负责：

- turn input snapshot
- reasoning summary
- final summary

### `core/termination.py`

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

## 当前主线

```text
service
  -> loop/engine.RuntimeLoopEngine
  -> loop/agent.RuntimeLoopAgent
  -> loop/turn_planner.RuntimeTurnPlanner
  -> loop/planner_components.*
  -> actions/action_runner.RuntimeActionRunner
  -> actions/capability_executor.RuntimeCapabilityExecutor
```

## 后续演进方向

- 在 `loop/planner_components.py` 中接入真正的 decision generator
- 把真实 LLM provider 接到 `providers/openai_runtime_adapter.py`
- 继续收敛 execution outcome 和 state update 边界

后续如果引入真正的 LLM agent loop，应继续沿着当前接口扩展：

- 替换或增强 `RuntimeAgentPort`
- 保留 `RuntimeRunRequest`
- 保留 `RuntimeDecision`
- 保留 `RuntimeAction`
- 保留 `RuntimeRunResult`

这样外部模块不需要跟着大改。

## 一句话总结

`runtime` 是 Knowbase 的 agent harness，负责把一次结构化任务请求执行成一条可审计的 run。 
