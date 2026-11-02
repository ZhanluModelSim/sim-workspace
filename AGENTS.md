# SimWorkspace 工作区协作约定

## 目标与当前状态

本工作区用于协同开发大模型训练／推理负载仿真系统，贯通负载生成、算子性能预测、L1/L2 离散事件仿真（DES）、指标输出，并逐步支持批量任务与寻优。

已确定采用同级独立仓库布局。工作区根目录组织跨仓开发，SIMPlatform 负责产品集成。根目录作为轻量 Git 管理仓，管理协作规则、公共规范和文档，独立业务仓库从根仓排除。四个业务仓库均已接入；平台与算子性能预测仓已进入训练优先实现阶段，推理仓仍为需求文档。当前实现和验证范围见平台 docs/development-status.md；不能将测试用 synthetic 预测视为真实 roofline 能力。

新仓接入记录（2026-10-30）：已克隆组织下的平台、推理与算子性能预测仓库。平台远端最初为 `sim-platform-`，用户已更名为 `sim-platform`，本地 origin 与获取说明同步更新。三个新仓本轮只写职责 README：说明已讨论的分工和未决事项，不写实现方案、接口契约或新的工程约定，不初始化业务代码。获取命令见根 README。

训练仓库接入记录（2026-10-30）：从 `/home/andy/Projects/torchtitan-npu-simulator` 的干净工作树创建独立本地 clone，使用 `--no-hardlinks`，未共享 Git objects alternates；分支为 `codex/simulator-titan030`，基线提交为 `dc2b6f7a21082bb74c001fb4e05b9fe5ff9cc526`。`origin` 已设为 `git@github.com:ZhanluModelSim/torchtitan-npu-simulator.git`。此次没有联网 fetch，不表示远端最新状态。该记录是接入来源，不代替未来平台集成清单；实际开发时重新检查 HEAD 与工作树。

当前已在 ttsim 容器独立虚拟环境安装工作区训练 checkout，并完成真实 Meta 捕获和平台系统验证。训练仓库内记录的旧宿主／容器路径属于原环境；运行前须核对主包和 simulator 的实际导入路径，不能默认新 checkout 已被旧 editable 安装使用。

## 目录与职责

```text
SimWorkspace/
  AGENTS.md
  docs/bootstrap/simplatform-architecture-review/
  sim-platform/
  torchtitan-npu-simulator/
  inference-models-simulator/
  operator-performance-models/
```

- `docs/bootstrap/`：从原 `init/` 整体迁入的启动评审资料，包含架构建议、DES 设计、独立原型与捕获数据。保留资料之间的相对链接。
- `sim-platform/`：平台编排、M/N 适配、统一负载表达 G、公共图处理、预测缓存、L1/L2 DES、指标与集成验证。
- `torchtitan-npu-simulator/`：现有训练负载发生器，维护训练框架适配、捕获、生命周期与训练专属处理。
- `inference-models-simulator/`：推理负载发生器，独立维护推理框架适配、捕获与生命周期。
- `operator-performance-models/`：算子预测特征归一、预测模型管理、性能估计与相关元数据。

业务仓库及目录名称采用小写连字符风格；平台为 `sim-platform`，推理为 `inference-models-simulator`，算子性能预测为 `operator-performance-models`，训练保留现有名称。SIMPlatform 作为平台产品称呼保留，Python 导入包规划仍为 `sim_platform`。四个业务仓库保持同级。新组件的名称和远端地址以实际创建或接入时的信息为准，不猜测远端地址。根目录不承载平台业务包，不在此建立第二套正式集成清单或运行器。

## 资料与决策状态

跨仓协作和文档维护遵循 `docs/workspace-conventions.md`；公共 agent 资料入口见 `.agents/README.md`；Python 开发遵循 [.agents/standards/python-development.md](.agents/standards/python-development.md)，新仓统一工具基线，训练仓保留自身工具链。

## Agent 协作方式

