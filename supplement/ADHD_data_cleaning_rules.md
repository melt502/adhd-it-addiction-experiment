# ADHD/网络成瘾实验数据清洗规则文档

本文档根据 `clean_adhd_experiment.py` 脚本整理，说明本轮数据清洗、合并、质控、去标识化与输出规则。适用于 ADHD/网络成瘾问卷数据、实验任务数据和 CPT 原始报告的清洗复现与论文方法描述。

## 1. 数据源

脚本以 `/mnt/data` 为输入输出目录，读取以下数据源：

| 数据类型 | 文件/工作表 | 主要用途 |
|---|---|---|
| 被试主表 | `被试信息汇总表.sav` | 人口学信息、问卷总分、主被试编号 |
| Stroop | `Stroop数据整理(1).xls` / `原始录入` | Stroop 准确率与反应时指标 |
| BART | `BART数据整理(1).xls` / `原始录入` | 风险决策任务收益、爆炸数、平均打气次数 |
| n-back | `n-back数据整理.xls` / `原始录入` | 工作记忆准确率、反应时、d′、β |
| DDT | `DDT数据整理.xls` / `原始录入` | 延迟折扣任务原始整理表、编号映射、问卷条目与总分 |
| DDT | `DDT数据整理.xls` / `整理处理用` | DDT 处理后主指标，优先用于 DDT 主分析 |
| DDT | `DDT数据整理.xls` / `踢除数据` | DDT 被踢除数据记录，保留用于审计 |
| 点探测/停止信号 | `停止信号 点探测.xlsx` / `yuxia` | 下方条件点探测/停止信号相关指标 |
| 点探测/停止信号 | `停止信号 点探测.xlsx` / `yushang` | 上方条件点探测/停止信号相关指标 |
| CPT 原始报告 | `CPT原始数据.zip` 中的 `.doc` 文件 | 解析 CPT 报告中的控制力、注意力、多动等指标 |

## 2. ID 标准化与数据合并规则

### 2.1 主 ID

- `被试信息汇总表.sav` 中的 `beishibianhao` 转为数值型，并保存为 `main_id`。
- `DDT数据整理.xls` 的 `原始录入` 工作表中：
  - `实验编号` 转为 `experiment_id`；
  - `编号` 转为 `main_id`。
- 以 DDT 原始表中的 `experiment_id`—`main_id` 去重映射作为基础合并框架。

### 2.2 实验 ID

以下数据表统一生成 `experiment_id`：

- Stroop、BART、n-back、DDT：使用 `实验编号`。
- 点探测/停止信号表：使用 `Subject`。
- CPT 原始 `.doc` 文件：从文件名中提取第一个数字作为 `experiment_id`。

所有 ID 均转换为数值型；无法转换者置为缺失值。

### 2.3 合并策略

- 基础表以 DDT 原始表提供的 `experiment_id`—`main_id` 映射为准。
- 主表 SAV 信息按 `main_id` 合并。
- 实验任务数据按 `experiment_id` 合并。
- CPT 解析结果按 `experiment_id` 合并。
- 合并方式均为左连接，尽量保留基础样本，不因某个任务缺失而删除整行。

## 3. 去标识化规则

输出分析表只保留数值型连接 ID：

- `main_id`
- `experiment_id`

明确不输出以下直接身份识别信息：

- 姓名
- 电话
- 班级
- 专业
- 其他脚本未列入 `primary_cols` 或任务指标列的个人识别字段

脚本注释明确说明：最终输出保留 ID 仅作为匿名化连接键，不包含姓名、联系方式、班级、专业等信息。

## 4. 问卷变量清洗与计分规则

### 4.1 保留的问卷主变量

| 变量 | 来源 | 含义 |
|---|---|---|
| `CIAS_total` | 实验文件优先，SAV 备用 | CIAS 网络成瘾总分 |
| `Young_total` | 实验文件优先，SAV 备用 | Young 网络成瘾诊断问卷总分 |
| `DSM_total1` | 实验文件优先，SAV 备用 | DSM 相关条目 D1–D9 总分 |
| `DSM_total2` | 实验文件优先，SAV 备用 | DSM 相关条目 D10–D22 总分 |
| `CAARS_total` | 实验文件优先，SAV 备用 | CAARS/ADHD 特质量表总分 |

### 4.2 主总分选择规则

