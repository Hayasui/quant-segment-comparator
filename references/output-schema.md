# 结果输出字段

## 必需字段

| 字段 | 含义 |
|---|---|
| `analysis_id` | 唯一分析编号 |
| `variable_id` | 数据变量 |
| `question` | 题号或指标组 |
| `item_label` | 面向读者的选项名 |
| `variable_type` | binary / nominal / ordinal / continuous |
| `population` | 分析母体定义 |
| `group_a_definition` | A组定义 |
| `group_b_definition` | B组定义 |
| `n_a` / `n_b` | 题目级有效分母 |
| `value_a` / `value_b` | 比例、均值或其他主要统计量 |
| `raw_difference` | 未调整差值，二元结果默认百分点差 |
| `effect_measure` | OR、均值差等 |
| `adjusted_effect` | 调整后效应量 |
| `ci_low` / `ci_high` | 95%置信区间 |
| `p_raw` | 原始p值 |
| `multiplicity_family` | 检验族 |
| `adjustment_method` | Holm、BH等 |
| `p_adjusted` | 校正后p值 |
| `model_status` | ok / sparse / separated / failed / descriptive_only |
| `include_in_body` | 是否满足预定正文纳入规则 |
| `limitation` | 条件出示、小样本、缺失等说明 |

## 报告规则

- 完整 CSV 保留全部结果，包括不显著项。
- 正文表只筛选 `include_in_body = true`。
- 正文筛选后仍保留原检验族和校正后 p 值，不能对筛选结果重新校正。
- 条件题必须在 `population` 或 `limitation` 标注真实适用人群。
