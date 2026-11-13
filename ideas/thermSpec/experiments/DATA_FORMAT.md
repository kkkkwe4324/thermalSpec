# 统一原始数据格式 v1

从这一版起，每次运行保存不可覆盖的 `config.resolved.json`、`events.jsonl`、`status.json`。`events.jsonl` 是长期保留的事实记录；`summary.json`、CSV 和 PNG 均可从它重新计算。运行过程中每条事件写入后立即刷新并同步到磁盘，因此中断时仍能保留此前的事件。旧手机 Demo 的 `rounds.jsonl`/`phone_telemetry.csv` 仅作兼容输入，不作为新实验的主格式。

每行事件采用相同外壳：

```json
{"schema_version":1,"run_id":"example","index":0,"kind":"phone_telemetry","source":"phone_via_adb","utc":"2026-11-13T00:00:00+00:00","host_monotonic_ns":123456789,"elapsed_ns":0,"data":{"cpu_temp_c":35.0}}
```

`index` 是该运行的顺序号；`elapsed_ns` 以控制电脑本次运行的单调时钟起点为零。手机温度/频率是通过 ADB 读取后在控制电脑标记的时刻。不同设备的绝对时间戳不能直接相减；手机服务自己的耗时另放在 `data` 中。新事件类型只扩展 `kind` 和 `data`，不改变外壳；若破坏旧字段的含义，必须提高 `schema_version`。

| 事件 `kind` | 生产者 | 当前保存内容 | 后续投机解码应补的内容 |
|---|---|---|---|
| `run_start` / `run_end` | 控制器 | 模式、设备、配置哈希、结束原因 | 目标端会话信息、工作量完成情况 |
| `phone_telemetry` | 手机采样器 | CPU/电池温度、三簇当前频率及 policy 上限、热限制标志、PPM 上限读回、充电状态、USB 在线值 | 必要时增加其他经核实的传感器；保留原始单位与节点版本 |
| `frequency_request` / `frequency_clear` | 控制器 | 三簇请求的上限及清理事件 | 选择策略与决策依据 |
| `draft_request` | 手机草稿服务 | 提示词 ID、请求 token 数、实际生成数、请求起止和耗时、手机服务计算/prefill 时间、token IDs、采样设置读回 | 在完整投机链路中标出轮次、上下文位置和通信路径 |
| `guard_stop` / `telemetry_error` / `run_error` | 控制器 | 停止或失败原因及最近读数 | 关联目标端异常 |
| `spec_round`（待接入） | Orin 协调器 | — | prompt ID、轮次、K、提出/接受/最终提交 token 数、draft RTT、目标验证时间、有效 token IDs、上下文长度 |
| `channel_sample`（待接入） | 信道采样器 | — | 实测 RTT、带宽、抖动、超时、注入参数 |

`config.resolved.json` 保留本次实验参数、自动识别的 ADB 序列号和传输方式、完整 `configs/project.json` 副本及其 SHA-256、提示词哈希。全局配置规定模型/数据集/生成规则；具体实验配置只指定变化量。正式加载冻结的 WildChat 提示词时先验证文件 SHA-256，避免改了数据还沿用旧图。正式投机轮还须记录采样算法、temperature、top-p、随机种子、接受/拒绝、修正 token 和概率载荷字节数；当前 Demo 不产生这些字段。

目前只验证 `phone_draft` 事件，尚无 Orin `spec_round`、端到端有效 token 统计或信道采样。现在生成的 `amortized_ms_per_token` 是**手机草稿请求耗时/token**，不是正式投机解码 TPOT；分析脚本必须按模式筛选，不能混合比较。
