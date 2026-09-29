# quant-segment-comparator

用于正式比较两个互斥的定量研究细分人群，并控制批量筛选带来的假阳性。

## 适用请求

- “比较知道某 IP 和不知道的人有什么差异。”
- “看看当前玩家与流失玩家的行为偏好是否不同。”
- “只展示统计显著的人群特征。”
- “复核一组画像差异是不是抽样波动。”

## 推荐启动模板

```text
请使用 quant-segment-comparator。

数据：<路径和版本>
分析母体：<筛选条件>
A组：<定义>
B组：<定义>
主结果变量：<清单或 manifest>
固定控制变量：<例如年龄、性别>
检验族：<定义>
多重比较：Holm
敏感性分组：<可选>
正文纳入规则：校正后 p<0.05
是否允许业务建议：否
```

## 文件

- `SKILL.md`：完整工作规则。
- `references/variable-manifest-template.csv`：分析计划模板。
- `references/output-schema.md`：结果字段规范。
- `references/statistical-guardrails.md`：统计护栏。
- `scripts/compare_segments.py`：标准库辅助脚本。

## 边界

辅助脚本适合输入审计、二元描述比较、Fisher 精确检验和 p 值校正。含协变量的正式模型需要 statsmodels、R 或项目认可的统计环境；依赖缺失时不得把未调整结果冒充调整后结果。
