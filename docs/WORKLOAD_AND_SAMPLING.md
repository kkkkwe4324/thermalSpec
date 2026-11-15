# 正式负载与采样口径

## 真实请求负载

数据集论文：[WildChat: 1M ChatGPT Interaction Logs in the Wild，ICLR 2024](https://openreview.net/pdf/40986fdeaa994d9dc8bbbe1a2c320eff8eff10a7.pdf)。

主数据源是 [WildChat-1M](https://huggingface.co/datasets/allenai/WildChat-1M) 中用户与 ChatGPT 模型交互的对话。研究者提供了收集对话的 ChatGPT 接口；这不是 OpenAI 官方产品的内部日志。我们只取每段对话首轮用户文本，不沿用原 ChatGPT 的回答。现有 SpecBench 四类提示词可作为附录中的标准基准对照，不再决定主实验的类别或比例。

`prepare_wildchat.py` 在官方数据集的公开 split 中，用固定随机种子抽取分散的行页，剔除源数据标记的 toxic/redacted 对话、乱码、重复文本和超过 12000 字符的极长请求。然后用项目指定版本的 Qwen2.5-7B 聊天模板计数，仅保留输入 token 数在 8 到 `context_size - formal_max_new_tokens` 之间的请求。固定取 64 条 calibration 和 192 条 test；保存原始行号、conversation hash、语言、原响应模型、输入 token 数、提示词、划分与顺序。筛选摘要保存在本地 `.manifest.json`。由于公开数据仍可能包含敏感文本，原始提示词文件和 manifest 不提交到仓库；只提交生成程序、源版本、筛选规则与冻结文件 SHA-256。

执行：

```powershell
python -m pip install -r requirements-data.txt
python -m framework.tools.prepare_wildchat --output data/wildchat_1m_first_turn_v1.jsonl
$env:THERMSPEC_DATASET_PATH = (Resolve-Path data/wildchat_1m_first_turn_v1.jsonl).Path
```

运行前须核对生成文件的 SHA-256 与 `configs/project.json` 相同。脚本通过 Hugging Face 文件系统直接读取指定 commit 的 Parquet 分片及所需行组，并校验分片总行数，因此数据仓库更新后仍能从旧 commit 重建。研究结果以冻结 JSONL 的哈希为准；若旧 commit 不再提供，则需从备份恢复相同哈希的冻结文件。

## 生成规则

为只比较 temperature/top-p 的效果，全局配置显式关闭 top-k 和 min-p，并设重复惩罚为 1.0。正式适配器还须核查运行时是否存在其他默认采样过滤器。

正式口径为 temperature 1.0、top-p 0.9、最多 128 个新 token。Qwen2.5-0.5B 与 7B 的模型输出维度分别为 151936 和 152064，但两个 tokenizer 都只有 151665 个可用 token ID。两端及 target-only 基线须先屏蔽超出 tokenizer 的填充 logits，再按同一套 temperature/top-p 规则变换和归一化。每一步草稿模型产生分布 $q$，目标模型产生分布 $p$；纯单轮校验器也允许概率数组长度不同，并按 token ID 将缺少的位置视为零概率。草稿抽样 token $x\sim q$ 后以 $\min(1,p(x)/q(x))$ 的概率接受；首次拒绝时从 $\operatorname{normalize}(\max(p-q,0))$ 抽样修正 token；全部接受时从目标模型多抽一个 token。这保证最终采样分布是目标模型的 $p$，不要求 $p=q$，也不要求同一随机种子下与 target-only 的 token 序列逐字相同。算法依据：[Leviathan 等，ICML 2023](https://proceedings.mlr.press/v202/leviathan23a.html)。

当前 `core/sampling.py` 已实现并测试统一 top-p 变换、单轮接受、首次拒绝时残差修正，以及全部接受后的目标 bonus token，**尚未接入手机草稿分布传输和 Orin 验证**。手机 `/completion` 接口设置 `n_probs` 时能返回前 N 个候选 token ID 和 logprob，但固定 N 不保证覆盖每一步完整的 top-p 支持，也不能仅靠修改 temperature 得到精确投机采样。接入时必须让草稿端返回每步完整的非零 $q$ 支持及概率，让目标端取得相应 $p$；两端 top-p 的排序、边界、归一化和特殊 token 规则须一致，并把额外传输字节与时间计入端到端指标。正式实验开始前以小词表穷举和真实单轮日志校验算法，再与 target-only 同采样设置比较。Greedy 只保留为诊断口径。

手机上实际部署的是 GGUF 量化模型；正式接入前仍须核对它与 Orin 模型的 token ID 映射、EOS 和填充 logits 屏蔽结果，不能只根据上游 Hugging Face 配置推定运行时完全一致。

如果 Orin 或手机接口暂时不能提供概率分布，实验状态必须标为“草稿 Demo”或“greedy 基线”，不能称为分布保持的正式投机实验。

### 概率载荷的本地单轮探针

运行 `python -m framework.tools.probe_probability_payload`。按屏蔽填充位后的 151665 个 token ID、K=4 计算，逐步传完整 fp32 草稿分布约 **2.43 MB/轮**；若每步 top-p 非零支持分别假设为 32、128、512 项，紧凑 JSON 的单轮载荷分别为 **1.8、7.9、36.6 KB**。这些支持大小是探针假设，不是手机模型实测；本地 JSON 编码平均耗时约 0.07、0.23、1.26 ms。Orin 当前 SSH 不可达，这些数字不包含手机生成概率、Wi-Fi 往返、目标验证或解码开销。下一步需要在真实单轮链路记录实际支持大小、载荷字节和 RTT，再决定精确采样的通信格式。

2026-11-14 用在线手机服务对短提示词做一次 1-token 接口探针：`n_probs=256` 的响应约 23.6 KB、请求墙钟约 319 ms，返回前 256 项的 $\sum\exp(\text{logprob})\approx0.976$；`n_probs=1024` 的响应约 93.3 KB、请求墙钟约 444 ms，质量和约 0.990。该次请求的前 256 项质量已超过 top-p 0.9，说明此例可从返回列表重建 top-p 支持；但其他上下文未验证，不得把这些数值当论文性能结果。正式适配器须检查每步返回的概率质量确实覆盖 top-p，并统一归一化规则。
