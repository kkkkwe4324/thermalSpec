# 动机实验 1：持续推理的热退化

[执行要求与交付图片](../../../docs/MOTIVATION_EXPERIMENTS.md)；[Demo 配置](configs/demo_phone.json)。本目录的 `summarize.py` 汇总原始事件，`plot_run.py` 画单次运行图，`plot_comparison.py` 画组间对照图。

当前 Demo 仅运行手机草稿模型，不含 Orin 目标验证，因此不能作为正式投机解码 TPOT 结果。正式配置在完成设备和温度标定后放入 `configs/`，继续复用本目录的汇总与绘图入口。
