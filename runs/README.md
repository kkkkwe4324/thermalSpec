# 本地运行输出

每次运行用独立目录保存原始事件、配置快照、状态、摘要和图片。仅本说明提交到 Git。

```text
runs/
├─ motivation/exp1/<run_id>/
├─ method/<experiment>/<run_id>/
└─ reproductions/<paper>/<run_id>/
```

历史配置快照记录运行当时的路径，保留原文和哈希。分析旧数据时把实际运行目录传给对应实验的绘图函数；重跑实验使用当前实验配置，不能直接把旧配置快照当新配置覆盖执行。
