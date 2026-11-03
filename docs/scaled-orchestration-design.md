# 规模化编排：批量任务、结果汇总与寻优设计

状态：2026-11-03 更新。用户已确认**只做批量／并行执行（FEAT-049）**，FEAT-050 与 FEAT-051 暂缓，不进入本轮范围；第 7、8 章保留为后续设计素材，不代表已批准。

- FEAT-049 已实现，以第 6 章为准（2026-11-03 简化后的口径，替代此前较重的工作进程协议方案）。
- 实现见平台仓[批量执行使用说明](../sim-platform/docs/batch-execution.md)、[批量执行设计](../sim-platform/docs/batch-execution-design.md)，实测与未覆盖项见[测试验证报告](../sim-platform/docs/batch-execution-verification.md)。
- 本文其余内容仍为建议，未经确认前不构成公共约定。

本文对应协作清单中的三条：

| 编号 | 特性 | 本轮范围 | 清单归属 |
| --- | --- | --- | --- |
| FEAT-049 | 批量任务与多进程 worker | **已实现** | sim-platform |
| FEAT-050 | 寻优入口与搜索策略 | 暂缓（用户确认训练场景不做寻优） | sim-workspace |
| FEAT-051 | 批量汇总、对比和结果检索 | **已实现（索引与排行，简化为只读派生）** | sim-platform |


依据：`SIMPlatform｜需求与特性协作清单.xlsx`「需求与特性」表 C 列模块为「规模化编排」的三行（A50–A52），以及本仓 [AGENTS.md](../AGENTS.md)「推进顺序」中阶段 E「批量、资源隔离、寻优、汇总」。

## 1. 问题

单任务路径已经完整（`run_training` 一个任务、一个 `training.output_dir`、一份 `task.log`、一套 L1/统计产物），但它只回答了「一个配置跑出什么」。要把仿真用于方案比较，还缺三件互相依赖的事：

1. **怎么一次跑一批**：现在只能逐个手工调用 CLI，没有清单、没有并发、没有失败隔离，一次失败就得从头重来。
2. **怎么读回来比较**：产物分散在各任务目录，`training.json` 是给人看的，没有机器可读的批量索引，失败项会被自然丢掉。
3. **怎么找最优**：没有搜索空间描述、没有候选物化、没有目标与约束，只能人工拼配置试。

三者不是并列关系：**寻优需要批量执行，批量执行需要能读回结果**。这个依赖决定了实施顺序。

## 2. 适用范围与非目标

适用于单机、单用户、训练路径的批量评估与配置寻优。不覆盖：

- 跨机分发、集群调度、任务队列服务、多用户配额；
- 推理路径的批量入口（推理尚未实现首条链路，FEAT-074～079）；
- 动态优先级、抢占、资源超卖；
- 仿真内部的 L2 阶段调度和目标设备上的 rank 放置——本仓 [legacy-workload-model-platform-review.md](legacy-workload-model-platform-review.md) 已明确"仿真内部调度／设备放置／批量编排"三者不共用一个调度器，本文只做第三者；
- 结果数据库、Web 界面、交互式编辑。

## 3. 现状盘点

### 3.1 可直接复用

| 能力 | 位置 | 用途 |
| --- | --- | --- |
| 单任务入口 | [api/task.py](../sim-platform/src/sim_platform/api/task.py) 的 `run_training` | worker 内部唯一执行路径，不复制 |
| 配置加载与校验（不导入训练栈） | [config/task.py](../sim-platform/src/sim_platform/config/task.py) 的 `load_training_task` | 批量预检，非法配置不浪费捕获 |
| 覆盖语义 | 同上，`overrides` 点分键 | 批量注入输出目录、寻优注入候选参数 |
| 每任务独立日志会话 | [observability/logging.py](../sim-platform/src/sim_platform/observability/logging.py) 的 `task_logging` | 天然按进程隔离 |
| 可读产物 | [exports/statistics.py](../sim-platform/src/sim_platform/exports/statistics.py) 写 `training.json` 与 3 份 CSV | 批量索引的取数来源 |
| 结果对象 | [results/training.py](../sim-platform/src/sim_platform/results/training.py) 的 `TrainingResult` | 指标来源（`timing`、`statistics`、`utilization`） |
| 进程级默认配置 | [config/runtime.py](../sim-platform/src/sim_platform/config/runtime.py) 的 `global_args` | 每 worker 独立初始化 |

