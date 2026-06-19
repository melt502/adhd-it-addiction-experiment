# ADHD/网络成瘾实验数据清洗报告

## 1. 本轮清洗结论

- 已将问卷主表、Stroop、BART、n-back、DDT、点探测/停止信号表，以及 CPT 原始 Word 报告合并为一张去标识化分析表。

- CPT 原始 ZIP 已成功读取；使用 antiword 提取了每个 `.doc` 报告中的 Q 值、控制力、注意力、多动事件、持续性等指标。

- 之前“ADHD 特质与实验任务关系弱”的说法只能作为未清洗初步现象；本报告不把它当结论。清洗后应以 `cleaned_questionnaire_task_spearman_all.csv` 和 `cleaned_CPT_N_vs_ADHD_effect_sizes.csv` 为准。

- 分组代码 1–6 的含义目前按口头说明暂定；正式论文中建议优先使用 `CPT_label_clean` 的 N/I/C 做分类，或把 1–6 作为待确认变量。

- `.1` 后缀总分与主问卷总分明显不一致，本轮清洗保留审计但不用于主分析。


## 2. 量表名称和当前解释

- `CIAS/CIASSUM/I1–I26`：CIAS，中文网络成瘾相关量表；本数据中总分等于 I1–I26 求和。

- `Young/YOUNGSUM/Y1–Y8`：Young 网络成瘾诊断问卷；本数据中总分等于 Y1–Y8 求和。

- `DSM/DSMSUM1/DSMSUM2/D1–D22`：DSM 相关网络/游戏成瘾诊断条目；D1–D9 对应 DSMSUM1，D10–D22 对应 DSMSUM2。

- `CAARS/CAARSSUM/C1–C26`：CAARS/ADHD 特质量表；前面说的 `C总分` 应理解为 CAARS 总分，而不是 CIAS。

- 反向计分：当前文件中各总分都等于条目直接求和；如果原问卷有反向题，也已经体现在编码后的条目中。没有原始问卷手册前，不应再额外反向。


## 3. CPT 标签解释

- `N`：Normal/正常。

- `I`：Inattentive/注意缺陷型。

- `C`：Combined/混合型。

- `I?`、`C?`：疑似注意缺陷型/疑似混合型，正式主分析建议先作为不确定分类。

- `?`：未知或无法确定。


## 4. 样本和任务可用性

| task_block     |   n_liberal_available |   n_strict_valid |   n_total_experiment_ids |   strict_loss |
|:---------------|----------------------:|-----------------:|-------------------------:|--------------:|
| Stroop         |                   126 |              124 |                      157 |             2 |
| BART           |                   111 |              111 |                      157 |             0 |
| n-back         |                   109 |              109 |                      157 |             0 |
| DDT            |                   126 |               96 |                      157 |            30 |
| Dot/Stop lower |                   111 |              111 |                      157 |             0 |
| Dot/Stop upper |                   109 |              109 |                      157 |             0 |
| CPT parsed doc |                   112 |              112 |                      157 |             0 |



## 5. CPT 分类计数

| variable        | value   |   n |
|:----------------|:--------|----:|
| CPT_label_clean | ?       |   3 |
| CPT_label_clean | C       |  52 |
| CPT_label_clean | C?      |   5 |
| CPT_label_clean | I       |  13 |
| CPT_label_clean | I?      |   3 |
| CPT_label_clean | N       |  33 |
| CPT_label_clean | nan     |  48 |



## 6. 量表信度/计分审计

| scale     |   n_items |   n_total_nonmissing |   total_min |   total_max |   n_itemsum_total_discrepancies |   max_abs_itemsum_total_diff |   cronbach_alpha_raw_items |
|:----------|----------:|---------------------:|------------:|------------:|--------------------------------:|-----------------------------:|---------------------------:|
| CIAS      |        26 |                  157 |          26 |         101 |                               0 |                            0 |                   0.953338 |
| Young     |         8 |                  157 |           0 |           8 |                               0 |                            0 |                   0.767913 |
| DSM_part1 |         9 |                  157 |           0 |           9 |                               0 |                            0 |                   0.729393 |
| DSM_part2 |        13 |                  157 |           0 |          13 |                               0 |                            0 |                   0.741734 |
| CAARS     |        26 |                  157 |           5 |          61 |                               0 |                            0 |                   0.903491 |



