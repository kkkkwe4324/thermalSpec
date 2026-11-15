# 我们自己的实验

- [motivation/](motivation/README.md)：动机实验 1–4 的配置、统计与绘图。
- [method/](method/README.md)：后续方法比较、基线和消融实验。

每项实验负责“比较什么、如何统计和画图”；[framework/](../framework/README.md)负责“如何运行、等待冷却和保存数据”。全局固定参数在 [configs/project.json](../configs/project.json)，实验自己的矩阵在各自的 `configs/`。