### 3.2 硬约束（决定了架构形态）

这三条不是风格偏好，是当前实现的物理限制，任何"同进程循环"的方案都会被它们否决：

- **FEAT-048**：`task_logging` 独占进程的 logging、warnings 与 Python stdio，同进程不并发、不嵌套；worker 必须独立目录。
- **FEAT-071**：Meta 捕获会话持有全局 patch／TLS／mesh／cache，并发或嵌套会话不支持；清单原文即"未来批量应采用独立 worker，不共享捕获全局状态"。
- **FEAT-009**：`global_args` 是进程级单例，单任务配置不可变快照。

**结论：进程就是隔离单元。** 一个进程同时只能跑一个训练任务。

### 3.3 一个必须提前说明的现实约束

当前真实 roofline 覆盖不足。以 `deepseek_v4_smoketest`（4 卡、EP=2、seq_len=128、selective AC）按静态分类估算：需预测 2032 个节点（vec 1702、cube 228、comm 63、mix 39），按现有模型类型估算可定价约 275 个（13.5%）。

2026-11-03 起平台改为[预测容错](../sim-platform/docs/prediction-tolerance.md)：缺模型或模型异常以零耗时继续 DES，覆盖计数写进结果，不再中断任务。因此约束**不再是"跑不出结果"，而是"结果只代表已建模部分"**。

同日拉取最新上游后实测更严峻：`success=0 / miss=2032 / fail=0`，端到端时延为 0，`utilization_unavailable` 报 "End-to-end latency is zero"。全部 miss 的错误都是同一句 `roofline: Unsupported attributes: ['input_tensor_bindings']`——训练仓在 `capture/operator_arguments.py` 把所有算子的参数名绑定写进节点属性，算子仓 `adaptors/_common.py` 的属性白名单还没接收它。这是跨仓契约待对齐项，不属于批量特性，当前仍未解决。

对三条需求的影响：

- 批量可以正常跑通，`ok` 与 `failed` 只反映任务是否完成，不反映覆盖高低；
- 汇总与排行已按"零时延不参与排行"实现（见第 7.3 节），所以当前跑出来的批次会显示"无可排行任务"而不是伪造第一二名；
- 寻优暂缓：在 0 覆盖状态下即便有搜索器，目标函数也全是 `null`，选不出任何候选。

本文不把"覆盖不足"当作不做的理由，但**不允许**把"跑完 60 个候选"写成寻优可用（对应 FEAT-023 与清单 K24 的口径要求）。

## 4. 方案思想

三条原则贯穿全文：

1. **进程即隔离单元。** 一个任务一个进程；批量层不共享任何全局状态，不依赖父进程的 Python 对象。
2. **不造第二套执行路径。** worker 就是既有的单任务 CLI，批量层只读配置、起进程、收状态，不复刻评估逻辑，也不需要 worker 协议。
3. **产物即接口。** 任务之间只通过目录约定和 JSON 通信。跨进程传 `TrainingResult` 会让编排层被迫导入训练栈，也让结果无法被事后审计。

清单里 FEAT-049 的「单任务 API 可供上层调用」就是第 2 条的意思：地基已经够用，上面只加调度。

## 5. 总体结构

```text
            ┌──────────────────────────────────────────────┐
            │ sim-platform batch CLI                       │
            │ （编排进程：不导入 torch，不做仿真）          │
            └───────────────┬──────────────────────────────┘
                            │ 读清单 → 预检 → 派发
                            ▼
            ┌──────────────────────────────────────────────┐
            │ 调度器：线程池 + 超时 + 重试 + 恢复            │
            └───────────────┬──────────────────────────────┘
                            │ subprocess（每任务一个）
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │sim-platform  │   │sim-platform  │   │sim-platform  │
   │   train      │   │   train      │   │   train      │
   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
          │                  │                  │
          ▼                  ▼                  ▼
   <batch>/<task>/{task.log, worker.log, l1/}
                            │
                            ▼
            ┌──────────────────────────────────────────────┐
            │ batch.json：状态、尝试次数、错误、输出目录     │
            └──────────────────────────────────────────────┘
```

三者关系：**049 产出目录与状态 → 051 把目录读成索引 → 050 用索引驱动下一轮候选**。本轮只做最左段。

## 6. FEAT-049 批量任务与多进程 worker（已实现）