问卷主分析总分优先使用实验整理表中的总分；若实验整理表缺失，则使用 SAV 主表中的总分：

- `CIAS_total = CIAS_total_file` 优先，否则 `CIAS_total_sav`
- `Young_total = Young_total_file` 优先，否则 `Young_total_sav`
- `DSM_total1 = DSM_total1_file` 优先，否则 `DSM_total1_sav`
- `DSM_total2 = DSM_total2_file` 优先，否则 `DSM_total2_sav`
- `CAARS_total = CAARS_total_file` 优先，否则 `CAARS_total_sav`

### 4.3 `.1` 后缀总分处理规则

DDT 原始表中的以下 `.1` 后缀总分仅保留用于审计，不作为主分析变量：

- `CIASSUM.1`
- `YOUNGSUM.1`
- `DSMSUM1.1`
- `DSMSUM2.1`
- `CAARSSUM.1`

脚本将其重命名为 `*_alt_CPTmerge`，并输出审计文件 `alternative_totals_do_not_use_audit.csv`。

处理原则：

- 不进入主分析；
- 仅比较其与主总分的差异、最大绝对差、相关；
- 结论为“疑似另一次合并/中间表，与原始问卷总分不一致”。

### 4.4 问卷总分范围检查

脚本对主问卷总分设置如下范围检查。缺失值视为范围检查通过，不额外标记为错误。

| 变量 | 合理范围 | 生成 QC 变量 |
|---|---:|---|
| `CIAS_total` | 26–104 | `CIAS_total_range_ok` |
| `Young_total` | 0–8 | `Young_total_range_ok` |
| `DSM_total1` | 0–9 | `DSM_total1_range_ok` |
| `DSM_total2` | 0–13 | `DSM_total2_range_ok` |
| `CAARS_total` | 0–78 | `CAARS_total_range_ok` |

### 4.5 量表计分审计规则

脚本使用 DDT 原始表中的条目重新计算总分，并与文件中的总分比较：

| 量表 | 条目 | 总分列 | 理论范围 |
|---|---|---|---:|
| CIAS | `I1`–`I26` | `CIASSUM` | 26–104 |
| Young | `Y1`–`Y8` | `YOUNGSUM` | 0–8 |
| DSM part 1 | `D1`–`D9` | `DSMSUM1` | 0–9 |
| DSM part 2 | `D10`–`D22` | `DSMSUM2` | 0–13 |
| CAARS | `C1`–`C26` | `CAARSSUM` | 0–78 |

审计内容包括：

- 条目数量；
- 总分非缺失样本量；
- 总分最小值、最大值；
- 条目求和与总分不一致的样本数；
- 最大绝对差；
- 原始条目的 Cronbach’s α；
- 完整条目样本量。

反向计分原则：

- 当前脚本判断文件中的总分等于当前条目直接求和；
- 若原问卷存在反向题，推定该文件中的条目已经完成编码；
- 在没有原始问卷手册前，不再额外反向计分。

## 5. 分组变量与 CPT 分类规则

### 5.1 实验分组代码

脚本将 `分组` 重命名为 `group_code_raw`，再转换为数值型 `group_code`。

当前分组标签为暂定解释：

| `group_code` | 暂定标签 |
|---:|---|
| 1 | 正常/对照?（待确认） |
| 2 | 注意缺陷型?（待确认） |
| 3 | 多动冲动型?（待确认） |
| 4 | 混合型?（待确认） |
| 5 | 注意缺陷型+网络成瘾?（待确认） |
| 6 | 多动冲动型+网络成瘾?（待确认） |

派生变量：

- `group_label_tentative`：暂定分组标签；
- `group_adhd_like_tentative`：`group_code` 为 2、3、4、5、6 时为真；
- `group_ia_comorbid_tentative`：`group_code` 为 5、6 时为真。

注意：脚本明确提示该分组映射仍需确认，正式分析建议优先使用 CPT 标签分类，或将 1–6 作为待确认变量。

### 5.2 CPT 标签清洗

原始 `CPT` 字段重命名为 `CPT_label_raw`。

清洗规则：

- 转为字符串；
- 去除首尾空格；
- 中文问号 `？` 替换为英文问号 `?`；
- 空字符串和字符串 `nan` 置为缺失。

生成变量：

