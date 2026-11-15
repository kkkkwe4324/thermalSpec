# 全局配置

`project.json` v2 固定当前论文实验的模型版本、真实用户提示词数据集、采样规则和指标口径。各实验配置只写要改变的 K、频率档、信道、热状态、运行时长及重复次数。旧运行保存当时的完整副本和哈希，不能悄悄覆盖历史口径。

主负载改为 [WildChat-1M](https://huggingface.co/datasets/allenai/WildChat-1M) 的真实用户首轮提示词。冻结脚本 `python -m framework.tools.prepare_wildchat --output data/wildchat_1m_first_turn_v1.jsonl` 按固定种子选取 64 条校准、192 条测试提示词，剔除标记为 toxic/redacted、乱码、重复和超出目标模型上下文预算的输入。原始提示词文件及筛选 manifest 留在本机，不进入 Git；正式运行设置 `THERMSPEC_DATASET_PATH` 指向该 JSONL。加载器先校验 SHA-256，再按固定顺序取 calibration 或 test，不按任务类型配额。来源版本、筛选流程、模型聊天模板与数据限制见 [负载和采样口径](../docs/WORKLOAD_AND_SAMPLING.md)。

正式生成规则为温度 1.0、top-p 0.9 的**精确投机采样**：目标分布经过同样的采样变换后，采用 `min(1,p/q)` 接受测试与残差重采样。现有 `phone_draft` Demo 只有手机草稿服务，没有 Orin 目标验证，因此其输出不等于完整精确投机解码；Demo 的内联提示词和 8 token 仅用于链路检查，不替代正式的 128-token 上限。