本节是 2026-11-03 简化后的口径，替代此前「独立 worker 模块 + `plan.json` + `status.json` 状态机」的方案。实现与验证记录见平台仓[批量执行](../sim-platform/docs/batch-execution.md)与[测试验证报告](../sim-platform/docs/batch-execution-verification.md)。

### 6.1 分层收缩为两层

| 层 | 职责 | 约束 |
| --- | --- | --- |
| 清单层 | 解析并校验清单，产出台账 | 纯配置，不导入 torch |
| 调度层 | 预检、派发子进程、并发、超时、重试、恢复、写 `batch.json` | 只依赖标准库 |

没有独立 worker 层：worker 就是既有的 `sim-platform train`。因此不需要 worker 协议、`plan.json` 或每任务 `status.json`，也不需要另建一条执行路径。

### 6.2 清单只引用任务文件

```toml
schema_version = 1
batch_id = "smoke-20261103"         # 可选，默认取文件名
output_dir = "../runs/batch-smoke"  # 相对清单目录

[execution]
max_workers = 3         # 可选，默认 min(4, CPU 数, 任务数)
timeout_seconds = 1800  # 可选，单次尝试的墙钟上限
retry = 0               # 可选，补充尝试次数

[[task]]
id = "seq128-lbs1"
config = "../sim-platform/examples/training.toml"

[[task]]
id = "seq256-lbs2"
config = "../sim-platform/examples/training.toml"
```

与草案的差别：**不再支持 `[task.overrides]`**。清单只引用已存在的任务文件，参数变化由调用方先生成任务文件（寻优候选本来就要物化成文件）。这样批量层不必把 TOML 值再序列化回 `--set`，也就没有引号与转义风险。

校验规则：`schema_version` 必须为 1；`id` 唯一、只允许 `[A-Za-z0-9._-]`、不得为 `.`／`..`（它直接作为输出目录名）；`config` 必须存在，相对清单所在目录解析；未知清单键、`execution` 键、`task` 键一律报错。

### 6.3 目录契约

```text
<batch.output_dir>/
  batch.json    # 唯一汇总产物，父进程写
  <task_id>/
    worker.log  # 子进程 stdout/stderr，批量层追加
    task.log    # 单任务日志（既有行为）
    l1/         # 单任务导出（成功时）
```

`batch.json` 在每次任务完成后重写，因此中断也留下可用报告；`l1/statistics/` 沿用现有布局（`exports.directory` 默认派生为 `training.output_dir/l1`），本文不借机调整。

### 6.4 输出目录接管

批量层通过 `train --output-dir` 注入 `training.output_dir`，任务目录固定为 `<output_dir>/<task_id>`。这是本特性唯一的必改点：不接管的话，并发任务会互相覆盖 `task.log`、`l1/` 与统计产物，属于静默错误。

来源语义按已确认口径：批量注入记为**显式覆盖**（`source = "override"`），不新增第五种来源枚举，也不改变 `--show-config` 的稳定输出。

### 6.5 调度行为

```text
preflight:
  for task in tasks:
      load_training_task(task.config)     # 不导入训练栈
      失败 → invalid：不派发、不重试
execute:
  resume: 上次 batch.json 中为 ok 的跳过（--force 关闭该行为）
  ThreadPoolExecutor(max_workers)，每个任务一次 subprocess：
      python -m sim_platform train <config> --output-dir <output_dir>/<id>
      0.2 s 轮询等待；超时 kill；中断置 stop 标记并 kill
  每完成一个任务重写 batch.json
exit: 0 全 ok ／ 1 存在失败 ／ 2 清单或参数非法 ／ 130 中断
```

实现取舍：用 `subprocess` 加线程池，而不是 `ProcessPoolExecutor`（崩溃、超时、stdio 分离都要自己控），但也不自建 watcher 线程与队列——线程池的每个槽位就阻塞在一次 `Popen.wait` 轮询上，超时与中断由同一个 `Event` 驱动。

### 6.6 状态

| 状态 | 含义 | 起进程 | 重试 |
| --- | --- | --- | --- |
| `ok` | 退出码 0 | 是 | — |
| `failed` | 退出码非 0 | 是 | 是 |
| `timeout` | 超过 `timeout_seconds` 被 kill | 是 | 是 |
| `cancelled` | 批次被中断 | 视情况 | 否 |
| `invalid` | 预检失败 | 否 | 否 |

