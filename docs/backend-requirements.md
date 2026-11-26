# 跨仓职责与协作边界

本页保留当前跨仓分工及共同约束，不重复组件内部的字段、公式、配置或测试记录。文件沿用旧名称以保持引用稳定；早期后端讨论、窗口卸载方案和阶段性状态已由当前职责替代，历史可从 Git 追溯。

## 从负载到结果的责任交接

| 环节 | 负责仓库 | 边界与实现入口 |
| --- | --- | --- |
| 用户入口与任务服务 | sim-portal | 账号、草稿、排队、整任务分发、Worker 生命周期与产物展示；不参与仿真计算，见[Portal 架构](../sim-portal/docs/architecture.md) |
| 训练负载 | torchtitan-npu-simulator | 模型、框架适配、预热/捕获、FSDP 通信视图、卸载计划和静态显存；见[训练架构](../torchtitan-npu-simulator/experiments/simulator/docs/architecture.md) |
| 推理负载 | inference-models-simulator | 模型表达、输入/状态、图调用计划、捕获及内存；已接平台独立入口，见[运行指南](../inference-models-simulator/docs/模型仿真运行指南.md)和[平台推理入口](../sim-platform/docs/usage/inference-task-entrypoint.md) |
| 公共适配 | sim-platform | 归一负载、来源和静态内存，校验依赖及语义，不重新实现模型；见[公共负载结构](../sim-platform/docs/design/training-api-and-l1-schema.md) |
| 算子预测 | operator-performance-models | 语义解析、模型注册、公式、预测明细与后端协议；见[预测设计](../operator-performance-models/docs/roofline-design.md) |
| 硬件与执行 | sim-platform | 用户硬件配置、调用/缓存、执行资源、L1、L2、修正和时延汇总；见[平台架构](../sim-platform/docs/architecture.md) |
| 统计与产品输出 | sim-platform | 配置来源、日志、指标、报告与集成验收；见[训练统计](../sim-platform/docs/design/training-statistics.md)和[开发验证](../sim-platform/docs/development/development-status.md) |

训练与推理的公共性首先是职责和可复用能力，不强制相同参数空间、TaskSpec、provider 父类或捕获实现。推理侧决定执行哪些图、次数、数据/状态绑定和分支；平台决定资源上的时序，不重新推断 draft/verify、KV 更新等模型行为。平台当前训练 Workload/入口不代表推理契约已经冻结。

SIMPortal 位于仿真链路外侧，不参与计算：它管身份、草稿、排队、整任务分发、Worker 生命周期与产物展示，仿真一律经平台公共入口执行。依赖方向为 portal → 平台 → 组件，平台不反向导入 portal；门户不复制模型注册表、不拆候选跨机器、不重算时延/显存/寻优判定，slot 也不等于模拟设备数，Meta/synthetic 或部分预测不能当作可行性或精度证明。当前已完成范围与最小交付边界见[Portal 实施计划](../sim-portal/docs/implementation-plan.md)。

当前串行分块 prefill 是平台展开请求并推进 KV 起点的已有特例，见[调用计划实现](../sim-platform/docs/design/inference-call-plan.md)。它与上述计划归属仍需收敛，见[待办](roadmap.md)；本次状态校正不迁移实现，也不将该特例推广为其他模型调用计划的职责规则。

## 负载事实的交付

- 允许同进程 Python 对象传递，文件导出不作为负载交付前提。训练默认不强制落盘内存，平台结果直接消费返回对象。
- 保持训练 FSDP 通信视图；完整源图可审计，但不自动纳入性能计算。源通信与事件不得重复计费，通信组/rank 顺序和依赖必须保留。
- 原始事实与预测分离：不消费旧 cost、外部 FLOPs/调试峰值或不可信的通信字节估算。原始名称、参数顺序、shape/dtype、FQN、重算及必要语义交给对应消费者，不按 shape 猜测未知角色。
- 自定义算子的输入/输出角色和轴含义由定义者提供；平台校验、保留并透传，算子 adaptor 按需消费。对接见[训练声明](../torchtitan-npu-simulator/experiments/simulator/docs/custom-tensor-semantics.md)、[平台保留](../sim-platform/docs/design/tensor-semantics.md)、[算子读取](../operator-performance-models/docs/tensor-semantics.md)。
- 当前平台接收静态内存，不依赖 L1/L2 回放。负载仓自身的生命周期估计不等于平台已实现执行时间驱动的动态回放；后续归一范围包含图及对应内存信息，接口仍需共同设计。

## 预测与硬件