- `CPT_label_clean`
- `CPT_label_certainty`
- `CPT_class_strict`
- `CPT_class_broad`
- `CPT_ADHD_strict`
- `CPT_ADHD_broad`

### 5.3 CPT 标签解释

| 原标签 | 严格分类 `CPT_class_strict` | 宽松分类 `CPT_class_broad` | 确定性 |
|---|---|---|---|
| `N` | `Normal` | `Normal` | `certain` |
| `I` | `Inattentive` | `Inattentive` | `certain` |
| `C` | `Combined` | `Combined` | `certain` |
| `I?` | 缺失 | `Inattentive_uncertain` | `uncertain_subtype` |
| `C?` | 缺失 | `Combined_uncertain` | `uncertain_subtype` |
| `?` | 缺失 | 缺失 | `unknown` |

ADHD 二分类规则：

- `CPT_ADHD_strict`：`I` 或 `C` 为 ADHD；`N` 为非 ADHD；`I?`、`C?`、`?`、缺失不纳入严格分类。
- `CPT_ADHD_broad`：`I`、`C`、`I?`、`C?` 均作为 ADHD 或疑似 ADHD；`N` 为非 ADHD；`?` 和缺失设为缺失。

## 6. CPT 原始报告解析规则

### 6.1 解压与读取

- 若存在 `CPT原始数据.zip`，脚本将其解压到 `CPT_zip_extracted_clean`。
- 搜索解压目录下所有 `.doc` 文件。
- 使用 `antiword -m UTF-8` 将 `.doc` 转为文本。
- 每个文件从文件名中提取第一个数字作为 `experiment_id`。

### 6.2 解析字段

脚本从 CPT 报告文本中解析以下信息：

基本报告信息：

- `cpt_report_number`：报告编号；
- `cpt_report_sex`：报告性别；
- `cpt_report_age_text`：原始年龄文本；
- `cpt_report_age_years`：换算成年龄，岁 + 月/12 + 天/365.25；
- `cpt_report_date`：报告日期。

理解能力：

- `cpt_comprehension_auditory`
- `cpt_comprehension_visual`

控制力与注意力：

- `cpt_control_auditory`
- `cpt_control_visual`
- `cpt_control_combined`
- `cpt_attention_auditory`
- `cpt_attention_visual`
- `cpt_attention_combined`

控制相关商数：

- `cpt_prudence_auditory`
- `cpt_prudence_visual`
- `cpt_consistency_auditory`
- `cpt_consistency_visual`
- `cpt_persistence_auditory`
- `cpt_persistence_visual`

注意相关商数：

- `cpt_alertness_auditory`
- `cpt_alertness_visual`
- `cpt_attention_q_auditory`
- `cpt_attention_q_visual`
- `cpt_speed_auditory`
- `cpt_speed_visual`

其他 CPT 指标：

- `cpt_balance`
- `cpt_agility_auditory`
- `cpt_agility_visual`
- `cpt_sustained_auditory`
- `cpt_sustained_visual`
- `cpt_sensorimotor_auditory`
- `cpt_sensorimotor_visual`
- `cpt_hyperactivity_events`
- `cpt_hyperactivity_quotient`

### 6.3 CPT 解析成功判定

每个 CPT 文件生成 `cpt_parse_ok`。

判定规则：只要解析结果中存在以下任一类实质性指标，即视为解析成功：

- 以 `cpt_control` 开头的指标；
- 以 `cpt_attention` 开头的指标；
- 以 `cpt_hyperactivity` 开头的指标。

合并到主表后生成：

- `cpt_doc_valid = cpt_parse_ok`，缺失时填充为 `False`。

### 6.4 CPT 文件去重

若同一个 `experiment_id` 对应多个 CPT 文件：

- 按 `experiment_id` 和 `cpt_file` 排序；
- 每个 `experiment_id` 仅保留排序后的第一个文件。

## 7. 实验任务清洗与质控规则

脚本对每个任务同时设置两类可用性标记：

- `*_valid_liberal`：宽松可用，只要该任务至少有一个关键指标非缺失；
- `*_valid_strict`：严格可用，除关键指标非缺失外，还需通过范围、反应时或准确率规则。

### 7.1 Stroop

#### 7.1.1 原始字段

读取字段：