相比草案去掉了 `pending`、`spawn_error`、`crashed`：`pending` 不需要落盘（父进程内存即状态）；在既定判据下，起不来与崩溃都表现为非零退出或超时，单独枚举没有额外信息。保留 `invalid` 与 `failed` 的区分，因为「配置错」与「跑挂了」的处理方式不同。

### 6.7 重试与恢复

- 重试在同一输出目录内进行，`attempts` 记录每次的退出码与耗时。**与草案的差别**：不建 `run-1/run-2`。逐次保留目录的价值依赖 051 的对比能力，等 051 立项时再定。
- 恢复读 `batch.json`：`ok` 的跳过，其余补跑；重入同一条命令即可继续，不需要额外子命令。
- 成功判据：**只判退出码 0**。草案曾要求「且 `training.json` 可解析」，但 `exports.enabled=false` 是合法配置，产物不存在不等于失败。

### 6.8 已知限制

- 真实训练图预测覆盖不完整，但任务不因此失败：miss／fail 节点按零耗时继续 DES，覆盖计数在 `training.json` 的 `results.prediction_coverage`。批量层只判退出码，不解释覆盖高低。
- `batch.json` 不聚合指标与覆盖，只有状态、尝试次数与错误；跨任务对比属于暂缓的 051。
- 退出码 2 同时表示「输入非法」和「运行期异常」，区分只能读 `worker.log`。若将来需要按类统计失败率，应在 `train` 上区分退出码，而不是让批量层猜。
- 超时只结束直接子进程；当前任务进程不再派生进程。

## 7. FEAT-051 批量汇总、对比与检索

> 已实现，口径见本节与平台[批量执行设计](../sim-platform/docs/batch-execution-design.md)第 10 章。实现与原设计的差别：索引默认不落盘（`--save` 才写）、检索只做等值过滤、新增"零时延不参与排行"的有效性门槛。

### 7.1 定位

只读层：不重算指标、不重新捕获、不修改任务目录。索引是派生产物，删掉可重建。

### 7.2 索引字段

`batch_index.json`（机器读）与 `index.csv`（人读）双写，与现有 `exports` 的双格式习惯一致。

| 字段 | 来源 | 缺失时 |
| --- | --- | --- |
| `task_id` / `final_status` / `attempt` / `wall_seconds` | `batch.json` | 必填 |
| `synthetic` | `TrainingResult.synthetic` 落到 `training.json` | 必填，无法判定时按 `true` 保守处理并告警 |
| `estimated_duration_us` | `timing.final_duration_us` | `null` + reason |
| `statistics_duration_us` | 同上，统计口径分母 | `null` |
| `tokens_per_second_per_device` | `training.json` | 已有 null 语义，沿用 |
| `mfu` / `hfu` / `mbu` | `training.json` 利用率段 | `null` + `unavailable_reasons` |
| `hardware` / `backends` | 配置段 | 必填 |
| `config_fingerprint` | 生效配置的稳定摘要 | 必填 |
| `artifacts` | 任务目录相对路径 | 必填 |
| `error` | `batch.json` | 成功时为空 |

索引本身带 `schema_version`，读取未知版本显式拒绝。

### 7.3 可比性规则（本层最容易被做错的地方）

排行榜必须分组，否则会得出错误结论：

- **`synthetic` 与真实预测不得混排。** 默认从排行中排除 synthetic，`--include-synthetic` 显式纳入并在输出中标注。
- **不同 `hardware` 不得混排**：`--group-by hardware` 为默认分组键之一。
- **不同 `backends` 组合不得混排**（roofline 与 roofline+其他 的耗时不可比）。
- 失败的候选**不进排行**，但必须出现在失败清单里；"没有结果"不能被当作"结果差"参与比较。
- **零时延不参与排行**（实现时补充）：预测全 miss 时 `end_to_end_us=0`，若直接排序会把"没算出来"排成第一名，因此这类任务只登记原因、不参与排序。
- 跨 `schema_version` 的索引不做自动合并。

### 7.4 命令

```bash
sim-platform batch report <batch_dir>                     # 全量表
sim-platform batch report <batch_dir> --sort mfu --top 10
sim-platform batch report <batch_dir> --only failed       # 失败追踪
sim-platform batch report <batch_dir> --group-by hardware
sim-platform batch report <batch_dir> --format csv        # 导出
sim-platform batch report <batch_dir> --save              # 落 batch_index.json + index.csv
```

