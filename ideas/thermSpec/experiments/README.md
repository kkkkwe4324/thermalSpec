# 运行实验框架

从仓库根目录执行。先确认 Android Debug Bridge、手机草稿服务和 `adb forward tcp:18082 tcp:18082` 已就绪。需要 `matplotlib`（`python -m pip install -r requirements.txt`）。

```powershell
python -m ideas.thermSpec.experiments.run_once --config ideas/thermSpec/experiments/studies/motivation/exp1_thermal_degradation/configs/demo_phone.json --run-id my-first-run
python -m ideas.thermSpec.experiments.run_matrix --config ideas/thermSpec/experiments/studies/motivation/exp1_thermal_degradation/configs/demo_phone.json
```

Demo 的配置使用手机草稿服务，**没有 Orin 目标验证，不是正式的投机解码动机实验**。运行完成后，每次运行的原始数据、摘要和三行图写入 `ideas/thermSpec/experiments/runs/motivation/exp1/<run_id>/`。重复运行矩阵入口时跳过已完成任务；未完成的目录保留供检查，不自动覆盖。修改图片可从原始日志重新调用 `plot_run`。

整夜运行前把 `adb_path`、起始温度门槛、最高温停止线、运行时长、频率档和重复次数填成当前设备实测值。`run_matrix` 在每一项开始前等待 CPU 与电池温度连续满足门槛。当前 Demo 只验证冷却温度门槛，正式实验仍需加入热限制状态、频率恢复确认、Orin 完整投机解码适配器和频率档读回校验。