- 准确率：`b1acc`, `b2acc`, `y1acc`, `y2acc`, `z1acc`, `z2acc`
- 反应时：`b1rt`, `b2rt`, `y1rt`, `y2rt`, `z1rt`, `z2rt`

所有字段转为数值型，并加前缀 `stroop_`。

#### 7.1.2 派生指标

| 指标 | 计算规则 |
|---|---|
| `stroop_b_acc_mean` | `stroop_b1acc` 与 `stroop_b2acc` 均值 |
| `stroop_y_acc_mean` | `stroop_y1acc` 与 `stroop_y2acc` 均值 |
| `stroop_z_acc_mean` | `stroop_z1acc` 与 `stroop_z2acc` 均值 |
| `stroop_b_rt_mean` | `stroop_b1rt` 与 `stroop_b2rt` 均值 |
| `stroop_y_rt_mean` | `stroop_y1rt` 与 `stroop_y2rt` 均值 |
| `stroop_z_rt_mean` | `stroop_z1rt` 与 `stroop_z2rt` 均值 |
| `stroop_acc_mean_all` | 三类准确率均值的平均 |
| `stroop_rt_mean_all` | 三类反应时均值的平均 |
| `stroop_rt_spread_maxmin` | 三类平均反应时最大值 − 最小值 |

#### 7.1.3 质控规则

宽松有效：

- 任一 Stroop 原始准确率或反应时指标非缺失。

严格有效需同时满足：

1. 宽松有效；
2. 所有非缺失反应时均在 200–3000 ms；
3. 所有非缺失准确率均在 0–1；
4. 任一准确率不得低于 0.50。

生成低准确率标记：

- `stroop_flag_low_accuracy_any = 任一准确率 < 0.50`

### 7.2 BART

#### 7.2.1 字段重命名

| 原字段 | 清洗后字段 |
|---|---|
| `总收益` | `bart_total_earnings` |
| `爆炸气球数` | `bart_explosions` |
| `未爆气球总打气次数` | `bart_unexploded_total_pumps` |
| `未爆气球平均打气次数` | `bart_adj_avg_pumps` |

#### 7.2.2 质控规则

宽松有效：

- `bart_total_earnings` 或 `bart_adj_avg_pumps` 任一非缺失。

严格有效需同时满足：

1. 宽松有效；
2. `bart_adj_avg_pumps` 在 0–100；
3. `bart_explosions` 在 0–30。

### 7.3 n-back

#### 7.3.1 字段重命名

| 原字段 | 清洗后字段 |
|---|---|
| `correct0`–`correct3` | `nback_acc0`–`nback_acc3` |
| `correct` | `nback_acc` |
| `RT0`–`RT3` | `nback_rt0`–`nback_rt3` |
| `RT` | `nback_rt` |
| `RTs0`–`RTs3` | `nback_rts0`–`nback_rts3` |
| `RTs` | `nback_rts` |
| `d'0`–`d'3` | `nback_dprime0`–`nback_dprime3` |
| `d'` | `nback_dprime` |
| `β0`–`β3` | `nback_beta0`–`nback_beta3` |
| `β` | `nback_beta` |

#### 7.3.2 派生指标

| 指标 | 计算规则 |
|---|---|
| `nback_acc_load_drop_3minus0` | `nback_acc3 - nback_acc0` |
| `nback_rt_load_increase_3minus0` | `nback_rt3 - nback_rt0` |
| `nback_dprime_load_drop_3minus0` | `nback_dprime3 - nback_dprime0` |

#### 7.3.3 质控规则

宽松有效：

- `nback_acc`、`nback_dprime`、`nback_rt` 任一非缺失。

严格有效需同时满足：

1. 宽松有效；
2. 所有非缺失准确率指标均在 0–1；
3. `nback_rt0`–`nback_rt3` 与 `nback_rt` 中所有非缺失值均在 200–3000 ms；
4. 总准确率 `nback_acc >= 0.60`。

### 7.4 DDT

#### 7.4.1 数值化字段

对 DDT 相关表中除 `姓名` 外的以下字段转为数值型：

- `SUM`
- `K`
- `LNK`
- `LK10`
- `R`
- `R方`
- `赋K`
- `5s主观点`
- `10s主观点`
- `20s主观点`
- `30s主观点`
- `60s主观点`

#### 7.4.2 字段来源与优先级