后续开发采用[多仓协作推荐工作流](.agents/workflows/multi-agent-development.md)：主 agent 负责需求讨论、总体设计、任务拆分、review 与集成验收；边界和验收条件明确的独立任务可按需委派子 agent。不要求每仓固定一个 agent，小任务由主 agent 直接完成。

当前需求讨论必须由主 agent 与用户直接完成，不委派需求确认，不让各仓自行补齐未定假设。派发时明确修改范围、依据、排除项及交付要求；每份可变内容只安排一个写入者。主 agent 检查实际 diff 和验证证据，统一协调跨仓变更与交付。

## 资料阅读与决策依据

开始架构或实现工作前，按任务需要阅读：

0. `docs/backend-requirements.md`：最新后端职责、预测与修正流程、offload 和共享配置讨论状态；优先于旧设计素材。
1. `docs/bootstrap/simplatform-architecture-review/README.md`
2. `docs/bootstrap/simplatform-architecture-review/架构与协同开发方案.md`
3. `docs/bootstrap/simplatform-architecture-review/DES设计与开发建议.md`
4. `docs/bootstrap/simplatform-architecture-review/des-prototype/README.md`

区分用户已确认决策、草案建议和已实现能力。同级仓库布局已经确认；资料中其余待评审问题不能仅因出现在文档中就视为获批。启动资料是历史设计基线；后续正式设计归属对应业务仓库，并在变更时说明替代关系，避免维护两份相互矛盾的规范。

原型目录是设计参考和回归素材，不是生产后端。其中 synthetic ticks、资源分类及回退规则不代表真实硬件性能；不能根据原型时间线推导真实显存峰值。原报告中的 `/tmp/` 路径和容器信息描述当时实验环境，不是当前工作区路径。

### 2026-10-30 对接讨论确认

以下用户确认优先于启动草案和此前助手提出的对接建议；这是后续设计约束，不表示代码已经修改。

- **保持 FSDP 通信视图。** 隐藏 FSDP 非通信准备／搬移工作是有意选择。当前下游继续消费返回的通信视图，不切换到 `captured_workload`，不将打开完整源图作为最小链路要求。源图可继续由发生器保留用于原始引用审计，不能因此自动纳入下游性能计算。
- **跨阶段调度归 L2。** L1 负责阶段／单图推演，L2 组织阶段实例与跨阶段依赖。无 PP 时，初步计划为按 GA 展开 F、B，再执行一份 O 的简单线性调度。区分发生器实际捕获的单 microbatch 与 L2 的建模展开；具体跨阶段边界交付、通信计费归属及重复实例引用仍需设计，不能直接丢弃外部依赖，也不再默认把整个 F/B/O 合并推演作为主方案。
- **允许通过内存对象交付。** 用约定好的 Python 对象语义传递负载和结果，不要求负载层必须写 mem 或其他文件。文件导出可作为独立的可选能力；序列化、文件交换和独立 worker 都不是当前接入的前置要求。现有 `simulate()` 仍自动导出 memory summary，调整该行为属于后续代码任务，本轮未改动。这里的内存对象指同进程接口，不代表已解决跨进程对象传输或并发安全。
- **不预定统一上游入口。** 训练与推理的共用首先是逻辑分层和可复用能力，不强制统一 `TaskSpec`、`run_task`、配置基类或 provider 父类。两侧可保留独立参数空间和入口；推理需求资料现已取得，按下述新确认推进，具体接口仍待设计。

### 2026-10-30 后端讨论确认

详细依据和待定项见[后端职责与核心流程确认](docs/backend-requirements.md)，不将本文摘要当作已实现接口。

