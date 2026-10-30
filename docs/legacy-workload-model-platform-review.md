# 旧 workload-model-platform 源码分析

分析日期：2026-10-30。源码基线：`ZhanluModelSim/workload-model-platform`，提交 `74210ed88c8685181a8ca8b4f46ed10bc4888c07`。本轮临时克隆并静态阅读，没有安装依赖、运行测试或验证硬件精度，没有修改旧仓或业务仓。

本文是历史实现调查和需求讨论材料，不是新接口约定。当前已确认事项仍以 [AGENTS.md](../AGENTS.md) 为准；尤其不以旧仓的推理实现替代尚未提供的推理需求。

## 核心判断

旧仓最有参考价值的是完整的评估流程：取得负载、加工表示、配置硬件、预测算子、执行仿真、解释指标，再批量比较候选方案。它能帮助检查当前模块是否遗漏，但不能直接视为可迁移的完整后端。

目录、数据类、配置字段、真实执行能力必须分别判断。例如，存在 TP/PP 配置不表示计算图已经分片，修改流水线名称不表示实际重排了执行；存在部署描述不表示实现了 continuous batching。

## 实际调用链

- `api.capture()` 在捕获上下文里调用一次 `model(sample_input)`，不会自动补 loss、backward、optimizer；捕获器默认组装单设备实例，并将负载类型设为 inference。[API](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/api.py#L6)、[捕获组装](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/capture/orchestrator.py#L89)。因此不能把它当作已完成的训练／推理统一入口。
- `api.analyze()` 实际串联 Capture → Simulate → TCO；`compose()` 是另一个入口，未自动接入这条链。[调用链](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/api.py#L64)。
- `predict()` 和 `sweep()` 复用 `run_trial()`：捕获缓存 → 深拷贝 → 配置编辑 → 静态剪枝 → rank 映射 → 仿真 → 费用与指标 → 结果约束。单点失败以 error 保留，约束不满足以 rejected 保留。[单点评估](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sweep/runner.py#L344)。这比直接借用其统一 TrialSpec 更值得参考。
- 核心 API 已经传递 Python 对象，文件是部分配置和报告的载体。我们允许内存对象交付的决定与这条链兼容，不必先建设文件交换或独立 worker。
- 旧仓虽定义 `SchedulePlan`，仿真入口实际消费 `iteration.schedule`，未接入该 plan。执行是同一个 DES 内按实例展开算子，不能据此宣称已实现“L1 阶段结果交给独立 L2 引擎”的完整分层。[引擎入口](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sim/engine.py#L270)。

## 模块与当前职责的对应

以下是分析建议，未新增仓库或冻结接口。

| 旧仓模块 | 主要内容 | 当前适合的归属 |
| --- | --- | --- |
| `capture/`、框架 adapters | 执行入口、捕获、阶段识别、框架适配 | 训练与推理发生器分别维护；平台只做交付件适配 |
| `core/`、`graph_pass/` | 算子、阶段模板、阶段实例、依赖、图处理 | 发生器保留源表达；平台维护公共 G 和必要转换，不能整体搬入公共契约 |
| `sim/perf_*`、部分 `sim/models/` | 算子耗时估计、模型选择与回退 | 预测模型归 operator-performance-models；平台负责调用、缓存及来源记录 |
| `sim/catalog`、topology、server、device_resource | 硬件配置、设备资源、拓扑 | 平台需要明确建模；预测侧消费所需硬件特征，具体边界待设计 |
| `sim/engine`、network、collective、memory_tracker | 执行依赖、资源占用、通信、内存、时间线 | sim-platform 的 DES 与相关模型；通信耗时预测和资源仲裁应分开讨论 |
| `sim/result`、inference_metrics、`viz/` | 结果、指标、时间线与解释 | 平台公共结果能力，加训练／推理各自的指标语义 |
| `sweep/`、部分 `sched/` | 单点复用、搜索、剪枝、映射、比较 | 平台后续批量评估能力；最小链路不必全做 |
| `editor/` | 参数与结构修改、修改历史 | 平台未来 what-if／修正能力的参考，不能只改字段就宣称行为已改变 |
| `cost/` | 设备费用、能耗、财务 TCO | 可选评估扩展；不是算子性能预测仓的职责 |

## 最需要避免的误判

1. **并行配置不等于并行仿真。** sweep 自身明确记录：未按 TP/PP/DP 切分算子 FLOPs，常规实例落到第一台设备，缺少捕获通信时也不会凭配置补出通信；并行度主要影响映射、通信组和费用。[源码限制说明](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sweep/runner.py#L264)。依赖驱动路径另有多设备算子轮转分配，但不强制模板内算子依赖，多设备实例也跳过容量跟踪，不能把它视为真实 TP。[实际派发](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sim/engine.py#L504)。
2. **DES 框架不等于执行语义完整。** 实际使用 salabim；每设备计算主要由一个 FIFO 消费进程执行，搬移和网络另行调度。单设备路径处理部分依赖，但不能因此认为保留了真实 stream/event 与所有资源争用。[设备进程](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sim/components/device.py#L23)、[派发规则](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sim/engine.py#L305)。
3. **调度策略字符串不等于 L2 展开。** `change_pipeline_schedule()` 实际更新字符串并记录历史，没有重建阶段顺序；`change_parallelism()` 也主要更新字段。[编辑实现](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/editor/schedule_editor.py#L27)。当前训练仍应按已确认的 L2 方向设计 `(F → B) × GA → O`，验证阶段边界、实例身份和通信归属。
4. **组合对象不等于完成集群放置。** `MultiGraphComposer` 汇集已有实例设备归属及 sharing mode，没有落实 candidate 的完整 placement／parallelism。[组合实现](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sched/composer.py#L19)。
5. **缓存只能在适用假设下复用。** 旧捕获缓存键只有 model、batch_size、seq_len、mode。[缓存键](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sweep/spec.py#L87)。真实训练中的并行策略、重算等会改变捕获结果，不能沿用“与并行度无关”的假设；捕获缓存与算子预测缓存也应分别设计。
6. **指标名称不代表统计口径可靠。** 旧引擎吞吐计算把 microbatch_count 当成样本数量，并假设单迭代可按次数外推。[吞吐实现](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sim/engine.py#L1256)。我们需要区分 microbatch 数、每批样本数、token 数、迭代时长和端到端时长，保留计算依据。

这些是迁移评估的限制，不是要求本轮修复旧仓的 bug 清单。

## 对当前需求梳理的启示

最小链路需要的核心不是只有“负载图 + 耗时预测 + 总时间”。至少还需明确以下责任，但不必立即规定数据类和字段：

- **输入事实与适配**：保留来源、节点身份、捕获配置和缺失信息；训练继续使用有意限定的 FSDP 通信视图。
- **硬件和执行环境**：设备能力、通信拓扑与资源容量的口径，要使预测和 DES 对同一目标的理解一致。
- **耗时与执行约束**：预测给出耗时依据；DES 决定依赖、资源占用和重叠，不能简单累计算子耗时。
- **模板与实例组织**：L1 推演单图，L2 负责阶段实例和跨阶段依赖；重复模板不意味着可以忽略跨实例状态。
- **结果与可信范围**：时间线、统计范围、未知算子、回退、近似和版本来源要能解释最终数字。具体显存指标受发生器交付范围约束，不能凭缺失数据补造。
- **可重复的单次评估**：同一条负载路径先能稳定完成一次评估，再让批量入口调用它。训练／推理可以各有单次评估入口，不要求统一 TaskSpec 或继承体系。

应区分三种“调度”：仿真内部的 L2 阶段调度、目标设备上的 rank／集群放置、运行仿真任务的批量编排。三者影响不同层面，也不必共用一个 Scheduler 类。

## 推理、批量与扩展的状态

旧仓推理部署路径包含请求到达、角色副本、prefill/decode 和逐 token 实例展开，可以作为未来复杂场景的参考。[部署展开](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/workload/sim/deployment.py)。这些历史选择不意味着当前必须支持服务级仿真。

其 decode 重复同一模板，`batch_policy` 仅作声明，没有动态批组成；这也说明“有推理部署配置”和“实现真实服务策略”是两回事。[旧仓明确的近似范围](https://github.com/ZhanluModelSim/workload-model-platform/blob/74210ed88c8685181a8ca8b4f46ed10bc4888c07/docs/usage/06-inference-serving.md#L153)。

我们仍保留单步评估、代表 decode 图／平均耗时乘 N、多图逐步仿真等可能性，等待推理资料明确。逻辑共享可以先发生在算子预测、单图执行和结果来源管理层；请求指标和训练迭代指标不必强行统一。

批量寻优、集群共享、财务 TCO、交互式编辑、复杂推理服务行为作为后续候选能力。旧仓提供问题清单与场景素材，不据此扩大当前最小交付范围。

下一步建议仍是讨论训练最小链路的输入事实、硬件目标、L1/L2 边界和输出口径，用一个真实小案例检验；推理接口继续留待真实资料，暂不开发或迁移旧仓代码。
