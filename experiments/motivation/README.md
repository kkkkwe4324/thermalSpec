# 动机实验代码入口

统一实验要求、标定变量和交付图片见[动机实验执行稿](../../docs/MOTIVATION_EXPERIMENTS.md)。每项实验只在自己的目录放配置、汇总和绘图代码；共用的设备连接、事件写盘和单次运行机制在 `framework/core/`、`framework/run_once.py`、`framework/run_matrix.py`。

| 实验 | 目录 | 当前状态 |
|---|---|---|
| 1. 持续推理的热退化 | [exp1_thermal_degradation](exp1_thermal_degradation/README.md) | 手机草稿 Demo、汇总和绘图已有；正式 Orin 验证待接入 |
| 2. 信道/热状态与最优 K | [exp2_channel_thermal_k](exp2_channel_thermal_k/README.md) | 预留 |
| 3. 频率上限与 K 联合选择 | [exp3_joint_f_k](exp3_joint_f_k/README.md) | 预留 |
| 4. 方法动机 | [exp4_method_motivation](exp4_method_motivation/README.md) | 仅预留，不定义实验 |

原始运行数据写到本地 `runs/motivation/<实验>/<run_id>/`，不与脚本混放。后续修改图片时从 `events.jsonl` 重建，不覆盖旧运行。