清洗后 DDT 主指标优先使用 `整理处理用` 工作表，若缺失再使用 `原始录入` 工作表。

| 主指标 | 优先来源 | 备用来源 |
|---|---|---|
| `ddt_sum` | `ddt_sum_clean` | `ddt_sum_full` |
| `ddt_k` | `ddt_k_clean` | `ddt_k_full` |
| `ddt_lnk` | `ddt_lnk_clean` | `ddt_lnk_full` |
| `ddt_fit_r` | `ddt_fit_r_clean` | `ddt_fit_r2_full` |

同时保留主观价值指标：

- `ddt_sv_5s`
- `ddt_sv_10s`
- `ddt_sv_20s`
- `ddt_sv_30s`
- `ddt_sv_60s`

#### 7.4.3 质控规则

宽松有效：

- `ddt_sum`、`ddt_k`、`ddt_lnk` 任一非缺失。

有效 K：

- `ddt_valid_k = ddt_k 非缺失 且 ddt_k > 0`

严格有效需同时满足：

1. `ddt_valid_k` 为真；
2. `ddt_fit_r` 在 0.60–1.00。

### 7.5 点探测/停止信号：下方条件 `yuxia`

#### 7.5.1 字段重命名

元信息：

| 原字段 | 清洗后字段 |
|---|---|
| `类型` | `dot_xia_type_code` |
| `分类` | `dot_xia_class_code` |
| `Age` | `dot_xia_age` |
| `Sex` | `dot_xia_sex` |

任务指标均添加 `dot_xia_` 前缀：

- `ACCxia`
- `pot右xia`
- `pot左xia`
- `yizhixingxia`
- `1右`
- `2右`
- `1左`
- `2左`
- `xia3`
- `xia4`
- `xia5`
- `xia6`

#### 7.5.2 质控规则

宽松有效：

- `dot_xia_ACCxia` 或 `dot_xia_yizhixingxia` 任一非缺失。

严格有效需同时满足：

1. 宽松有效；
2. `dot_xia_ACCxia` 在 0.80–1.00；
3. 反应时相关字段中所有非缺失值均在 150–1500 ms。

反应时相关字段包括字段名中含有：

- `pot`
- `1右`、`2右`、`1左`、`2左`
- `xia3`–`xia6`

### 7.6 点探测/停止信号：上方条件 `yushang`

#### 7.6.1 字段重命名

元信息：

| 原字段 | 清洗后字段 |
|---|---|
| `类型` | `dot_shang_type_code` |
| `分类` | `dot_shang_class_code` |
| `Age` | `dot_shang_age` |
| `Sex` | `dot_shang_sex` |

任务指标均添加 `dot_shang_` 前缀：

- `ACCshang`
- `pot右shang`
- `pot左shang`
- `yizhixingshang`
- `1右`
- `2右`
- `1左`
- `2左`
- `shang3`
- `shang4`
- `shang5`
- `shang6`

#### 7.6.2 质控规则

宽松有效：

- `dot_shang_ACCshang` 或 `dot_shang_yizhixingshang` 任一非缺失。

严格有效需同时满足：

1. 宽松有效；
2. `dot_shang_ACCshang` 在 0.80–1.00；
3. 反应时相关字段中所有非缺失值均在 150–1500 ms。

反应时相关字段包括字段名中含有：

- `pot`
- `1右`、`2右`、`1左`、`2左`
- `shang3`–`shang6`

## 8. 人口学一致性检查

脚本比较实验表与 SAV 主表中的年龄、性别信息。

生成变量：

| 变量 | 规则 |
|---|---|
| `age_diff_exp_vs_sav` | `age_exp - age_sav` |
| `sex_diff_exp_vs_sav` | `sex_exp != sex_sav` |

性别差异标记规则：

- 若 `sex_exp` 或 `sex_sav` 任一缺失，则 `sex_diff_exp_vs_sav` 设为缺失；
- 否则二者不相等时标记为真。

## 9. 全局任务可用性规则

### 9.1 宽松任务块数

`n_task_blocks_liberal` 为以下宽松有效标记为真的任务数量总和：

- `stroop_valid_liberal`
- `bart_valid_liberal`
- `nback_valid_liberal`
- `ddt_valid_liberal`
- `dot_xia_valid_liberal`
- `dot_shang_valid_liberal`
- `cpt_doc_valid`

