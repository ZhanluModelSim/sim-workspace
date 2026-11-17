# 大模型负载仿真工作区

SIMPlatform 将训练／推理负载捕获、算子性能预测与仿真串起来，输出时延、吞吐、静态显存预算、算子统计和时间线。支持单任务和参数扫描批量执行。

**首次使用推荐发布镜像：无需克隆源码、安装 Python 依赖、下载模型权重或准备 NPU。** 本页带你完成一次训练 demo；详细配置与用例由平台仓维护。

## 首次运行

### 1. 获取镜像并进入容器

准备可运行 Linux 容器的 Docker；当前镜像面向 **Linux x86_64（linux/amd64）**。拉取需要网络，运行可断网。

镜像发布在 GitHub Container Registry（GHCR），当前示例使用公开版本 `0.1.0-preview.1`，无需登录。固定 digest、发布记录和验收范围见[平台镜像指南](https://github.com/ZhanluModelSim/sim-platform/blob/main/docs/usage/offline-cli-quickstart.md)。镜像内源码固定，主线更新不会自动进入此版本。

在宿主机终端执行：

```bash
docker pull ghcr.io/zhanlumodelsim/simplatform:0.1.0-preview.1
docker run -it --name sim-demo --pull never --network none \
  ghcr.io/zhanlumodelsim/simplatform:0.1.0-preview.1 bash
```

### 2. 运行训练 demo

以下命令在容器中执行，环境已经安装，无需额外激活：

```bash
cd /sim-workspace/sim-platform
sim-platform train examples/training/single.toml --validate
sim-platform train examples/training/single.toml
```

第一条只预检配置，第二条才捕获并仿真。首次训练可能编译镜像内的扩展，无需联网下载。demo 使用 DeepSeek-V4 smoketest 小配置和 `example` 示例硬件。

### 3. 查看并取出结果

在容器中查看：

```bash
cat runs/training/l1/default/statistics/training.json
ls runs/training/l1/default/
```

`runs/training/task.log` 是任务日志；`l1/default/` 包含阶段 CSV、Chrome Trace 和统计目录。`training.json` 包含时延、吞吐、利用率、预测覆盖和静态显存。检查结果及预测覆盖，不仅看命令是否成功退出：缺失／失败预测会被记录，任务仍可能完成。

执行 `exit` 退出容器后，在宿主机取出结果：

```bash
docker cp sim-demo:/sim-workspace/sim-platform/runs/training ./training-results
```

具名容器保留结果和修改；下次用 `docker start -ai sim-demo` 重新进入。同名容器已存在时使用此命令，或为新容器换名。不要在取出结果前删除容器。

这是 Meta 仿真流程演示：示例硬件不代表已标定设备精度，静态显存预算不等于设备运行时动态峰值。

## 接下来做什么

按当前目标选择一项即可，无需依次读完所有文档。镜像内的 `/sim-workspace/sim-platform/docs/` 和 `examples/` 与镜像版本对应；下列网页链接跟随平台主线。

| 目标 | 平台文档 |
| --- | --- |
| 修改模型、并行、batch、精度或硬件配置 | [训练任务与配置](https://github.com/ZhanluModelSim/sim-platform/blob/main/docs/usage/training-task-entrypoint.md) |
| 批量扫描参数并导出汇总 CSV | [批量执行](https://github.com/ZhanluModelSim/sim-platform/blob/main/docs/usage/batch-execution.md) |
| 运行推理仿真 | [推理快速开始](https://github.com/ZhanluModelSim/sim-platform/blob/main/docs/usage/inference-quickstart.md) |
| 阅读 CSV、Trace 和统计产物 | [结果导出](https://github.com/ZhanluModelSim/sim-platform/blob/main/docs/usage/l1-exports.md) |
| 寻找更多可运行配置 | [示例索引](https://github.com/ZhanluModelSim/sim-platform/blob/main/examples/README.md) |
| 更新镜像内源码、核对版本 | [镜像指南](https://github.com/ZhanluModelSim/sim-platform/blob/main/docs/usage/offline-cli-quickstart.md) |

批量体验可在同一容器的 `/sim-workspace/sim-platform` 下继续执行：

```bash
sim-platform batch run examples/training/batch.toml --dry-run
sim-platform batch run examples/training/batch.toml
sim-platform batch export runs/batch-demo --top 10
```

示例展开 8 个任务，状态记录在 `runs/batch-demo/batch.json`，汇总表为 `runs/batch-demo/batch-summary.csv`。退出后可用 `docker cp sim-demo:/sim-workspace/sim-platform/runs/batch-demo ./batch-results` 取出整批产物。重复运行和失败处理见批量文档。

## 参与开发

需要克隆源码、配置开发环境或修改实现时，阅读[开发指南](docs/development.md)。AI 执行任务遵守 [AGENTS.md](AGENTS.md)，按任务进入对应仓库，不默认遍历所有设计文档。

| 仓库 | 职责 |
| --- | --- |
| [sim-platform](https://github.com/ZhanluModelSim/sim-platform) | 仿真集成、配置、预测编排、调度与结果 |
| [torchtitan-npu-simulator](https://github.com/ZhanluModelSim/torchtitan-npu-simulator) | 训练模型、图捕获与静态内存 |
| [inference-models-simulator](https://github.com/ZhanluModelSim/inference-models-simulator) | 推理模型、调用计划与内存交付 |
| [operator-performance-models](https://github.com/ZhanluModelSim/operator-performance-models) | 算子语义与性能模型 |
| [sim-portal](https://github.com/ZhanluModelSim/sim-portal) | Web/MCP 用户入口、任务分发与结果展示 |

本管理仓只维护首次体验导航、跨仓规则与待办；业务仓独立管理，不使用 submodule。管理资料按需查阅[文档索引](docs/README.md)。
