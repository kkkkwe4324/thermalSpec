# 已验证设备与运行路径

这份概要来自 2026-11-08 原 `paperSearch/ideas/thermSpec` 工作区的设备记录；完整原始日志仍保存在原工作区。本仓库仅保留启动实验框架所需的背景。

| 角色 | 设备与模型 | 当前验证情况 |
|---|---|---|
| 草稿端 | Redmi Note 10 Pro `chopin`，Android 13；`llama.cpp` CPU 版；Qwen2.5-0.5B-Instruct GGUF Q4_K_M | 模型位于手机 `/data/local/tmp/thermSpec/`，服务监听回环地址 18082；本地经 `adb forward` 可访问 `/health` 和 `/completion`。 |
| 目标端 | Jetson AGX Orin `orin4tb`；Qwen2.5-7B-Instruct CUDA 模型 | 原工作区的 D-PROMISE 独立副本在 `/home/why/thermSpec/repro/`；此前 4 条短提示词的 greedy 输出逐 token 对齐。 |

手机 CPU 三簇的频率上限可以请求，但不能据请求值推断实际锁频；厂商控制可能清除请求，热管理也可能覆盖它。接口细节见[频率控制矩阵](FREQUENCY_CONTROL_MATRIX_2026-11-08.md)。`mtktscpu` 与电池温度均可读取。手机 GPU/NPU 本轮不作为动作。

此前 `K=2`、每条最多 8 个输出 token 的 4 条短提示词中，手机投机路径比 Orin target-only 慢；因此当前没有加速证据。原短测在电池 38°C、`mtktscpu` 65°C 或 CPU thermal cap 出现时停止，无法直接用于“限频之后”的持续实验。正式运行必须单独标定起始状态、热限频事件和硬停止线。

2026-11-13 的环境检查：手机通过 USB 可见，草稿服务 `/health` 可达；Orin 的 Tailscale 地址能收到中继 ping，但 SSH 连接超时。因此本仓库当前 Demo 只运行真实手机草稿服务，尚未接入 Orin 目标验证。