### 9.2 严格任务块数

`n_task_blocks_strict` 为以下严格有效标记为真的任务数量总和：

- `stroop_valid_strict`
- `bart_valid_strict`
- `nback_valid_strict`
- `ddt_valid_strict`
- `dot_xia_valid_strict`
- `dot_shang_valid_strict`
- `cpt_doc_valid`

注意：CPT 文档只使用 `cpt_doc_valid`，不另设宽松/严格两套规则。

## 10. 探索性综合指标规则

脚本生成 3 个探索性 z 分数综合指标。所有 z 分数均按样本均值和样本标准差计算；若标准差为 0 或缺失，则该 z 分数为缺失。

### 10.1 冷执行功能指标

`cold_exec_index_z` 为以下指标的平均：

- `-zscore(stroop_acc_mean_all)`
- `zscore(stroop_rt_mean_all)`
- `-zscore(nback_acc)`
- `zscore(nback_rt)`

方向含义：数值越高通常表示冷执行功能表现越差，但脚本提示不应过度解释。

### 10.2 热奖赏/风险指标

`hot_reward_index_z` 为以下指标的平均：

- `zscore(bart_adj_avg_pumps)`
- `zscore(bart_explosions)`
- `zscore(ddt_k)`
- `-zscore(ddt_sum)`

方向含义：数值越高通常表示风险/奖赏相关表现更高或折扣更强，但需结合具体指标解释。

### 10.3 CPT 注意指标

`attention_cpt_index_z` 为以下指标的平均：

- `-zscore(cpt_attention_combined)`
- `-zscore(cpt_sustained_auditory)`
- `-zscore(cpt_sustained_visual)`
- `zscore(cpt_hyperactivity_events)`

方向含义：数值越高通常表示 CPT 注意/持续性问题更明显。

## 11. 输出数据集规则

### 11.1 主清洗表：宽松版

输出文件：

- `clean_ADHD_experiment_master_liberal.csv`

包含内容：

- 去标识化 ID；
- 人口学变量；
- 问卷主变量和原始来源总分；
- 暂定分组变量；
- CPT 标签与 CPT 报告指标；
- Stroop、BART、n-back、DDT、点探测/停止信号指标；
- 各任务宽松/严格有效标记；
- 总体任务块数量；
- 探索性综合 z 指标。

### 11.2 严格标记版

输出文件：

- `clean_ADHD_experiment_master_strict_flags.csv`

筛选规则：

- 保留 `n_task_blocks_strict > 0` 的样本；或
- `CPT_label_clean` 非缺失的样本。

注意：该表不是全局严格删除后的唯一分析集，而是保留严格标记的子集。脚本建议按任务使用任务特异 QC flag，不建议一刀切删除整行。

### 11.3 CPT 解析指标表

输出文件：

- `CPT_parsed_metrics.csv`

包含每个 CPT 文件解析得到的指标、文件名、解析成功标记等。

### 11.4 数据字典

输出文件：

- `cleaned_data_dictionary.csv`

脚本按变量名前缀自动生成简要说明：

- `CIAS*`：CIAS 网络成瘾量表；
- `Young*`：Young 网络成瘾问卷；
- `DSM*`：DSM 相关网络/游戏/成瘾条目；
- `CAARS*`：CAARS/ADHD 特质；
- `CPT*` 或 `cpt*`：CPT 标签或报告指标；
- `stroop*`：Stroop 指标；
- `bart*`：BART 指标；
- `nback*`：n-back 指标；
- `ddt*`：DDT 指标；
- `dot*`：点探测/停止信号指标；
- `*_valid_liberal`：任务至少有一个可用指标；
- `*_valid_strict`：通过保守范围/质量规则；
- `tentative` 或 `group_code`：分组解释暂定，需确认。

## 12. 审计与统计输出规则

脚本额外生成以下审计和探索性统计文件：

