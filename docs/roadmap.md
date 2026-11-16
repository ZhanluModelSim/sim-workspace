# 跨仓待办与未决事项

本页只记录需要跨仓协作或用户决策的未完成工作，不是冻结的排期，也不复制组件内部功能清单。训练单任务、推理独立入口及批量、两种卸载、指标/导出、日志、预测容错和 tensor_semantics 已接入，当前范围见[平台架构](../sim-platform/docs/architecture.md)。

## 接入与能力补齐

| 事项 | 当前边界 / 需要确认 | 牵头与协作 |
| --- | --- | --- |
| 推理调用计划归属 | 独立入口、逐图预测/DES、统计及批量已实现；串行分块 prefill 目前由平台展开请求，与模型计划归负载仓的边界需要收敛，复杂计划另行设计，本轮不迁移 | 平台 + 推理 |
| 通信争用与校准 | topology 加载和通信 V1 单算子接入已实现；后续收敛跨算子资源争用及真机校准，不把单算子模型视为多rank联合调度 | 平台 + 算子，负载仓提供通信事实 |
| 传输配置迁移 | 通信 V1 的 topology 已有实现；统一主机传输能力/API 就绪后，将 platform.transfers 及旧别名迁到 topo 能力/API，覆盖两种卸载与兼容策略 | 平台，训练核对行为保持 |
| 批量寻优 | 批量执行（一个文件的参数扫描展开）与结果汇总／排行已实现，见[规模化编排设计](../sim-platform/docs/design/scaled-orchestration-design.md)与平台[批量执行](../sim-platform/docs/usage/batch-execution.md)；用户已确认训练场景不做搜索式寻优，仍待决的是何时重启 FEAT-050 | 平台 |
| 精确组件组合与发布 | 已有[有限范围组合验证](../sim-platform/docs/development/component-compatibility.md)；继续补齐完整通过的发布组合及集成 CI，记录提交、制品和环境，根仓不重复锁版本。Portal 候选组合见平台 `integration/portal-compatibility.json`，仍为未发布状态 | 各组件独立发布，平台集成 |
| Portal 交付边界 | 单任务、硬件变体、批量、寻优、共享池与机器 HTTPS 已在本机容器验证；真实两机、SSO 与用户侧 HTTPS 部署属门户自身交付边界，见[实施计划](../sim-portal/docs/implementation-plan.md) | sim-portal，平台记录组合 |
| 性能校准与覆盖验证 | 使用已建模主要算子及代表性真实负载验证，明确缺失覆盖；不追求100%覆盖作为运行门槛，也不固定当前示例端到端时间 | 算子仓 + 平台 + 硬件数据提供方 |

推理现状和限制见[推理 README](../inference-models-simulator/README.md)、[运行指南](../inference-models-simulator/docs/模型仿真运行指南.md)；预测范围见[算子 README](../operator-performance-models/README.md)。这里不维护逐模型或逐算子完成度。

## 后续设计，不提前冻结接口

- **多图与复杂 L2**：PP、跨阶段重叠、不同 microbatch 模板，以及推理循环/分支需要真实调用计划驱动设计；不能直接沿用串行训练加法。
- **推理服务与分离部署**：单步、代表图乘次数、KV逐步增长和完整投机循环不是同一口径；AF/PD与复杂服务调度不自动纳入首条接入链路。推理仓已有静态投机表达，不等于平台已支持服务级调度。
- **图与内存统一消费**：后续设计执行时序驱动的内存回放及事件锚点；负载仓自己的生命周期估计不等于平台 DES 回放，静态结果不得标为动态峰值。
- **多硬件执行与指标**：已有局部算子硬件预测覆盖；异构部署、迁移、跨设备资源和多硬件利用率还需单独确定。
- **公共图高级工具**：现有查询/校验/快照可用；交互编辑、依赖可视化和大图存档优化由实际需要驱动，不作为训练流程前置条件。

## 持续验证与维护

- 新模型或同步策略变动后复核[GA 通信模板](../sim-platform/docs/development/ga-communication-audit.md)；Kimi 策略恢复已修复，不再列为待修。
- 训练已采用默认结构预热，变更时保护[优化器稳态与状态量](../sim-platform/docs/development/optimizer-first-use-audit.md)，不能用名称过滤初始化来替代正确捕获。
- 按[真实链路复核方法](../sim-platform/docs/development/development-status.md#真实链路复核方法)检查基础及卸载组合、部分预测覆盖、结果结构和指标关系；历史实验通过不等于之后的新组合已验收。
- 源字段扩展由实际 adaptor/model 需求驱动；自定义算子角色/轴语义已有交付链路，不为潜在模型猜测标量、索引或Tensor身份。
- 组件文档状态随实现维护；核对能力时结合当前 README、AGENTS.md 与源码，不沿用旧状态。

完成一项时，将实现和验收说明落到负责的业务仓，更新此页状态或移出待办；若改变跨仓分工，同时更新[职责边界](backend-requirements.md)。未确认事项必须先由主 agent 与用户讨论。
