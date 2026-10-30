# SIMPlatform 设计评审资料包

本目录保留启动评审与原型的历史资料。当前工作区目录名已统一为 `sim-platform`、`torchtitan-npu-simulator`、`inference-models-simulator`、`operator-performance-models`；正文中的旧名保留作历史上下文。最新布局见[工作区 README](../../../README.md)，后续确认及推理侧未决问题见[工作区 AGENTS.md](../../../AGENTS.md)，其优先于早期建议。

建议阅读顺序：

1. [架构与协同开发方案](架构与协同开发方案.md)及 [SVG 架构图](architecture.svg)。
2. [DES 设计与开发建议](DES设计与开发建议.md)。
3. [原型穿刺报告](des-prototype/README.md)及其时间线。

`des-prototype/` 包含标准库 DES、测试、原始捕获 JSON、分类 CSV、结果 JSON 和 SVG；可在解压后使用 Python 3 重放，无需训练环境。重新抓取才需要原训练容器。

所有性能时间为假设 ticks，不是真实硬件性能。已有验证、未验证范围与后续计划分别列明。平台初始化采用单发行包 `src/sim_platform/`；不得从早期讨论误建 `packages/` 多发行包结构。