检索首期只支持**固定字段等值过滤**（`--where seq_len=256`），不做表达式引擎或 DSL。理由：一旦开放表达式，语法、类型、错误提示都会变成需要长期维护的公共契约，收益与成本不匹配。

## 8. FEAT-050 寻优入口与搜索策略

### 8.1 定位

寻优 = **候选生成** + 复用 049 执行 + 用 051 读数。它不是第四条执行路径，自身不包含仿真逻辑。

### 8.2 归属（未决，见 11.2）

清单把本项归到 `sim-workspace`，但候选执行必须调用平台的 `run_training`。建议：**搜索口径、目标定义、约束语义写在本仓文档，实现代码落在 sim-platform**，避免管理仓反向依赖平台。

### 8.3 搜索描述

```toml
schema_version = 1
sweep_id = "mbs-seq-tradeoff"
base_config = "../sim-platform/examples/training.toml"
output_dir = "../runs/sweep-20261103"

[sweep]
strategy = "grid"                       # grid | random | grid_then_random
seed = 0
objective = { metric = "tokens_per_second_per_device", direction = "max" }
budget = { max_candidates = 60, max_wall_seconds = 3600 }
constraints = ["static_memory.peak_bytes <= 3.4e9"]

[sweep.space]
"training.local_batch_size" = [1, 2, 4]
"training.seq_len" = [128, 256]
"training.model_overrides.n_layers" = [2, 3]
```

校验规则：`space` 的键必须是 `base_config` 可接受的覆盖键；候选值必须是标量或同类型列表；笛卡尔积超过 `max_candidates` 时按策略截断并**显式记录被截断**（不静默丢弃）。

### 8.4 候选物化

每个候选落成一份**完整 TOML**：`<output_dir>/candidates/<序号>-<slug>.toml`，内容是 base 配置叠加本次覆盖后的生效值。

理由：候选必须能脱离寻优器独立重跑、能被 review、能进版本对比。只存"参数组合"会让复现依赖寻优器本身。

随后生成等价于 6.2 的批量清单指向这些候选，交给 `batch run`。

### 8.5 策略与预算

| 策略 | 行为 | 适用 |
| --- | --- | --- |
| `grid` | 空间笛卡尔积，按稳定顺序枚举 | 小空间、需要完整对照表 |
| `random` | 用 `seed` 做可复现的均匀采样，不重复 | 空间大于预算 |
| `grid_then_random` | 先网格覆盖边界，再随机填充剩余预算 | 首期推荐默认 |

**首期不做贝叶斯优化／进化算法。** 单次评估在十秒到分钟级，一次 sweep 只有几十个样本，代理模型学不到稳定结构，反而引入"搜索器比仿真更不可解释"的问题。等真实预测覆盖与单任务耗时稳定后再评估。

### 8.6 目标与约束

- 目标指标取自索引，方向 `max`/`min`；指标为 `null` 的候选不参与排序，计入"无有效目标"清单。
- 约束分两类，**必须区分**：
  - **可预检约束**（配置层面的非法组合）：派发前剪枝，成本为零；
  - **需仿真约束**（如静态显存峰值）：只能在结果出来后事后过滤，不能当剪枝用，否则会得出"约束从未违反"的假象。
- 约束违反者保留在结果中并标记 `violated`，不删除——否则无法回答"为什么最优候选不在候选集里"。

### 8.7 闭环

```text
sweep 描述 → 生成候选 TOML → 生成批量清单 → batch run
           → 索引 → 目标求值 + 约束标记 → 排行
           → （可选）下一轮：以当前最优邻域生成新候选
```

首期只做单轮；多轮迭代与早停留作扩展，但候选与索引格式已经支持。

## 9. 数据契约与版本化

本轮只有两份带 `schema_version` 的产物（草案中的 `plan.json`、`status.json` 随 6.1 的分层收缩取消）：

| 产物 | 位置 | 写入者 | 读取者 |
| --- | --- | --- | --- |
| 批量清单 | 用户指定 | 用户／寻优器 | 调度器 |
| `batch.json` | `<batch>/` | 调度器 | 用户、resume、未来的 051 索引器 |

规则与平台现有快照策略一致（[workload-snapshots.md](../sim-platform/docs/workload-snapshots.md) 的 v6 做法）：**未知版本显式拒绝，不猜测、不兼容性降级**。字段只增不改；语义变化必须升版本并在本文件记录替代关系。

## 10. 关键设计决策