- 算子仓负责特征归一、模型管理与预测；平台负责负载适配、预测调用和缓存、L1 DES、修正、offload 后处理及 L2 阶段组织。保留算子预测与 L1 图评估两个入口层次，名称和签名待定，不要求单个 PerfBackend 大类。
- 主流程为原始预测 → **vec scaler → L1 DES → MoE A2A 后处理**。vec scaler 对全图所有 vec 算子预测耗时乘固定系数；MoE 在 DES 后按 FQN／module path 或算子标识提取各 MoE 通信与计算时间，再按规则和比例折减通信。两者都需要；具体分类、匹配、比例及汇总细节待定，尤其不沿用旧 issue 的 DES 前 MoE 折算位置。
- AC／优化器 offload 分析需要保留，但当前**不涉及 L2**。从 L1 阶段时间线提取逐层窗口，与上游数据量对齐，计算需求带宽或按硬件带宽计算传输时间与溢出，作为后处理补充端到端时间。层级、配对与优化器窗口须取得真实训练负载后确定；与 MoE 修正的组合口径及显存修正公式待定。
- 当前只采用 **roofline**，保留多预测后端、可配置选择与 fallback、算子级／局部硬件覆盖能力。局部硬件覆盖不自动承诺异构部署仿真；缺失预测不能伪造为成功。
- 缓存原始预测，vec 等修正在缓存之后；键须覆盖实际特征、硬件、模型／归一版本与预测配置，不绕过路由和 fallback。图依赖或 vec 系数改变后，重新执行受影响的 DES；缓存不保存某次执行的节点身份和时间线。
- 用户偏好进程内集中共享、可读可写且可查询的 global args 类配置，支持环境变量／CLI／程序 args 初始化。已确认它管理进程默认设置与公共开关，单次任务的模型／运行配置及 context 独立保存，搜索候选不能互相覆盖。具体单例 API、来源优先级与运行中更新规则待定；配置快照、类型校验及注入视图仍是建议，不让组件为此反向依赖平台。
- 指标种类、公式及输出 schema 尚未确认。现已获用户授权逐步实现与测试，MoE 具体规则暂不开发。两个旧 issue 是讨论素材；旧 workload-model-platform 仅用于理解职责，不是开发必读或实现依据。

### 2026-10-30 推理需求与首期范围确认

已读取推理仓 `docs/推理仓目录结构与功能设计.md`（版本 `8a9d09d293df4df848091c145be6078d3f01689a`），作为需求／功能文档，不将其中示例直接当成冻结实现。该仓仍未开发业务代码。详细记录见 [backend-requirements.md](docs/backend-requirements.md)。

- 推理仓负责图调用计划及模型语义：图选择、次数、依赖／分支、数据和状态绑定；平台 L2 负责这些调用在资源上的执行时序，不重新推断 draft/verify、KV 更新等模型行为。
- 首条推理链路是固定配置的一次 prefill 或 decode，明确 query 与已有 KV 长度。随后扩展图集合与调用计划；代表图乘 N、逐步 KV 增长和投机行为不默认等价，暂不将复杂服务调度纳入最小链路。
- 首期训练／推理均由负载仓输出静态内存信息，不接入任何 L1／L2 内存回放。后续统一范围包含图 G 及对应内存信息，再增加执行时序驱动的内存回放；当前不冻结内存 schema，不将静态峰值标为动态峰值。
- AF/PD 分离部署的子图 L2 调度暂不做；局部算子硬件预测覆盖不代表已经承诺该能力。
- offload 仍按此前确认做 L1 时间窗口上的后处理，不受暂缓内存回放影响。

剩余待定包括推理交付接口、后续多图／循环优先级、具体内存归一结构及训练／推理更上层共享边界。不因希望复用而提前冻结继承体系或统一配置。

## 架构与工程边界

### 2026-11-02 激活 offload 职责更新

本次确认替代此前激活 offload 仅做平台窗口后处理的计划：训练仓插入传输节点、等待依赖并修正静态显存，平台负责传输耗时和 DES；MBU 分子保持不变。优化器卸载不在本次范围。用户已批准开始实现，并确认保留独立 F/B 阶段：利用 B 内预取窗口，没有窗口则在 B 入口显式加载，不跨阶段延续异步传输。新增传输归为 h2d/d2h，自然参与 DES、掩盖和统计，不再额外补同一传输的拖尾。证据和实现说明见[训练仓激活 offload 文档](torchtitan-npu-simulator/experiments/simulator/docs/activation-offload-design.md)。

