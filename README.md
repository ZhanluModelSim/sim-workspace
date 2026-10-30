# 大模型负载仿真工作区

本仓库管理多仓协作所需的说明、规则、设计资料和公共 agent 规范。业务代码分别位于同级的独立仓库中，不纳入本仓库，也不使用 Git submodule。

## 目录与命名

仓库与目录名称统一使用小写英文和连字符；Python 导入包使用下划线。SIMPlatform 是平台产品称呼，对应仓库目录 `sim-platform`，规划中的 Python 包为 `sim_platform`。

| 目录 | 职责 | 当前状态 |
| --- | --- | --- |
| `sim-platform/` | 编排、公共适配、预测缓存、DES 与指标 | 已接入，当前仅有职责 README |
| `torchtitan-npu-simulator/` | 训练负载发生器 | 已接入独立仓库 |
| `inference-models-simulator/` | 推理负载发生器 | 已接入，当前仅有职责 README |
| `operator-performance-models/` | 算子性能预测模型及其管理 | 已接入，当前仅有职责 README |
| `docs/` | 跨仓设计、决策、启动资料与文档约定 | 由本仓库管理 |
| `.agents/` | 可共享的 agent 工作流程与规范入口 | 由本仓库管理 |

`operator-performance-models` 替代原 `Costmodel` 名称，强调算子性能预测职责；它不承担完整训练／推理仿真编排。原 `SIMPlatform`、`inference-workload` 目录已分别改名为 `sim-platform`、`inference-models-simulator`。

## 获取和恢复工作区

管理仓地址为 [ZhanluModelSim/sim-workspace](https://github.com/ZhanluModelSim/sim-workspace)，使用具备仓库访问权限的 GitHub SSH 身份获取：

```bash
git clone git@github.com:ZhanluModelSim/sim-workspace.git SimWorkspace
cd SimWorkspace
```

需要离线交接时，可从仓库根目录执行 `git bundle create ../sim-workspace.bundle --all`，接收者执行 `git clone sim-workspace.bundle SimWorkspace`。以上方式只交付管理仓中的已提交内容，不包含业务仓库和未提交改动。

业务仓库由根 `.gitignore` 排除。获取管理仓后，从其根目录分别克隆四个业务仓库：

```bash
git clone git@github.com:ZhanluModelSim/sim-platform.git sim-platform
git clone git@github.com:ZhanluModelSim/inference-models-simulator.git inference-models-simulator
git clone git@github.com:ZhanluModelSim/operator-performance-models.git operator-performance-models
git clone --branch codex/simulator-titan030 \
  git@github.com:ZhanluModelSim/torchtitan-npu-simulator.git \
  torchtitan-npu-simulator
```

这些仓库需要相应的 GitHub SSH 访问权限。若目录已存在，先检查其状态，不重复 clone 或覆盖。平台远端已由用户更名为 `sim-platform`，与本地目录名称一致。

2026-10-30 接入与初始化：三个新仓库均已克隆，本轮仅编写各自的职责 README，说明分工与尚待明确的问题。未建立实现文档、接口契约、工程骨架、CI 或新的开发约定；具体细节继续讨论后再确定。

当前接入基线为 `dc2b6f7a21082bb74c001fb4e05b9fe5ff9cc526`。分支可能继续移动；需要复现本轮源码时，可在训练仓库无本地改动的前提下执行：

```bash
git -C torchtitan-npu-simulator switch --detach dc2b6f7a21082bb74c001fb4e05b9fe5ff9cc526
```

源码就位不等于运行环境就绪。训练仓库仍需配套训练栈，安装和运行遵循其自身 README 与 AGENTS.md。旧容器的 editable 安装不会自动切换到本工作区的新路径。

## 两层版本管理

- 本仓库：协作规则、文档、公共规范和工作区搭建说明。
- 业务仓库：各自的源码、依赖、测试和发布。
- 平台未来的集成清单：经过验证的精确组件提交及环境组合，放在 `sim-platform` 内。根仓不维护另一套正式组件锁定清单。

在根目录使用 Git 只操作管理资料；操作业务源码时进入对应仓库或使用 `git -C <目录>`。不要强制添加被忽略的业务目录，也不要把它们转换为 gitlink。共享修改前分别检查有关仓库的状态。

## 阅读入口

1. [工作区协作约定](AGENTS.md)：当前状态、架构边界、已确认决策和遗留问题。
2. [公共协作与文档规范](docs/workspace-conventions.md)：规则归属、文档维护和验证要求。
3. [公共 agent 资料](.agents/README.md)：共享内容的放置和使用方式。
4. [启动评审资料](docs/bootstrap/simplatform-architecture-review/README.md)：原始架构方案和 DES 原型。
5. [后端职责与核心流程确认](docs/backend-requirements.md)：已确认的预测、DES、两种修正和 offload 要求，以及共享配置建议和待定项。

[旧平台源码分析](docs/legacy-workload-model-platform-review.md) 仅保留为历史调查记录，不是开发必读或实现依据；当前需求以 AGENTS.md 和后端确认文档为准。

启动资料保留历史讨论与实验快照；其中旧目录名称、运行路径和未批准方案不自动成为当前约定。当前确认包括保留 FSDP 通信视图、跨阶段调度归 L2、允许内存对象交付；训练／推理统一入口和推理建模方式仍待资料明确。详细记录以 AGENTS.md 为准。
