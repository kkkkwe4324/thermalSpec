# 全局配置

`project.json` 固定当前论文实验的模型版本、数据集身份与筛选规则、生成规则和指标口径。各实验配置只写要改变的 K、频率档、信道、热状态、运行时长及重复次数。修改全局配置需提高 `config_version`，旧运行保存当时的完整副本和哈希，不能悄悄覆盖历史口径。

正式数据集文件不随仓库发布。运行正式实验时把 `THERMSPEC_DATASET_PATH` 指向本地冻结的 `specbench_4task_prompts.jsonl`；`load_calibration_prompts` 已实现 SHA-256 校验和四类任务各 2 条的 calibration 子集选择。接入 Orin 的正式运行入口仍需调用它，并另行指定正式测试子集。Demo 的内联提示词和 8 token 仅用于链路检查，不替代这份配置中的正式 128-token 上限。