## 7. 清洗后探索性结果提示

### CAARS_total 与实验/CPT指标的 Spearman 相关 Top 12

| metric                         |   spearman_rho |   p_value |   n |
|:-------------------------------|---------------:|----------:|----:|
| stroop_rt_mean_all             |       0.223243 | 0.0119804 | 126 |
| dot_xia_yizhixingxia           |       0.197442 | 0.0377902 | 111 |
| stroop_rt_spread_maxmin        |       0.184081 | 0.0390767 | 126 |
| cold_exec_index_z              |       0.18251  | 0.0400024 | 127 |
| cpt_control_combined           |      -0.18068  | 0.0565976 | 112 |
| cpt_hyperactivity_quotient     |      -0.173571 | 0.0672181 | 112 |
| bart_explosions                |      -0.16087  | 0.0916634 | 111 |
| nback_rt_load_increase_3minus0 |      -0.160701 | 0.0950593 | 109 |
| attention_cpt_index_z          |       0.155558 | 0.101465  | 112 |
| bart_adj_avg_pumps             |      -0.145337 | 0.128013  | 111 |
| ddt_fit_r                      |      -0.134165 | 0.160357  | 111 |
| ddt_k                          |       0.127946 | 0.180816  | 111 |


### CPT: Normal vs I/C 的效应量 Top 12，d 为 ADHD(I/C) - Normal

| metric                      |   N_normal |   N_ADHD_IC |   mean_Normal |   mean_ADHD_IC |   cohen_d_ADHD_minus_Normal |   mannwhitney_p |
|:----------------------------|-----------:|------------:|--------------:|---------------:|----------------------------:|----------------:|
| cpt_control_combined        |         33 |          65 |    103.394    |     77.2308    |                   -1.6062   |     1.25497e-10 |
| cpt_attention_combined      |         33 |          65 |    101.848    |     76.7538    |                   -1.23336  |     3.39417e-07 |
| nback_acc                   |         32 |          63 |      0.941281 |      0.912937  |                   -0.737649 |     0.00124994  |
| attention_cpt_index_z       |         33 |          65 |     -0.25171  |      0.0951979 |                    0.669153 |     0.000698206 |
| bart_adj_avg_pumps          |         33 |          65 |     35.0047   |     27.92      |                   -0.56278  |     0.0104778   |
| bart_total_earnings         |         33 |          65 |     33.8394   |     28.6535    |                   -0.510911 |     0.00796202  |
| hot_reward_index_z          |         33 |          65 |      0.165406 |     -0.143182  |                   -0.494658 |     0.0506437   |
| cold_exec_index_z           |         33 |          65 |     -0.162878 |      0.058961  |                    0.408893 |     0.0236545   |
| nback_acc_load_drop_3minus0 |         32 |          63 |     -0.132719 |     -0.160952  |                   -0.402998 |     0.063489    |
| CAARS_total                 |         33 |          65 |     31.7879   |     35.4       |                    0.315679 |     0.166262    |
| stroop_rt_spread_maxmin     |         33 |          65 |    240.87     |    203.917     |                   -0.3045   |     0.60923     |
| cpt_hyperactivity_quotient  |         33 |          65 |     99.9091   |     94.3846    |                   -0.300039 |     0.460376    |



## 8. 建议的主分析原则

1. 第一篇论文主分类建议用 `CPT_label_clean` 中确定的 N/I/C；`I?`、`C?`、`?` 用于敏感性分析。

2. 问卷中的 ADHD 特质主变量用 `CAARS_total`；网络成瘾主变量用 `CIAS_total`，辅以 `Young_total` 和 `DSM_total1/2`。

3. 实验任务用任务特异 QC flag，不建议一刀切删除整行。

4. CPT 原始报告本身可以作为持续注意/分类依据，也可作为真实行为指标。

5. 正式论文中对“ADHD 特质与实验任务关系弱/强”的判断，应基于清洗后的相关、效应量和稳健性分析，不再基于初步审计。
