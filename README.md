# thermalSpec

研究手机草稿模型、远端目标模型组成的普通投机解码：当信道状态与手机温度变化时，如何共同选择手机 CPU 频率上限和投机长度 K，使端到端解码性能在持续运行中保持稳定。当前设备是 Redmi Note 10 Pro（Qwen2.5-0.5B-Instruct CPU 草稿）和 Jetson AGX Orin（Qwen2.5-7B-Instruct 目标）。这是待验证的研究问题；已有短测逐 token 对齐，但短输出的投机路径慢于目标模型单独解码，尚无加速或热态收益证据。

研究分三步：先用[动机实验 1–3](ideas/thermSpec/MOTIVATION_EXPERIMENTS.md)确认热退化、状态对最优 K 的影响、频率上限与 K 的联合效应；再设计同时感知信道与热状态的控制方法；最后在相同端到端指标与负载下比较固定配置和动态方法。实验 4 暂留给方法动机。每次运行保留原始数据，旧图可以重新生成。完整研究方向见 [idea 说明](ideas/thermSpec/README.md)，[代码分层](ideas/thermSpec/EXPERIMENT_FRAMEWORK_DESIGN.md)将单次运行、矩阵调度、动机实验分析和论文复现分开。

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

`run_once.py` 支持手机草稿端的真实单次运行、[统一事件日志](ideas/thermSpec/experiments/DATA_FORMAT.md)和自动出图；`run_matrix.py` 支持参数矩阵、温度回落后自动开始和断点续跑。[全局配置](ideas/thermSpec/experiments/configs/README.md)固定模型、数据集与生成规则。2026-11-13 已经通过 Wi‑Fi ADB 在手机未充电时完成短运行。**当前 `phone_draft` 模式不包含 Orin 验证，不能当作动机实验 1 的投机解码结果。** Orin 连通后需加入完整投机解码适配器，再正式采集实验数据。运行方法见 [实验入口说明](ideas/thermSpec/experiments/README.md)。