### 2026-11-02 优化器卸载补充确认

优化器状态卸载现已单独获准实现，与激活卸载独立开关。训练仓按实际本卡状态量生成双向传输和更新窗口依赖，直接交付不含优化器状态的 F/B/O 静态峰值（用户明确忽略逐 tensor 搬运缓冲）；原始状态总量仍保留。平台用单向带宽、独立 h2d/d2h 资源与 DES 实现全双工充分流水近似：更新窗口耗时为 max(H2D、原更新路径、D2H)，不改 AdamW 原耗时、不重复补偿、不乘 GA。更新窗口不扩大为整个 O 阶段，激活驻留修正保留；两种卸载的传输均不增加 MBU 分子。详细口径见 docs/backend-requirements.md 最新章节。

- 平台按单发行包 `pyproject.toml + src/sim_platform/` 规划；内部图处理、DES、指标等不各自发布，不创建 `packages/` 多发行包骨架。
- 共享 `sim_contracts` 包需实际共享需求与明确评审决定，不预建。初期由平台适配器对接组件的窄接口。
- 训练与推理发生器独立演进，允许不同内部结构、捕获实现和环境，不强制共用捕获框架，不导入平台内部实现。
- 各负载路径可分别提供单任务函数，供对应 CLI、批量编排和寻优复用；是否统一训练／推理的最外层接口尚未确定。正式集成清单、集成 CI 和平台运行入口归 SIMPlatform。
- 标准安装是跨仓集成基础。开发使用各自环境中的 editable 安装；正式 CI 验证 wheel 普通安装。不将 `PYTHONPATH` 或 `sys.path.append()` 作为常规集成机制。
- 保留现有训练仓库的工程布局，不为形式统一强制迁移其 `experiments/simulator/pyproject.toml`。

## 跨仓修改与版本管理

- 进入业务仓库后，先阅读其适用的 `AGENTS.md`，检查 Git 状态与已有改动；不覆盖用户未提交工作。
- 每个业务仓库独立管理 Git、依赖、测试和发布。职责说明之外的接口、工程骨架和业务实现按后续讨论与任务推进。
- 平台单向锁定已验证的组件组合；组件不反向锁定平台提交。正式清单记录精确 commit 与环境信息，分支名不能代替可复现版本。
- 本地覆盖需记录路径、实际 SHA 与 dirty 状态，不能静默写入正式发布组合。
- 跨仓变更先保持组件接口兼容，以候选精确提交组合做集成验证；组件合入后更新最终 SHA 并重新验证，平台最后合入集成清单。
- 尽量将变更限定于所属组件；涉及边界调整时说明受影响的生产者、消费者和迁移方式。

## 仿真语义与验证

- 分开保存原始捕获事实、建模假设、预测结果和模型修正，保留原始节点到 G 的作用域身份映射与版本来源。
- G 是公共负载表达，可包含算子图、调度和生命周期等结构，不等同于 DES 内部执行对象。
- DES 分开表达执行约束、资源需求和仲裁策略；保留捕获的 stream/event 关系。逻辑 stream 不等于硬件资源，ready 优先级不能代替执行资格约束。
- 缺失流信息、未知算子和未知成本必须显式报告或采用有记录的策略；未知预测不能静默记为零耗时。
- L1 修正保留原结果与修改记录，避免重试重复应用。修改节点耗时需重算受影响的调度；只修改汇总字段时明确时间线未同步变化。
- 预测缓存应纳入 dtype、layout、相关属性、硬件、配置、模型版本和归一版本等影响因素。
- 验证按修改范围覆盖组件、契约、适配器及必要的集成测试。区分逻辑正确性、仿真性能和真实硬件精度，不将 Meta 捕获成功当作设备数值或性能验证。

## 推进顺序

按启动方案逐步贯通：A 边界与工程骨架 → B 训练最小链路 → C 真实预测与修正 → D 推理接入 → E 契约稳定与规模化编排。