算子语义 adaptor 与 costmodel 独立注册，前者解释事实，后者按语义和硬件建模。当前采用 roofline，保留其他后端和显式 fallback 的组织能力；缺 adaptor、缺 model 和模型失败不能伪装为预测成功。分类/执行资源归平台，模型只返回耗时及解释明细。

默认算法假设、内部计算精度、等效操作计数、固定开销及校验归算子仓。平台按名称调用通用后端工厂或注入 Backend，不管理模型专属配置字段；替换为查表等后端不应修改平台任务 schema。有效版本和配置由后端声明，平台只用作缓存身份，不解释算法参数。默认模型假设与设备标定须明确区分。

芯片/拓扑的用户配置归平台，算子仓消费窄能力接口，不读取平台目录、不反向依赖平台。局部硬件预测覆盖不自动表示异构部署调度。当前已有 chip、topology 加载及通信 V1 单算子接入；跨算子通信争用及设备标定不因此视为完成，见[硬件入口](../sim-platform/hardware/README.md)和[通信接入](../sim-platform/docs/communication-v1-implementation.md)。

平台缓存原始预测，键覆盖语义、硬件、模型版本和有效配置；执行修正不污染缓存。miss/fail 在平台明确记录后以零耗时继续，保留依赖和覆盖状态；配置/路由/图错误仍失败。完整策略和指标覆盖定义见[预测容错](../sim-platform/docs/design/prediction-tolerance.md)，不在管理仓维护异常类或缓存字段清单。

## 卸载、执行与修正

- 训练仓生成激活/优化器双向传输与等待依赖，修正最终静态内存；平台只计算传输时间、运行 DES 和消费预算。两种卸载独立开关，不将传输时间改写为 AdamW 时间，也不重复补窗口拖尾或扣显存。
- 主机链路默认能力归 topo，任务 TOML 可逐字段覆写。平台冻结各硬件变体的生效能力，向算子仓提供传输方向与有效字节数，并调度返回的传输耗时。算子仓维护计时公式。激活、优化器和推理主机传输复用同一能力，详见[平台传输配置](../sim-platform/docs/design/activation-offload.md)。
- L1 负责单图，L2 负责阶段实例及跨阶段依赖。当前训练按 GA 串行复用 F/B 后执行一次 O，不据此承诺 PP、跨阶段异步执行或推理循环。
- vec 修正在 DES 前，保留原始预测和执行成本；DES 后处理保留原时间线与具名变化记录。MoE A2A 修正用于近似替代 MegaMoE，不接入独立 MegaMoE 实现；按最新确认在 DES 之前处理。先按层级 FQN、执行类型及通信依赖提取片段，区分原始前向、重算和梯度反向；两种系数均表示缩减比例、默认 0 且范围 [0,1]；MoE 按该比例对 min(通信串行和, vec 修正后计算串行和) 分摊折减，只改 DES 耗时，不改工作量；见[平台 DES 前修正](../sim-platform/docs/design/pre-des-corrections.md)。

卸载近似与适用范围由[训练激活方案](../torchtitan-npu-simulator/experiments/simulator/docs/activation-offload-design.md)、[平台激活接入](../sim-platform/docs/design/activation-offload.md)、[优化器接入](../sim-platform/docs/design/optimizer-offload.md)维护；修正及分母由[平台后处理](../sim-platform/docs/design/postprocessing.md)维护。指标公式和 GA 加权由[指标组件](../sim-platform/docs/design/utilization-metrics.md)与[训练统计](../sim-platform/docs/design/training-statistics.md)维护，不再在本页复制。

## 配置、日志与版本

进程共享对象仅管理默认设置；任务固定独立配置快照，不能让候选任务互相覆盖。CLI/Python 使用相同加载路径，来源可查询；具体优先级见[统一入口](../sim-platform/docs/usage/training-task-entrypoint.md)。组件通过参数获得所需配置，不导入平台单例。

平台管理每任务独立目录及 task.log，子仓发标准日志；批量执行按任务起独立进程并注入目录，不汇总成一个大日志、不要求 inherit，见[批量执行](../sim-platform/docs/usage/batch-execution.md)。Python 日志接管不包含原生 FD/C++/子进程输出，后者不列为待办，见[任务日志](../sim-platform/docs/usage/task-logging.md)。

组件独立安装/发布；平台单向验证精确组合，根仓不维护第二份锁定清单。运行环境可以不同，不能因为共享工作区就假定训练/推理依赖可合装。版本与协作规则见[公共规范](workspace-conventions.md)。

## 尚未收敛的工作

只在[跨仓待办](roadmap.md)维护未完成能力及决策点。业务仓已有实现不自动代表平台已经接入；具体完成状态和验收证据应回到所属仓库查看。