| 决策 | 选择 | 被否决的替代 | 理由 |
| --- | --- | --- | --- |
| 隔离模型 | 每任务独立子进程 | 同进程串行／线程 | 捕获会话、日志会话、`global_args` 三重进程级状态 |
| 进程 API | `subprocess` + 线程池 | `ProcessPoolExecutor` | 崩溃污染、超时难杀、stdio 无法按任务分离 |
| worker 载体 | 既有 `sim-platform train` | 独立 worker 模块＋`plan.json` | 不需要第二套执行路径与状态协议 |
| 编排层依赖 | 不导入 torch | 直接调 `run_training` | 预检也不能导入训练栈 |
| 重试语义 | 同目录重跑，记 `attempts` | 新 attempt 目录 | 逐次留产物依赖 051 的对比能力，051 未立项 |
| 成功判据 | 退出码 0 | 退出码 + 产物可读 | `exports.enabled=false` 是合法配置 |
| 索引存储 | `batch.json` | JSON + CSV／数据库 | 051 暂缓，先只留必要状态 |
| 搜索策略 | 网格／随机（暂缓） | 贝叶斯／进化 | 样本量不足，可解释性优先 |
| 可比性 | 按 synthetic／hardware／backends 分组（暂缓） | 单一全局排行 | 混排会直接产生错误结论 |

## 11. 未决问题

FEAT-049 范围已由用户确认并按第 6 章实现；下列 11.1、11.4、11.5 已按简化口径落地，仅保留记录。11.2、11.3 随 FEAT-050 一起暂缓。

### 11.1 重试语义（已定）

同目录重跑并记录 `attempts`，不建 `run-n/` 目录（见 6.7）。

### 11.2 FEAT-050 的实现归属（暂缓）

清单写 `sim-workspace`。建议拆分：需求与搜索口径写入本仓文档，代码落在 `sim-platform`。

### 11.3 FEAT-050 的首期验收口径（暂缓）

三个选项，影响未来 M3 的验收定义：

- A. 用 synthetic 后端验证闭环正确性（能跑通、能选出"最优"、证据链完整），不宣称性能结论；
- B. 圈定已覆盖的 matmul 子集，用真实预测验证；
- C. 先补 vec 覆盖（需预测节点中 vec 占 84%），再做寻优验收。

建议 A 或 B 作为寻优验收，C 作为并行工作项，不与本设计耦合。

### 11.4 批量注入输出目录的来源标注（已定）

记为显式覆盖，不新增第五种来源（见 6.4）。

### 11.5 并发默认值（已定）

`min(4, cpu_count, 任务数)`，可用 `--max-workers` 覆盖。内存限流不实现。

## 12. 分阶段计划与验收

| 阶段 | 范围 | 状态 |
| --- | --- | --- |
| M1 | 清单解析 + 目录契约 + 进程调度 + 状态 + 重试／恢复 | **已完成**。验收：① 多任务 `max_workers` 限制下目录互不覆盖；② 预检失败不派发、其余任务照常；③ 重入同命令只补未成功项；④ 超时任务被 kill 且不影响同批。系统测试 `tests/system/test_batch_capture.py` 用两个真实任务并发验证：约 15 s 内两个任务均 `ok`，各自目录含 `task.log`、`worker.log` 与 `l1/` |
| M2 | 索引 + 排行 + 失败追踪 + 可比性分组 | **已完成**。验收：① 非 `ok` 与非正时延任务不进排行且给出原因；② synthetic 默认排除；③ `hardware`／`backends` 分组不混排；④ 失败项保留在 `index.csv` 与 `not ranked` 清单；⑤ 索引带 `schema_version`，未知版本拒读。13 个单元用例 + 真实批次验证 |
| M3 | 搜索空间解析 + 候选物化 + 接批量 + 目标／约束／预算 | 暂缓（FEAT-050，用户确认训练场景不做寻优） |

M2 依赖 M1 产物，M3 依赖 M1 与 M2。M2 已用手写目录夹具做单元测试，不依赖真实捕获。

## 13. 测试策略

按平台现有分层（单元／模块／系统）与 `RUN_TRAINING_SYSTEM=1` 门禁。M1 实际落地：