优先用真实小案例检验接口，再扩大抽象；公共契约应在训练和推理路径均验证后稳定。当前平台与算子预测仓已初始化可安装 Python 包，训练最小工程链路已实现；真实 roofline、自动 offload 窗口配对、MoE 规则与推理接入继续按需求推进。实现必须包含单元／模块／系统验证和独立 review。

### 公共算子名称与分类（最新确认）

公共图以 PascalCase 简化名称供 costmodel 匹配，移除框架命名空间和 overload 后缀，同时保留 raw_name 调试。初期覆盖常见 ATen/CANN 与实际训练样本，可迭代扩展规则。核心 category 为 mix、cube、vec、comm、h2d、d2h、control、zero；最新确认未命中规则默认vec，不再保存节点kind或unknown类别。mix 默认同时需要 cube 与 vec；类别、耗时、资源需求独立表达。control 是独立类别，默认零耗时零资源；View 等纯元数据操作归 zero，默认也不需要资源。零耗时节点可显式请求资源，但不能凭空产生持续占用时间；依赖始终保留。不可将可能搬运数据的 reshape、contiguous、copy 一概标为 zero。

### 2026-10-31 硬件配置确认与实现

平台仓根 hardware/chip/ 保存可编辑 JSON；支持名称、文件名和显式外部路径，name 必须与文件 stem 一致，不扫描匹配。平台负责 schema、加载、选择与来源，算子仓只声明独立的不可变能力消费接口，不读取配置文件或反向导入平台。chip 包含按位宽索引的 cube/vec 峰值、HBM capacity_gb 与 bandwidth_tb_per_second（十进制），利用率为常数或 clamp(k*ln(原始 FLOPs/bytes)+b)。缺失位宽不自动替代，零工作量不求 log(0)。硬件在任务入口捕获前固定，负载仓不需要硬件，预测器接收完整能力并参与缓存键。与 vec_scale 同时启用会叠加。topo、多硬件选择策略和完整 roofline 算子模型不在本轮实现范围；HBM 带宽不替代通信或主机传输带宽。详见平台 hardware/README.md。

### 平台职责分层

平台包现按 api/frontend/graph/hardware/backend/config/results 组织，仍为单 wheel。公共图独立于负载适配与执行；入口编排消费各层，后端不反向依赖入口；任务参数归 config，最终结果归 results，领域结果留在后端模块。未实现的结果导出和通用工具不预建。当前路径以平台 docs/architecture.md 第 2 节和本仓 AGENTS.md 为准。

### 2026-10-31 预测输出与通信字节职责收敛

算子仓Estimate仅返回duration_us及keyword-only synthetic/details，移除category/resources；分类与执行资源由平台决定，未命中规则默认vec，不由预测模型补分类；节点和OpFeatures移除重复kind。平台不再读取/校验/传递上游communication_input_bytes或事件volume_bytes，不保留Communication.input_bytes；通信工作量由后续算子语义解析和模型计算。保留张量参数顺序、shape/dtype等语义事实及通信组/rank/owner。平台公共负载快照升级v3并拒绝v1/v2。训练仓假后端或捕获逻辑清理是后续任务，本轮不改训练仓。

### 单任务日志（2026-10-31）

统一训练入口默认在 training.output_dir 写 task.log；每个任务使用独立目录，无 inherit 或集中大文件。平台入口管理日志会话，子仓使用标准 logging，不反向依赖平台；会话收集 logging、Python warnings 和 print，结束后恢复进程设置。原生 C/C++／FD／子进程输出不实现，也不列为日志功能待办。批量／寻优将来负责目录和 worker 生命周期，不要求 worker 继承父进程 handler。底层评估接口只发日志，不创建会话。详情以平台 docs/task-logging.md 为准。

后续 topo 完成后，platform.transfers 作为过渡配置须迁移为 topo 配置及相应传输带宽／耗时工具 API，统一服务激活和优化器卸载。具体接口与兼容策略届时收敛；迁移要求见 docs/backend-requirements.md。
