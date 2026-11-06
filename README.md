# 大模型负载仿真工作区

本仓管理跨仓协作规则、职责边界、文档导航与待办。业务代码位于独立仓库，不纳入本仓，也不使用 Git submodule。

## 仓库与阅读入口

| 目录 / 远端 | 责任与文档入口 |
| --- | --- |
| [sim-platform](https://github.com/ZhanluModelSim/sim-platform) | 产品集成、公共图、预测编排、DES、指标与输出；[当前架构](sim-platform/docs/architecture.md)、[扩展指南](sim-platform/docs/development/extending-platform.md)、[开发验证](sim-platform/docs/development/development-status.md) |
| [torchtitan-npu-simulator](https://github.com/ZhanluModelSim/torchtitan-npu-simulator) | 训练负载；[sim 架构](torchtitan-npu-simulator/experiments/simulator/docs/architecture.md)、[模型接入](torchtitan-npu-simulator/experiments/simulator/docs/model-integration.md) |
| [inference-models-simulator](https://github.com/ZhanluModelSim/inference-models-simulator) | 推理负载；[能力与限制](inference-models-simulator/README.md)、[运行指南](inference-models-simulator/docs/模型仿真运行指南.md) |
| [operator-performance-models](https://github.com/ZhanluModelSim/operator-performance-models) | 语义解析和算子预测；[入口](operator-performance-models/README.md)、[预测设计](operator-performance-models/docs/roofline-design.md) |

平台已贯通训练单任务；推理仓已有独立负载实现，平台接入仍待完成。组件支持范围与验收以各仓为准，管理仓不维护重复功能清单。仓库名使用小写连字符，Python 导入包使用下划线；SIMPlatform 为平台产品名称。

表内相对文档链接用于获取完整工作区后的本地阅读；仅浏览管理仓远端时，通过各业务仓远端入口访问其文档。

## 获取工作区

使用具备组织仓库权限的 GitHub SSH 身份：

```bash
git clone git@github.com:ZhanluModelSim/sim-workspace.git SimWorkspace
cd SimWorkspace
git clone git@github.com:ZhanluModelSim/sim-platform.git sim-platform
git clone git@github.com:ZhanluModelSim/inference-models-simulator.git inference-models-simulator
git clone git@github.com:ZhanluModelSim/operator-performance-models.git operator-performance-models
git clone --branch codex/simulator-titan030 \
  git@github.com:ZhanluModelSim/torchtitan-npu-simulator.git \
  torchtitan-npu-simulator
```

已存在的目录先检查状态，不重复 clone 或覆盖。以上分支是开发获取入口，不是可复现版本锁定；运行前确认实际提交及 dirty 状态。源码就位不等于环境就绪，安装遵循各仓说明，并核对容器映射及 editable 安装的真实导入位置。

根 `.gitignore` 排除业务仓、环境、临时日志和运行产物。需要离线交付管理资料时，可执行 `git bundle create ../sim-workspace.bundle --all`，接收者用 `git clone sim-workspace.bundle SimWorkspace` 恢复；业务仓需分别交付，bundle 不包含未提交改动。

## 管理资料

1. [AGENTS.md](AGENTS.md)：跨仓开发规则与阅读顺序。
2. [职责与协作边界](docs/backend-requirements.md)：当前责任交接及组件实现链接。
3. [跨仓待办](docs/roadmap.md)：未完成能力、待确认设计及协作归属。
4. [文档与协作规范](docs/workspace-conventions.md)：唯一维护位置、版本和交付。
5. [公共 agent 资料](.agents/README.md)：推荐工作流与 Python 规范。

[启动评审资料](docs/bootstrap/simplatform-architecture-review/README.md)只作历史参考，不是当前开发必读或实现依据；早期临时调查和已替代的决策可从 Git 历史追溯。

## 版本管理

根仓只管理上述资料；业务仓独立管理源码、依赖、测试和发布。操作业务代码时进入对应仓库或使用 `git -C`，不要强制添加被忽略目录或转换成 gitlink。

平台单向选择并验证精确组件组合，正式集成清单归 `sim-platform`；根仓不维护第二份锁定清单。组件不反向锁定平台，包版本或分支名不能代替提交、制品及环境验证。具体流程见[公共规范](docs/workspace-conventions.md)。