| 文件 | 内容 |
|---|---|
| `scale_score_reliability_audit.csv` | 量表条目求和、总分一致性、Cronbach’s α 审计 |
| `alternative_totals_do_not_use_audit.csv` | `.1` 后缀总分与主总分差异审计 |
| `cleaning_task_availability.csv` | 各任务宽松/严格可用样本数、严格规则损失数 |
| `cleaning_group_CPT_counts.csv` | 分组与 CPT 分类计数 |
| `cleaned_metric_descriptives.csv` | 清洗后核心指标描述统计 |
| `cleaned_questionnaire_task_spearman_all.csv` | 问卷总分与任务指标 Spearman 相关 |
| `cleaned_questionnaire_task_spearman_top80.csv` | 相关结果前 80 条 |
| `cleaned_CPT_N_vs_ADHD_effect_sizes.csv` | CPT Normal vs I/C 的效应量和 Mann–Whitney U 检验 |
| `cleaned_CPT_group_summary.csv` | CPT 严格分类下核心指标分组描述 |
| `ADHD_data_cleaning_report.md` | 自动生成的人类可读清洗报告 |

## 13. 统计分析规则

### 13.1 描述统计

对核心问卷、实验任务、CPT 和综合指标计算：

- 非缺失样本量 `n`
- 均值 `mean`
- 标准差 `sd`
- 最小值 `min`
- 中位数 `median`
- 最大值 `max`

### 13.2 相关分析

问卷变量：

- `CAARS_total`
- `CIAS_total`
- `Young_total`
- `DSM_total1`
- `DSM_total2`

与任务/CPT/综合指标进行 Spearman 相关。

规则：

- 对每一对变量，先转为数值型；
- 仅使用二者均非缺失的样本；
- 有效配对样本量小于 10 时不计算；
- 输出 Spearman rho、p 值、样本量和绝对相关系数。

### 13.3 CPT 严格分类效应量

比较组别：

- Normal：`CPT_class_strict == Normal`
- ADHD I/C：`CPT_class_strict` 为 `Inattentive` 或 `Combined`

规则：

- 每组非缺失样本量均至少为 5 才计算；
- 计算 Cohen’s d，方向为 ADHD(I/C) − Normal；
- 计算 Mann–Whitney U 双侧检验 p 值；
- 按绝对 d 值排序。

## 14. 打包规则

脚本最终将主要输出文件和 `clean_adhd_experiment.py` 本身打包为：

- `ADHD_cleaned_outputs.zip`

打包文件包括：

1. `clean_ADHD_experiment_master_liberal.csv`
2. `clean_ADHD_experiment_master_strict_flags.csv`
3. `CPT_parsed_metrics.csv`
4. `cleaned_data_dictionary.csv`
5. `scale_score_reliability_audit.csv`
6. `alternative_totals_do_not_use_audit.csv`
7. `cleaning_task_availability.csv`
8. `cleaning_group_CPT_counts.csv`
9. `cleaned_metric_descriptives.csv`
10. `cleaned_questionnaire_task_spearman_all.csv`
11. `cleaned_questionnaire_task_spearman_top80.csv`
12. `cleaned_CPT_N_vs_ADHD_effect_sizes.csv`
13. `cleaned_CPT_group_summary.csv`
14. `ADHD_data_cleaning_report.md`
15. `clean_adhd_experiment.py`

## 15. 推荐分析原则

根据脚本内置报告，正式分析建议遵循以下原则：

1. 主分类优先使用 `CPT_label_clean` 中确定的 `N`、`I`、`C`。
2. `I?`、`C?`、`?` 建议用于敏感性分析，不纳入严格主分类。
3. ADHD 特质主变量使用 `CAARS_total`。
4. 网络成瘾主变量使用 `CIAS_total`，并辅以 `Young_total` 和 `DSM_total1/DSM_total2`。
5. 实验任务应使用任务特异 QC 标记，不建议因单个任务不合格而删除整行样本。
6. CPT 原始报告既可作为分类依据，也可作为持续注意、多动等行为指标来源。
7. 对“ADHD 特质与实验任务关系强弱”的判断，应基于清洗后的相关、效应量和稳健性分析，而非未清洗初步结果。

## 16. 需要人工确认的事项

以下内容脚本中标记为待确认或不宜过度解释：

1. `group_code` 1–6 的确切含义仍需根据实验设计或 codebook 确认。
2. 点探测/停止信号表中的 `类型`、`分类` 以及具体条件编码需要 codebook 确认。
3. CPT 的 `I?`、`C?` 属于不确定亚型，主分析和敏感性分析应分开处理。
4. `.1` 后缀问卷总分不用于主分析，仅作为审计保留。
5. 综合 z 指标为探索性指标，方向和解释需在论文中谨慎说明。
