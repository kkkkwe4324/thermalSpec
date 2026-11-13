# 运行实验框架

从仓库根目录执行。先确认 Android Debug Bridge 和手机草稿服务已就绪；单次运行会为选中的设备建立端口转发。需要 `matplotlib`（`python -m pip install -r requirements.txt`）。固定模型、数据集及生成规则见 [全局配置](configs/README.md)，长期保留的数据字段见 [统一数据格式](DATA_FORMAT.md)。

```powershell
python -m ideas.thermSpec.experiments.run_once --config ideas/thermSpec/experiments/studies/motivation/exp1_thermal_degradation/configs/demo_phone.json --run-id my-first-run
python -m ideas.thermSpec.experiments.run_matrix --config ideas/thermSpec/experiments/studies/motivation/exp1_thermal_degradation/configs/demo_phone.json
```

Demo 的配置使用手机草稿服务，**没有 Orin 目标验证，不是正式的投机解码动机实验**。运行完成后，每次运行的 `events.jsonl` 会持续写入 `ideas/thermSpec/experiments/runs/motivation/exp1/<run_id>/`，结束后生成摘要和三行图。重复运行矩阵入口时跳过已完成任务；未完成的目录保留供检查，不自动覆盖。修改图片可从原始事件重新调用 `plot_run`。

无线调试：手机与电脑的网络需互通。先在手机“无线调试”页面读取当前 IP:端口，执行 `adb connect <IP:端口>`，再用 `adb devices -l` 确认在线。若同时连接 USB 与 Wi‑Fi 两个传输，在实验配置的 `adb_serial` 填写无线设备的完整 `IP:端口`；照片中的端口只代表当时状态，可能变化。`require_unplugged=true` 会拒绝 USB ADB，并在采样中检查 `usb_online=0`。2026-11-13 已通过 Wi‑Fi ADB 访问手机 root 遥测及回环草稿服务；这不等于 Orin 也已经连通。

整夜运行前把 `adb_path`、起始温度门槛、最高温停止线、运行时长、频率档和重复次数填成当前设备实测值。`run_matrix` 在每一项开始前等待 CPU 与电池温度连续满足门槛。当前 Demo 只验证冷却温度门槛，正式实验仍需加入热限制状态、频率恢复确认、Orin 完整投机解码适配器和频率档读回校验。
