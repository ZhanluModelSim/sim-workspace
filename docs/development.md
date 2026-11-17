# 工作区开发指南

仅运行 demo 或修改仿真配置时，从[首页](../README.md)进入平台使用文档即可。本页面向需要克隆、修改和交付源码的开发者；具体安装与测试命令仍由所属业务仓维护。

## 获取源码

使用具备组织仓库权限的 GitHub SSH 身份。下面获取完整工作区；单仓任务可以只克隆目标仓及其实际依赖，Portal 不是 CLI 仿真的前提。

```bash
git clone git@github.com:ZhanluModelSim/sim-workspace.git SimWorkspace
cd SimWorkspace
git clone git@github.com:ZhanluModelSim/sim-platform.git sim-platform
git clone git@github.com:ZhanluModelSim/operator-performance-models.git operator-performance-models
git clone --branch codex/simulator-titan030 \
  git@github.com:ZhanluModelSim/torchtitan-npu-simulator.git torchtitan-npu-simulator
git clone git@github.com:ZhanluModelSim/inference-models-simulator.git inference-models-simulator
git clone git@github.com:ZhanluModelSim/sim-portal.git sim-portal
```

已存在的目录先检查状态，不重复 clone 或覆盖。分支是开发获取入口，不是可复现版本锁定；核对实际 SHA 与 dirty 状态。根 `.gitignore` 排除业务仓、环境、日志和产物，不强制添加业务目录，不转换为 submodule/gitlink。

## 选择开发环境与入口

发布镜像适合固定版本体验，源码位于 `/sim-workspace/`，没有 `.git` 历史，不能直接 `git pull`。镜像内修改、导出和替换源码的方法见[平台镜像指南](../sim-platform/docs/usage/offline-cli-quickstart.md)。替换组件后，原镜像的验收结论不自动适用。

从克隆源码开发时，先遵守所在工作区的执行环境规则，再按目标仓安装说明准备环境；不要把镜像内路径与开发容器挂载路径混用。核对容器映射、Python、依赖版本和实际导入位置；源码存在不等于已安装。使用标准安装，不用 `PYTHONPATH` 或 `sys.path` 拼接替代。

| 修改目标 | 最小入口 |
| --- | --- |
| 平台配置、执行、结果或集成 | [平台 README](../sim-platform/README.md) → [开发与验证](../sim-platform/docs/development/development-status.md) |
| 训练模型、捕获或静态内存 | [Simulator README](../torchtitan-npu-simulator/experiments/simulator/README.md) → [环境与开发导航](../torchtitan-npu-simulator/experiments/simulator/docs/developer-guide.md) |
| 推理模型与调用计划 | [推理 README](../inference-models-simulator/README.md) |
| 算子语义与性能模型 | [算子 README](../operator-performance-models/README.md) |
| Web/MCP、队列与 Worker | [Portal README](../sim-portal/README.md) |

以上相对链接用于已克隆的工作区；只浏览管理仓网页时，从[首页仓库表](../README.md#参与开发)打开业务仓。进入目标仓先读适用 AGENTS.md，再按任务读取相关专题，不默认阅读所有仓库或全部架构文档。

## 开发与交付

修改前检查目标仓分支、HEAD、工作树与远端引用，保留已有改动；从确认的基线创建独立任务分支。所有修改经 PR 合入，禁止直接推送 main/master 或约定集成分支，详见[分支与 PR 规则](../.agents/workflows/pr-only-development.md)。

涉及跨仓接口或职责变化时才进一步读取[跨仓边界](backend-requirements.md)；确认未完成事项时读取[待办](roadmap.md)。按风险完成验证，纯文档检查事实、命令、路径和链接即可，无需重跑昂贵训练。

各仓独立 Git、依赖、测试和发布。正式集成组合由平台记录精确 commit、制品和环境，管理仓不维护第二份锁定清单。跨仓变更说明生产者、消费者和迁移方式，先验证候选组合，再按组件到平台顺序交付。

需离线交付管理资料时，可在管理仓执行 `git bundle create ../sim-workspace.bundle --all`；接收者用 `git clone sim-workspace.bundle SimWorkspace` 恢复。业务仓需分别交付；bundle 不包含未提交改动或运行环境。

更多规则按[文档索引](README.md)选择，文档维护遵循[公共协作与文档规范](workspace-conventions.md)。`docs/bootstrap/` 只作历史追溯，不是开发前置阅读。
