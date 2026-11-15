# thermalSpec

研究手机草稿模型、远端目标模型组成的普通投机解码：当信道状态与手机温度变化时，如何共同选择手机 CPU 频率上限和投机长度 K，使端到端解码性能在持续运行中保持稳定。当前设备是 Redmi Note 10 Pro（Qwen2.5-0.5B-Instruct CPU 草稿）和 Jetson AGX Orin（Qwen2.5-7B-Instruct 目标）。这是待验证的研究问题；已有短测逐 token 对齐，但短输出的投机路径慢于目标模型单独解码，尚无加速或热态收益证据。

研究分三步：先用[动机实验 1–3](docs/MOTIVATION_EXPERIMENTS.md)确认热退化、状态对最优 K 的影响、频率上限与 K 的联合效应；再设计同时感知信道与热状态的控制方法；最后在相同端到端指标与负载下比较固定配置和动态方法。实验 4 暂留给方法动机。每次运行保留原始数据，旧图可以重新生成。完整研究方向见 [idea 说明](docs/IDEA.md)，[代码分层](docs/EXPERIMENT_FRAMEWORK_DESIGN.md)将单次运行、矩阵调度、动机实验分析和论文复现分开。

找代码请从[论文复现目录](reproductions/README.md)或[动机实验目录](experiments/motivation/README.md)进入；两个索引都列出各子目录的当前状态和文件放置位置。

## 仓库目录

```text
thermalSpec/
├─ README.md                           项目介绍、目录导航与快速开始
├─ docs/                               研究与实验文档
│  ├─ IDEA.md                          研究问题、相关论文与当前进度
│  ├─ MOTIVATION_EXPERIMENTS.md         实验要求、标定变量与交付图片
│  ├─ SETUP.md                         设备与模型部署
│  ├─ DATA_FORMAT.md                   原始数据格式
│  └─ WORKLOAD_AND_SAMPLING.md          数据集与采样设置
├─ configs/project.json                全局固定配置
├─ framework/                          共用运行框架
│  ├─ run_once.py                      跑一次、写盘、调用本次绘图
│  ├─ run_matrix.py                    参数矩阵、冷却等待与续跑
│  ├─ core/                            设备、采样、状态门槛和日志
│  └─ tools/                           数据集准备与诊断工具
├─ experiments/                        我们自己的实验
│  ├─ motivation/
│  │  ├─ exp1_thermal_degradation/     已有 Demo、统计与绘图
│  │  │  ├─ configs/demo_phone.json
│  │  │  ├─ summarize.py
│  │  │  ├─ plot_run.py
│  │  │  └─ plot_comparison.py
│  │  ├─ exp2_channel_thermal_k/       预留配置、统计与绘图位置
│  │  ├─ exp3_joint_f_k/
│  │  └─ exp4_method_motivation/       仅预留，设计待定
│  └─ method/                          后续方法、基线与消融
├─ reproductions/                      其他论文的复现
│  ├─ eardvfs/                         每篇有 src/、configs/、analysis/
│  ├─ pelm/
│  └─ banditspec/
├─ data/                               本地输入数据，仅 README 入 Git
├─ runs/                               本地运行记录，仅 README 入 Git
└─ tests/                              共用框架与采样的测试
```

师弟新增实验主要修改 `experiments/` 中自己的配置和分析脚本；共用的设备访问、持续写盘、冷却与批量调度放在 `framework/`。每篇论文的复现保持独立。每次运行用 `runs/` 中独立的 run_id 保存原始记录，后续可以直接重画旧图。

## 快速开始

从仓库根目录执行，先按[运行说明](framework/README.md)准备手机服务并填写设备参数：

```powershell
python -m pip install -r requirements.txt
python -m framework.run_once --config experiments/motivation/exp1_thermal_degradation/configs/demo_phone.json --run-id my-first-run
python -m framework.run_matrix --config experiments/motivation/exp1_thermal_degradation/configs/demo_phone.json
```

上述入口目前是手机草稿 Demo；完整 Orin 验证仍待接入。复现与实验 2–4 的占位目录不代表已有可运行实现。

## 相关论文与边界

| 论文 | 与本研究的关系 |
|---|---|
| [EarDVFS, ICCAD 2025](https://doi.org/10.1109/ICCAD66269.2025.11240765) | 手机持续负载下的温控与主动频率上限；没有投机解码。 |
| [PELM, SenSys 2026](https://arxiv.org/abs/2609.09662) | Orin 上将 DVFS 与自投机的计算深度等控制量联合优化；我们的草稿和目标在两台设备上，使用独立草稿模型。 |
| [BanditSpec, ICML 2025](https://proceedings.mlr.press/v267/hou25h.html) | 普通投机解码动态选长度/配置；不直接处理手机热状态与 DVFS。 |
| [FlexSpec, IEEE TMC 2026](https://doi.org/10.1109/TMC.2026.3683574) | 端云投机解码的信道感知 K 选择，是直接相关工作；正式版中的热/DVFS 范围还需核实。 |
| [SpecDec++, COLM 2025](https://openreview.net/pdf/20e04fa6a4fd4676e6c928f26603189768563b4a.pdf) | 依据接受概率动态停止草稿，属于 K 控制的方法邻居。 |

不能仅凭这些论文声称本项目的方法具有新颖性；后续需用正式版本和实际实验进一步对照。较完整的检索与阅读状态保留在原 `paperSearch/ideas/thermSpec/papers.md`。

## 当前代码状态

`run_once.py` 支持手机草稿端的真实单次运行、[统一事件日志](docs/DATA_FORMAT.md)和自动出图；`run_matrix.py` 支持参数矩阵、温度回落后自动开始和断点续跑。[全局配置](configs/README.md)固定模型、数据集与生成规则。2026-11-13 已经通过 Wi‑Fi ADB 在手机未充电时完成短运行。**当前 `phone_draft` 模式不包含 Orin 验证，不能当作动机实验 1 的投机解码结果。** Orin 连通后需加入完整投机解码适配器，再正式采集实验数据。运行方法见 [实验入口说明](framework/README.md)。