| 层 | 覆盖 | 现状 |
| --- | --- | --- |
| 单元 | 清单解析与校验（版本、id 规则、重复、缺失文件、未知键）、CLI 分发与 `--output-dir` 覆盖 | 已实现，`tests/unit/batch/` |
| 单元 | 索引字段、缺失原因、零时延门槛、synthetic 排除、排序方向、分组、过滤、CSV、`--save`、版本拒读 | 已实现，`tests/unit/batch/test_report.py` |
| 模块 | 注入假命令验证并发重叠、失败隔离、预检拦截、超时 kill、resume 与 `--force` | 已实现，`tests/integration/test_batch_runner.py` |
| 系统（opt-in） | 2 个真实任务并发跑通，检查目录隔离、`batch.json`、`training.json` 覆盖字段 | 已实现，`tests/system/test_batch_capture.py`，随 `RUN_TRAINING_SYSTEM=1` 门禁 |


不允许用"能跑"代替断言：超时、重试、恢复、排行资格四条必须有可判定的断言，而不是看日志。

## 14. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 真实 roofline 覆盖 13.5% | 结果只代表已建模部分，容易被当成完整性能 | 覆盖计数进 `training.json`；`batch.json` 不聚合指标，避免误读；文档写明当前覆盖现状 |
| 单任务捕获内存 GiB 级 | `max_workers` 过大导致 OOM | 默认 `min(4, cpu_count, 任务数)`；不做全局配额，需要时手工降低并发 |
| 中断恢复不幂等 | 重复写同一目录导致结果混杂 | 成功项按 `batch.json` 跳过，永不重跑；未成功项重跑会覆盖自己的 `l1/`，日志追加保留 |
| 长时间无人值守运行 | 单个挂起任务拖垮整批 | `timeout_seconds` 默认 1800，超时 kill 并记 `timeout` |
| 退出码含义重叠 | 输入非法与运行期异常都是 2，无法按类统计 | 已记录为已知限制（6.8）；需要时在 `train` 上拆分退出码 |

## 15. 与需求条目的映射

| 需求 | 本文对应 | 关系 |
| --- | --- | --- |
| FEAT-049 | 第 6 章 | 主体，已实现 |
| FEAT-050 | 第 8 章 | 暂缓 |
| FEAT-051 | 第 7 章 | 暂缓 |
| FEAT-007 | 6.4 | 覆盖语义沿用，不新增来源枚举 |
| FEAT-009 | 6.5 | 每任务独立进程内初始化 `global_args` |
| FEAT-023 | 3.3、14 | 覆盖不足是验收口径前提 |
| FEAT-039／040／041 | 7.2 | 指标字段与 null 口径沿用（051 暂缓） |
| FEAT-046 | 7.2 | 索引从 `training.json` 取数（051 暂缓） |
| FEAT-048 | 3.2、6.5 | 日志会话按进程隔离 |
| FEAT-071 | 3.2 | 捕获不可并发，是进程模型的主要依据 |

## 附录 A：产物示例

`batch.json`（实际格式，见平台[批量执行](../sim-platform/docs/batch-execution.md)）：

```json
{
  "schema_version": 1,
  "batch_id": "smoke-20261103",
  "manifest": "/abs/path/batch.toml",
  "started_at": "2026-11-03T09:00:00+08:00",
  "ended_at": "2026-11-03T09:04:12+08:00",
  "interrupted": false,
  "execution": {"max_workers": 3, "timeout_seconds": 1800, "retry": 1},
  "tasks": [
    {
      "task_id": "seq128-lbs1",
      "status": "failed",
      "reused": false,
      "error": "exit code 2",
      "output_dir": "/abs/runs/batch-smoke/seq128-lbs1",
      "attempts": [{"attempt": 1, "exit_code": 2, "wall_seconds": 14.175}]
    }
  ]
}
```

索引的实际字段与落盘格式以平台[批量执行使用说明](../sim-platform/docs/batch-execution.md)第 4 章为准；
第 7.2 节保留设计意图（例如 `statistics_duration_us`、`config_fingerprint` 的取舍理由）。

## 附录 B：与既有文档的关系

- 本文不替代 [AGENTS.md](../AGENTS.md)「推进顺序」中的阶段 E，只是它的具体化；
- 本文不改变单任务入口语义；[training-task-entrypoint.md](../sim-platform/docs/training-task-entrypoint.md) 已同步更新为「多任务由批量层以独立进程组织」；
- 实现细节（模块划分、命令参数、状态与目录契约）以 `sim-platform/docs/batch-execution.md`（用法）与 `batch-execution-design.md`（设计与取舍）为准，本文件只保留跨仓口径与决策记录。
