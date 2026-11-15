# 本地输入数据

这里保存冻结的提示词 JSONL 和数据集 manifest。仅本说明提交到 Git；生成方法见[负载与采样](../docs/WORKLOAD_AND_SAMPLING.md)。

从仓库根目录设置 `THERMSPEC_DATASET_PATH` 指向 `data/wildchat_1m_first_turn_v1.jsonl`，加载器会核对全局配置中的 SHA-256。
