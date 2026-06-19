#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clean and audit ADHD / internet addiction questionnaire + experiment data.

Outputs de-identified cleaned tables, CPT parsed metrics, QC report, and exploratory statistics.
"""
from __future__ import annotations
import os, re, json, zipfile, subprocess, math, textwrap
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
import pyreadstat
from scipy.stats import spearmanr, kruskal, mannwhitneyu

OUT = Path('/mnt/data')
CPT_ZIP = OUT/'CPT原始数据.zip'
CPT_EXTRACT = OUT/'CPT_zip_extracted_clean'

# ---------- helpers ----------
def to_num(s):
    return pd.to_numeric(s, errors='coerce')

def clean_id(x):
    y = pd.to_numeric(x, errors='coerce')
    try:
        if pd.isna(y): return pd.NA
        return int(y)
    except Exception:
        return pd.NA

def safe_cols(df, cols):
    return [c for c in cols if c in df.columns]

def row_mean(df, cols):
    cols = safe_cols(df, cols)
    if not cols: return pd.Series(np.nan, index=df.index)
    return df[cols].apply(to_num).mean(axis=1)

def zscore(s):
    x = to_num(s)
    sd = x.std(ddof=1)
    if sd == 0 or pd.isna(sd):
        return pd.Series(np.nan, index=s.index)
    return (x - x.mean()) / sd

def cronbach_alpha(items: pd.DataFrame):
    X = items.apply(to_num)
    X = X.dropna(how='any')
    k = X.shape[1]
    if k < 2 or X.shape[0] < 3:
        return np.nan, X.shape[0]
    variances = X.var(axis=0, ddof=1)
    total_var = X.sum(axis=1).var(ddof=1)
    if total_var == 0 or pd.isna(total_var):
        return np.nan, X.shape[0]
    return float(k/(k-1) * (1 - variances.sum()/total_var)), int(X.shape[0])

def cohen_d(x, y):
    x = to_num(pd.Series(x)).dropna(); y = to_num(pd.Series(y)).dropna()
    if len(x)<2 or len(y)<2: return np.nan
    nx, ny = len(x), len(y)
    sp = math.sqrt(((nx-1)*x.var(ddof=1) + (ny-1)*y.var(ddof=1))/(nx+ny-2))
    if sp == 0: return np.nan
    return float((y.mean() - x.mean())/sp)  # y minus x

def spearman_pair(x,y):
    x = to_num(pd.Series(x)); y = to_num(pd.Series(y))
    m = x.notna() & y.notna()
    if m.sum() < 10:
        return np.nan, np.nan, int(m.sum())
    r,p = spearmanr(x[m], y[m])
    return float(r), float(p), int(m.sum())

# ---------- load files ----------
sav, meta = pyreadstat.read_sav(OUT/'被试信息汇总表.sav', apply_value_formats=False)
sav['main_id'] = to_num(sav['beishibianhao']).astype('Int64')

# Excel files
stroop = pd.read_excel(OUT/'Stroop数据整理(1).xls', sheet_name='原始录入', engine='xlrd')
bart = pd.read_excel(OUT/'BART数据整理(1).xls', sheet_name='原始录入', engine='xlrd')
nback = pd.read_excel(OUT/'n-back数据整理.xls', sheet_name='原始录入', engine='xlrd')
ddt_full = pd.read_excel(OUT/'DDT数据整理.xls', sheet_name='原始录入', engine='xlrd')
ddt_clean = pd.read_excel(OUT/'DDT数据整理.xls', sheet_name='整理处理用', engine='xlrd')
ddt_drop = pd.read_excel(OUT/'DDT数据整理.xls', sheet_name='踢除数据', engine='xlrd')
stop_xia = pd.read_excel(OUT/'停止信号 点探测.xlsx', sheet_name='yuxia', engine='openpyxl')
stop_shang = pd.read_excel(OUT/'停止信号 点探测.xlsx', sheet_name='yushang', engine='openpyxl')

# Normalize IDs
for df in [stroop, bart, nback, ddt_full, ddt_clean, ddt_drop]:
    if '实验编号' in df.columns:
        df['experiment_id'] = to_num(df['实验编号']).astype('Int64')
for df in [stop_xia, stop_shang]:
    df['experiment_id'] = to_num(df['Subject']).astype('Int64')

ddt_full['main_id'] = to_num(ddt_full['编号']).astype('Int64')
mapping = ddt_full[['experiment_id','main_id']].drop_duplicates()

# ---------- extract and parse CPT docs ----------
if CPT_ZIP.exists():
    if CPT_EXTRACT.exists():
        # leave existing; zip changed? overwrite simple by extracting into existing
        pass
    CPT_EXTRACT.mkdir(exist_ok=True)
    with zipfile.ZipFile(CPT_ZIP) as z:
        z.extractall(CPT_EXTRACT)

cpt_files = sorted([p for p in CPT_EXTRACT.rglob('*.doc')])

def antiword_text(path: Path) -> str:
    try:
        proc = subprocess.run(['antiword','-m','UTF-8',str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return proc.stdout
    except Exception as e:
        return ''

def parse_chinese_age(age_s):
    if not isinstance(age_s, str): return np.nan
    y = re.search(r'(\d+)\s*岁', age_s)
    m = re.search(r'(\d+)\s*月', age_s)
    d = re.search(r'(\d+)\s*天', age_s)
    years = int(y.group(1)) if y else 0
    months = int(m.group(1)) if m else 0
    days = int(d.group(1)) if d else 0
    return years + months/12 + days/365.25

def line_tokens(line):
    return [t.strip() for t in line.strip().strip('|').split('|')]

def parse_cpt_text(text: str):
    rec = {}
    if not text:
        return rec
    # keep raw text compact for diagnostics, but no name in output
    m = re.search(r'编号[:：]\s*(\d+)', text)
    if m: rec['cpt_report_number'] = m.group(1)
    m = re.search(r'性别[:：]\s*([男女])', text)
    if m: rec['cpt_report_sex'] = m.group(1)
    m = re.search(r'年龄[:：]\s*([^\n\r]+)', text)
    if m:
        age_s = m.group(1).strip()
        rec['cpt_report_age_text'] = age_s
        rec['cpt_report_age_years'] = parse_chinese_age(age_s)
    # report date
    m = re.search(r'报告日期[:：]\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})', text)
    if m: rec['cpt_report_date'] = m.group(1)
    # auditory/visual comprehension - may be split across two lines
    lines = [ln.rstrip() for ln in text.splitlines()]
    for i, ln in enumerate(lines):
        if '听觉 / 视觉' in ln or '听觉/视觉' in ln:
            nums = re.findall(r'\d+', ln)
            # line usually has two numeric values; if second on next line, add next line nums
            if len(nums) < 2 and i+1 < len(lines):
                nums += re.findall(r'\d+', lines[i+1])
            if len(nums) >= 2:
                rec['cpt_comprehension_auditory'] = int(nums[0])
                rec['cpt_comprehension_visual'] = int(nums[1])
            break
    # table rows
    for ln in lines:
        toks = line_tokens(ln)
        if len(toks) >= 3:
            # main rows
            if toks[0] == '听觉' and re.fullmatch(r'\d+', toks[1] or '') and re.fullmatch(r'\d+', toks[2] or ''):
                rec['cpt_control_auditory'] = int(toks[1]); rec['cpt_attention_auditory'] = int(toks[2])
            if toks[0] == '视觉' and re.fullmatch(r'\d+', toks[1] or '') and re.fullmatch(r'\d+', toks[2] or ''):
                rec['cpt_control_visual'] = int(toks[1]); rec['cpt_attention_visual'] = int(toks[2])
            if toks[0] == '综合' and re.fullmatch(r'\d+', toks[1] or '') and re.fullmatch(r'\d+', toks[2] or ''):
                rec['cpt_control_combined'] = int(toks[1]); rec['cpt_attention_combined'] = int(toks[2])
        # control and attention scale rows
        if '谨慎商数' in ln:
            nums = re.findall(r'\d+', ln)
            if len(nums) >= 4:
                rec['cpt_prudence_auditory'] = int(nums[0]); rec['cpt_prudence_visual'] = int(nums[1]); rec['cpt_alertness_auditory'] = int(nums[2]); rec['cpt_alertness_visual'] = int(nums[3])
        if '一致性商' in ln and '注意力商' in ln:
            nums = re.findall(r'\d+', ln)
            if len(nums) >= 4:
                rec['cpt_consistency_auditory'] = int(nums[0]); rec['cpt_consistency_visual'] = int(nums[1]); rec['cpt_attention_q_auditory'] = int(nums[2]); rec['cpt_attention_q_visual'] = int(nums[3])
        if '毅力商数' in ln:
            nums = re.findall(r'\d+', ln)
            if len(nums) >= 4:
                rec['cpt_persistence_auditory'] = int(nums[0]); rec['cpt_persistence_visual'] = int(nums[1]); rec['cpt_speed_auditory'] = int(nums[2]); rec['cpt_speed_visual'] = int(nums[3])
        if '平衡能力' in ln:
            nums = re.findall(r'\d+', ln)
            if nums: rec['cpt_balance'] = int(nums[0])
        if '敏捷商数' in ln and '听觉' in ln:
            nums = re.findall(r'听觉\s*(\d+)', ln)
            if nums: rec['cpt_agility_auditory'] = int(nums[0])
        # continuation line for agility visual
        if '视觉' in ln and '目标分占优势' in ln:
            nums = re.findall(r'视觉\s*(\d+)', ln)
            if nums and 'cpt_agility_visual' not in rec: rec['cpt_agility_visual'] = int(nums[0])
        if '持续性商数' in ln and '听觉' in ln:
            nums = re.findall(r'听觉\s*(\d+)', ln)
            if nums: rec['cpt_sustained_auditory'] = int(nums[0])
        if '感觉/运动商数' in ln and '听觉' in ln:
            nums = re.findall(r'听觉\s*(\d+)', ln)
            if nums: rec['cpt_sensorimotor_auditory'] = int(nums[0])
    # lines following sustained/sensorimotor need context
    for i, ln in enumerate(lines):
        if '持续性商数' in ln:
            # search next 2 lines for visual
            for j in range(i, min(i+3, len(lines))):
                nums = re.findall(r'视觉\s*(\d+)', lines[j])
                if nums: rec['cpt_sustained_visual'] = int(nums[0]); break
        if '感觉/运动商数' in ln:
            for j in range(i, min(i+3, len(lines))):
                nums = re.findall(r'视觉\s*(\d+)', lines[j])
                if nums: rec['cpt_sensorimotor_visual'] = int(nums[0]); break
    mh = re.search(r'多动事件次数[:：]\s*(\d+)', text)
    if mh: rec['cpt_hyperactivity_events'] = int(mh.group(1))
    mq = re.search(r'多动商数值[:：]\s*(\d+)', text)
    if mq: rec['cpt_hyperactivity_quotient'] = int(mq.group(1))
    return rec

cpt_rows = []
for p in cpt_files:
    exp = None
    m = re.search(r'(\d+)', p.stem)
    if m: exp = int(m.group(1))
    text = antiword_text(p)
    rec = {'experiment_id': exp, 'cpt_file': p.name, 'cpt_parse_ok': False}
    rec.update(parse_cpt_text(text))
    # require at least one substantive metric
    rec['cpt_parse_ok'] = any(k.startswith('cpt_control') or k.startswith('cpt_attention') or k.startswith('cpt_hyperactivity') for k in rec)
    cpt_rows.append(rec)
cpt_df = pd.DataFrame(cpt_rows)
# dedup by experiment_id (should be unique)
cpt_df = cpt_df.sort_values(['experiment_id','cpt_file']).drop_duplicates('experiment_id', keep='first')

# ---------- construct base experiment-level table ----------
base = mapping.copy()
# Add SAV demographics and original totals
sav_keep = {
    'xingbie':'sex_sav','nianling':'age_sav','from':'source_sav','fumuwenhua':'parent_edu_sav','dusheng':'only_child_sav','jiatingleixin':'family_type_sav','jinjizhuangkuang':'family_econ_sav','wangling':'internet_years_sav','shangwangshijian':'internet_time_recent_sav',
    'I总分':'CIAS_total_sav','Y总分':'Young_total_sav','D总分1':'DSM_total1_sav','D总分2':'DSM_total2_sav','C总分':'CAARS_total_sav'
}
base = base.merge(sav[['main_id'] + list(sav_keep.keys())].rename(columns=sav_keep), on='main_id', how='left')

# Metadata from DDT/Stroop; use DDT since it includes main_id, but remove PII
meta_cols = ['experiment_id','分组','性别','年龄','来自','父母文化水平','独生','家庭类型','家庭经济状况','网龄','近3月平均上网时间',
             '抑郁','焦虑','学习障碍','品行障碍','对立违抗行为','物质依赖','赌博',
             'CIASSUM','CIASSUM1','CIASSUM2','CIASSUM3','CIASSUM4','CIASSUM5','YOUNGSUM','DSMSUM1','DSMSUM2','CAARSSUM','CPT']
meta_src = ddt_full[safe_cols(ddt_full, meta_cols)].copy()
rename_meta = {
    '分组':'group_code_raw','性别':'sex_exp','年龄':'age_exp','来自':'source_exp','父母文化水平':'parent_edu_exp','独生':'only_child_exp','家庭类型':'family_type_exp','家庭经济状况':'family_econ_exp','网龄':'internet_years_exp','近3月平均上网时间':'internet_time_recent_exp',
    '抑郁':'comorb_depression','焦虑':'comorb_anxiety','学习障碍':'comorb_learning_disability','品行障碍':'comorb_conduct','对立违抗行为':'comorb_odd','物质依赖':'comorb_substance','赌博':'comorb_gambling',
    'CIASSUM':'CIAS_total_file','CIASSUM1':'CIAS_sub1_file','CIASSUM2':'CIAS_sub2_file','CIASSUM3':'CIAS_sub3_file','CIASSUM4':'CIAS_sub4_file','CIASSUM5':'CIAS_sub5_file',
    'YOUNGSUM':'Young_total_file','DSMSUM1':'DSM_total1_file','DSMSUM2':'DSM_total2_file','CAARSSUM':'CAARS_total_file','CPT':'CPT_label_raw'
}
meta_src = meta_src.rename(columns=rename_meta)
base = base.merge(meta_src, on='experiment_id', how='left')

# Exclude .1 totals from main dataset; audit separately
alt_totals = ddt_full[['experiment_id','CIASSUM.1','YOUNGSUM.1','DSMSUM1.1','DSMSUM2.1','CAARSSUM.1']].copy()
alt_totals.columns = ['experiment_id','CIAS_total_alt_CPTmerge','Young_total_alt_CPTmerge','DSM_total1_alt_CPTmerge','DSM_total2_alt_CPTmerge','CAARS_total_alt_CPTmerge']
base = base.merge(alt_totals, on='experiment_id', how='left')

# Final analysis scale totals: prefer experimental file total; if missing then SAV
for var in ['CIAS','Young','DSM_total1','DSM_total2','CAARS']:
    file_col = f'{var}_total_file' if var in ['CIAS','Young','CAARS'] else f'{var}_file'
    sav_col = f'{var}_total_sav' if var in ['CIAS','Young','CAARS'] else f'{var}_sav'
# Explicit due naming variations
base['CIAS_total'] = to_num(base['CIAS_total_file']).combine_first(to_num(base['CIAS_total_sav']))
base['Young_total'] = to_num(base['Young_total_file']).combine_first(to_num(base['Young_total_sav']))
base['DSM_total1'] = to_num(base['DSM_total1_file']).combine_first(to_num(base['DSM_total1_sav']))
base['DSM_total2'] = to_num(base['DSM_total2_file']).combine_first(to_num(base['DSM_total2_sav']))
base['CAARS_total'] = to_num(base['CAARS_total_file']).combine_first(to_num(base['CAARS_total_sav']))

# group mapping, explicitly tentative
group_map = {
    1: '正常/对照?（待确认）',
    2: '注意缺陷型?（待确认）',
    3: '多动冲动型?（待确认）',
    4: '混合型?（待确认）',
    5: '注意缺陷型+网络成瘾?（待确认）',
    6: '多动冲动型+网络成瘾?（待确认）',
}
base['group_code'] = to_num(base['group_code_raw']).astype('Int64')
base['group_label_tentative'] = base['group_code'].map(group_map)
base['group_adhd_like_tentative'] = base['group_code'].isin([2,3,4,5,6])
base['group_ia_comorbid_tentative'] = base['group_code'].isin([5,6])

# CPT labels from summary table, and strict/broad classes
base['CPT_label_clean'] = base['CPT_label_raw'].astype(str).str.strip().replace({'nan':np.nan, '？':'?', '':np.nan})
base['CPT_label_certainty'] = np.select([
    base['CPT_label_clean'].isin(['N','I','C']),
    base['CPT_label_clean'].isin(['I?','C?']),
    base['CPT_label_clean'].isin(['?'])
], ['certain','uncertain_subtype','unknown'], default=None)
base['CPT_class_strict'] = base['CPT_label_clean'].map({'N':'Normal','I':'Inattentive','C':'Combined'})
base['CPT_class_broad'] = base['CPT_label_clean'].map({'N':'Normal','I':'Inattentive','C':'Combined','I?':'Inattentive_uncertain','C?':'Combined_uncertain'})
base['CPT_ADHD_strict'] = base['CPT_label_clean'].isin(['I','C'])
base['CPT_ADHD_broad'] = base['CPT_label_clean'].isin(['I','C','I?','C?'])
base.loc[base['CPT_label_clean'].isna() | base['CPT_label_clean'].eq('?'), ['CPT_ADHD_strict','CPT_ADHD_broad']] = np.nan

# ---------- add tasks ----------
# Stroop
stroop_cols = ['b1acc','b1rt','b2acc','b2rt','y1acc','y1rt','y2acc','y2rt','z1acc','z1rt','z2acc','z2rt']
st = stroop[['experiment_id']+stroop_cols].copy()
for c in stroop_cols: st[c] = to_num(st[c])
st = st.rename(columns={c:'stroop_'+c for c in stroop_cols})
st['stroop_b_acc_mean'] = row_mean(st, ['stroop_b1acc','stroop_b2acc'])
st['stroop_y_acc_mean'] = row_mean(st, ['stroop_y1acc','stroop_y2acc'])
st['stroop_z_acc_mean'] = row_mean(st, ['stroop_z1acc','stroop_z2acc'])
st['stroop_b_rt_mean'] = row_mean(st, ['stroop_b1rt','stroop_b2rt'])
st['stroop_y_rt_mean'] = row_mean(st, ['stroop_y1rt','stroop_y2rt'])
st['stroop_z_rt_mean'] = row_mean(st, ['stroop_z1rt','stroop_z2rt'])
st['stroop_acc_mean_all'] = row_mean(st, ['stroop_b_acc_mean','stroop_y_acc_mean','stroop_z_acc_mean'])
st['stroop_rt_mean_all'] = row_mean(st, ['stroop_b_rt_mean','stroop_y_rt_mean','stroop_z_rt_mean'])
st['stroop_rt_spread_maxmin'] = st[['stroop_b_rt_mean','stroop_y_rt_mean','stroop_z_rt_mean']].max(axis=1) - st[['stroop_b_rt_mean','stroop_y_rt_mean','stroop_z_rt_mean']].min(axis=1)
st['stroop_valid_liberal'] = st[safe_cols(st, [f'stroop_{c}' for c in stroop_cols])].notna().any(axis=1)
rt_cols = [c for c in st.columns if c.startswith('stroop_') and c.endswith('rt')]
acc_cols = [c for c in st.columns if c.startswith('stroop_') and c.endswith('acc')]
st['stroop_flag_low_accuracy_any'] = (st[acc_cols].min(axis=1) < 0.50)
st['stroop_valid_strict'] = st['stroop_valid_liberal'] & st[rt_cols].apply(lambda row: row.dropna().between(200,3000).all(), axis=1) & st[acc_cols].apply(lambda row: row.dropna().between(0,1).all(), axis=1) & (~st['stroop_flag_low_accuracy_any'])
base = base.merge(st, on='experiment_id', how='left')

# BART
bart_cols = {'总收益':'bart_total_earnings','爆炸气球数':'bart_explosions','未爆气球总打气次数':'bart_unexploded_total_pumps','未爆气球平均打气次数':'bart_adj_avg_pumps'}
ba = bart[['experiment_id'] + list(bart_cols.keys())].rename(columns=bart_cols).copy()
for c in bart_cols.values(): ba[c] = to_num(ba[c])
ba['bart_valid_liberal'] = ba[['bart_total_earnings','bart_adj_avg_pumps']].notna().any(axis=1)
ba['bart_valid_strict'] = ba['bart_valid_liberal'] & ba['bart_adj_avg_pumps'].between(0,100) & ba['bart_explosions'].between(0,30)
base = base.merge(ba, on='experiment_id', how='left')

# n-back
nb_cols = ['correct0','correct1','correct2','correct3','correct','RT0','RT1','RT2','RT3','RT','RTs0','RTs1','RTs2','RTs3','RTs',"d'0","d'1","d'2","d'3","d'",'β0','β1','β2','β3','β']
nb = nback[['experiment_id']+nb_cols].copy()
for c in nb_cols: nb[c] = to_num(nb[c])
nb = nb.rename(columns={"d'0":"nback_dprime0","d'1":"nback_dprime1","d'2":"nback_dprime2","d'3":"nback_dprime3","d'":"nback_dprime",'β0':'nback_beta0','β1':'nback_beta1','β2':'nback_beta2','β3':'nback_beta3','β':'nback_beta',
                        'correct0':'nback_acc0','correct1':'nback_acc1','correct2':'nback_acc2','correct3':'nback_acc3','correct':'nback_acc','RT0':'nback_rt0','RT1':'nback_rt1','RT2':'nback_rt2','RT3':'nback_rt3','RT':'nback_rt','RTs0':'nback_rts0','RTs1':'nback_rts1','RTs2':'nback_rts2','RTs3':'nback_rts3','RTs':'nback_rts'})
nb['nback_acc_load_drop_3minus0'] = nb['nback_acc3'] - nb['nback_acc0']
nb['nback_rt_load_increase_3minus0'] = nb['nback_rt3'] - nb['nback_rt0']
nb['nback_dprime_load_drop_3minus0'] = nb['nback_dprime3'] - nb['nback_dprime0']
nb['nback_valid_liberal'] = nb[['nback_acc','nback_dprime','nback_rt']].notna().any(axis=1)
nb_acc_cols = [c for c in nb.columns if c.startswith('nback_acc') and c != 'nback_acc_load_drop_3minus0']
nb_rt_cols = [c for c in nb.columns if re.match(r'nback_rt[0-3]?$', c)]
nb['nback_valid_strict'] = nb['nback_valid_liberal'] & nb[nb_acc_cols].apply(lambda row: row.dropna().between(0,1).all(), axis=1) & nb[nb_rt_cols].apply(lambda row: row.dropna().between(200,3000).all(), axis=1) & (nb['nback_acc'] >= 0.60)
base = base.merge(nb, on='experiment_id', how='left')

# DDT: use processed sheet as main, full as backup
for df in [ddt_clean, ddt_full, ddt_drop]:
    for c in df.columns:
        if c not in ['姓名']:
            if c in ['SUM','K','LNK','LK10','R','R方','赋K','5s主观点','10s主观点','20s主观点','30s主观点','60s主观点']:
                df[c] = to_num(df[c])

dc = ddt_clean[['experiment_id','SUM','K','LNK','LK10','R']].rename(columns={'SUM':'ddt_sum_clean','K':'ddt_k_clean','LNK':'ddt_lnk_clean','LK10':'ddt_log10k_clean','R':'ddt_fit_r_clean'}).copy()
df = ddt_full[['experiment_id','SUM','K','LNK','R方','赋K','5s主观点','10s主观点','20s主观点','30s主观点','60s主观点']].rename(columns={'SUM':'ddt_sum_full','K':'ddt_k_full','LNK':'ddt_lnk_full','R方':'ddt_fit_r2_full','赋K':'ddt_assigned_k_full','5s主观点':'ddt_sv_5s','10s主观点':'ddt_sv_10s','20s主观点':'ddt_sv_20s','30s主观点':'ddt_sv_30s','60s主观点':'ddt_sv_60s'}).copy()
ddt = df.merge(dc, on='experiment_id', how='left')
# Main DDT values prefer clean processed, then full
ddt['ddt_sum'] = ddt['ddt_sum_clean'].combine_first(ddt['ddt_sum_full'])
ddt['ddt_k'] = ddt['ddt_k_clean'].combine_first(ddt['ddt_k_full'])
ddt['ddt_lnk'] = ddt['ddt_lnk_clean'].combine_first(ddt['ddt_lnk_full'])
ddt['ddt_fit_r'] = ddt['ddt_fit_r_clean'].combine_first(ddt['ddt_fit_r2_full'])
ddt['ddt_valid_liberal'] = ddt[['ddt_sum','ddt_k','ddt_lnk']].notna().any(axis=1)
ddt['ddt_valid_k'] = ddt['ddt_k'].notna() & (ddt['ddt_k'] > 0)
ddt['ddt_valid_strict'] = ddt['ddt_valid_k'] & ddt['ddt_fit_r'].between(0.60, 1.0)
base = base.merge(ddt, on='experiment_id', how='left')

# Dot/Stop Probe tables: type/class labels retained but not interpreted as trial-level stop-signal without codebook
sx_cols = ['ACCxia','pot右xia','pot左xia','yizhixingxia','1右','2右','1左','2左','xia3','xia4','xia5','xia6']
sx = stop_xia[['experiment_id','类型','分类','Age','Sex'] + sx_cols].copy()
for c in sx_cols + ['Age','Sex','类型','分类']: sx[c] = to_num(sx[c])
sx = sx.rename(columns={'类型':'dot_xia_type_code','分类':'dot_xia_class_code','Age':'dot_xia_age','Sex':'dot_xia_sex', **{c:'dot_xia_'+c for c in sx_cols}})
sx['dot_xia_valid_liberal'] = sx[['dot_xia_ACCxia','dot_xia_yizhixingxia']].notna().any(axis=1)
sx_rt_cols = [c for c in sx.columns if c.startswith('dot_xia_') and (('pot' in c) or re.search(r'[12][右左]|xia[3-6]', c))]
sx['dot_xia_valid_strict'] = sx['dot_xia_valid_liberal'] & sx['dot_xia_ACCxia'].between(0.80,1.0) & sx[sx_rt_cols].apply(lambda row: row.dropna().between(150,1500).all(), axis=1)
base = base.merge(sx, on='experiment_id', how='left')

sy_cols = ['ACCshang','pot右shang','pot左shang','yizhixingshang','1右','2右','1左','2左','shang3','shang4','shang5','shang6']
sy = stop_shang[['experiment_id','类型','分类','Age','Sex'] + sy_cols].copy()
for c in sy_cols + ['Age','Sex','类型','分类']: sy[c] = to_num(sy[c])
sy = sy.rename(columns={'类型':'dot_shang_type_code','分类':'dot_shang_class_code','Age':'dot_shang_age','Sex':'dot_shang_sex', **{c:'dot_shang_'+c for c in sy_cols}})
sy['dot_shang_valid_liberal'] = sy[['dot_shang_ACCshang','dot_shang_yizhixingshang']].notna().any(axis=1)
sy_rt_cols = [c for c in sy.columns if c.startswith('dot_shang_') and (('pot' in c) or re.search(r'[12][右左]|shang[3-6]', c))]
sy['dot_shang_valid_strict'] = sy['dot_shang_valid_liberal'] & sy['dot_shang_ACCshang'].between(0.80,1.0) & sy[sy_rt_cols].apply(lambda row: row.dropna().between(150,1500).all(), axis=1)
base = base.merge(sy, on='experiment_id', how='left')

# CPT raw report metrics
base = base.merge(cpt_df, on='experiment_id', how='left')
base['cpt_doc_valid'] = base['cpt_parse_ok'].fillna(False)

# ---------- QC flags ----------
# Range checks for survey totals
range_specs = {
    'CIAS_total': (26,104),
    'Young_total': (0,8),
    'DSM_total1': (0,9),
    'DSM_total2': (0,13),
    'CAARS_total': (0,78),
}
for col,(lo,hi) in range_specs.items():
    base[f'{col}_range_ok'] = to_num(base[col]).between(lo,hi) | to_num(base[col]).isna()

# ID/demographic discrepancies
base['age_diff_exp_vs_sav'] = to_num(base['age_exp']) - to_num(base['age_sav'])
base['sex_diff_exp_vs_sav'] = to_num(base['sex_exp']) != to_num(base['sex_sav'])
base.loc[to_num(base['sex_exp']).isna() | to_num(base['sex_sav']).isna(), 'sex_diff_exp_vs_sav'] = np.nan
# Flag alt totals as not primary
for var in ['CIAS','Young','DSM_total1','DSM_total2','CAARS']:
    alt = f'{var}_total_alt_CPTmerge' if var in ['CIAS','Young','CAARS'] else f'{var}_alt_CPTmerge'

# Global task availability
valid_flags = ['stroop_valid_liberal','bart_valid_liberal','nback_valid_liberal','ddt_valid_liberal','dot_xia_valid_liberal','dot_shang_valid_liberal','cpt_doc_valid']
base['n_task_blocks_liberal'] = base[valid_flags].fillna(False).sum(axis=1)
strict_flags = ['stroop_valid_strict','bart_valid_strict','nback_valid_strict','ddt_valid_strict','dot_xia_valid_strict','dot_shang_valid_strict','cpt_doc_valid']
base['n_task_blocks_strict'] = base[strict_flags].fillna(False).sum(axis=1)

# Composite exploratory domain scores (z-coded; higher meaning depends on metric, noted in report)
# Use selected valid metrics. We won't overinterpret.
base['cold_exec_index_z'] = pd.concat([
    -zscore(base['stroop_acc_mean_all']), zscore(base['stroop_rt_mean_all']), -zscore(base['nback_acc']), zscore(base['nback_rt'])
], axis=1).mean(axis=1)
base['hot_reward_index_z'] = pd.concat([
    zscore(base['bart_adj_avg_pumps']), zscore(base['bart_explosions']), zscore(base['ddt_k']), -zscore(base['ddt_sum'])
], axis=1).mean(axis=1)
base['attention_cpt_index_z'] = pd.concat([
    -zscore(base['cpt_attention_combined']), -zscore(base['cpt_sustained_auditory']), -zscore(base['cpt_sustained_visual']), zscore(base['cpt_hyperactivity_events'])
], axis=1).mean(axis=1)

# ---------- outputs: cleaned datasets ----------
# Remove PII and keep explicit deidentified variables
# Keep IDs only as numeric linking keys; no names, phone, class, major.
primary_cols = [
    'main_id','experiment_id','age_sav','sex_sav','age_exp','sex_exp','age_diff_exp_vs_sav','sex_diff_exp_vs_sav',
    'source_exp','parent_edu_exp','only_child_exp','family_type_exp','family_econ_exp','internet_years_exp','internet_time_recent_exp',
    'comorb_depression','comorb_anxiety','comorb_learning_disability','comorb_conduct','comorb_odd','comorb_substance','comorb_gambling',
    'group_code','group_label_tentative','group_adhd_like_tentative','group_ia_comorbid_tentative',
    'CPT_label_raw','CPT_label_clean','CPT_label_certainty','CPT_class_strict','CPT_class_broad','CPT_ADHD_strict','CPT_ADHD_broad',
    'CIAS_total','CIAS_sub1_file','CIAS_sub2_file','CIAS_sub3_file','CIAS_sub4_file','CIAS_sub5_file','Young_total','DSM_total1','DSM_total2','CAARS_total',
    'CIAS_total_sav','Young_total_sav','DSM_total1_sav','DSM_total2_sav','CAARS_total_sav','CIAS_total_file','Young_total_file','DSM_total1_file','DSM_total2_file','CAARS_total_file',
]
# Add all task and cpt metric columns
metric_prefixes = ('stroop_','bart_','nback_','ddt_','dot_xia_','dot_shang_','cpt_')
metric_cols = [c for c in base.columns if c.startswith(metric_prefixes)]
qc_cols = [c for c in base.columns if c.endswith('_range_ok') or c.endswith('_valid_liberal') or c.endswith('_valid_strict') or c in ['n_task_blocks_liberal','n_task_blocks_strict','cold_exec_index_z','hot_reward_index_z','attention_cpt_index_z','cpt_doc_valid']]
keep_cols = []
for c in primary_cols + metric_cols + qc_cols:
    if c in base.columns and c not in keep_cols:
        keep_cols.append(c)
clean = base[keep_cols].copy()
# Coerce nullable booleans/IDs to friendly outputs
clean.to_csv(OUT/'clean_ADHD_experiment_master_liberal.csv', index=False, encoding='utf-8-sig')
# Strict subset: not excluding participants globally; but keep rows with at least one strict task or survey+CPT label
strict_subset = clean[(base['n_task_blocks_strict']>0) | base['CPT_label_clean'].notna()].copy()
strict_subset.to_csv(OUT/'clean_ADHD_experiment_master_strict_flags.csv', index=False, encoding='utf-8-sig')
# Parsed CPT metrics
cpt_df.to_csv(OUT/'CPT_parsed_metrics.csv', index=False, encoding='utf-8-sig')

# ---------- audits ----------
# Scale score validation and reliability using original experimental file items
scale_rows = []
scale_specs = [
    ('CIAS','I',26,'CIASSUM',26,104),
    ('Young','Y',8,'YOUNGSUM',0,8),
    ('DSM_part1','D',9,'DSMSUM1',0,9),
    ('DSM_part2','D',13,'DSMSUM2',0,13),
    ('CAARS','C',26,'CAARSSUM',0,78),
]
# CAARS total maybe 26 items 0-3, CIAS 1-4; DSM part2 uses D10-D22
for scale, prefix, n_items, total_col, lo, hi in scale_specs:
    if scale == 'DSM_part1':
        items = [f'D{i}' for i in range(1,10)]
    elif scale == 'DSM_part2':
        items = [f'D{i}' for i in range(10,23)]
    else:
        items = [f'{prefix}{i}' for i in range(1,n_items+1)]
    items = safe_cols(ddt_full, items)
    item_sum = ddt_full[items].apply(to_num).sum(axis=1) if items else pd.Series(np.nan, index=ddt_full.index)
    total = to_num(ddt_full[total_col]) if total_col in ddt_full.columns else pd.Series(np.nan, index=ddt_full.index)
    diff = (item_sum - total).abs()
    alpha, alpha_n = cronbach_alpha(ddt_full[items]) if items else (np.nan,0)
    scale_rows.append({
        'scale':scale,
        'items':','.join(items),
        'n_items':len(items),
        'total_column':total_col,
        'n_total_nonmissing':int(total.notna().sum()),
        'total_min':float(total.min()) if total.notna().any() else np.nan,
        'total_max':float(total.max()) if total.notna().any() else np.nan,
        'expected_total_range':f'{lo}-{hi}',
        'n_itemsum_total_discrepancies':int((diff>1e-9).sum()),
        'max_abs_itemsum_total_diff':float(diff.max()) if diff.notna().any() else np.nan,
        'cronbach_alpha_raw_items':alpha,
        'cronbach_alpha_n_complete':alpha_n,
        'reverse_scoring_comment':'总分等于当前条目求和；若原问卷有反向题，则该文件中条目很可能已编码好，当前不能另行反向。'
    })
scale_audit = pd.DataFrame(scale_rows)
scale_audit.to_csv(OUT/'scale_score_reliability_audit.csv', index=False, encoding='utf-8-sig')

# Alternative .1 totals audit
alt_audit = []
for main_col, alt_col in [
    ('CIAS_total','CIAS_total_alt_CPTmerge'),('Young_total','Young_total_alt_CPTmerge'),('DSM_total1','DSM_total1_alt_CPTmerge'),('DSM_total2','DSM_total2_alt_CPTmerge'),('CAARS_total','CAARS_total_alt_CPTmerge')]:
    x = to_num(base[main_col]); y = to_num(base[alt_col])
    m = x.notna() & y.notna()
    alt_audit.append({
        'comparison': f'{main_col} vs {alt_col}',
        'n_pair': int(m.sum()),
        'n_nonzero_diff': int(((x-y).abs()>1e-9)[m].sum()) if m.any() else 0,
        'max_abs_diff': float((x-y).abs()[m].max()) if m.any() else np.nan,
        'pearson_r': float(x[m].corr(y[m])) if m.sum()>2 else np.nan,
        'decision':'不作为主分析；疑似另一次合并/中间表，与原始问卷总分不一致。'
    })
alt_audit_df = pd.DataFrame(alt_audit)
alt_audit_df.to_csv(OUT/'alternative_totals_do_not_use_audit.csv', index=False, encoding='utf-8-sig')

# Task availability and exclusion summary
task_flags = [
    ('Stroop','stroop_valid_liberal','stroop_valid_strict'),
    ('BART','bart_valid_liberal','bart_valid_strict'),
    ('n-back','nback_valid_liberal','nback_valid_strict'),
    ('DDT','ddt_valid_liberal','ddt_valid_strict'),
    ('Dot/Stop lower','dot_xia_valid_liberal','dot_xia_valid_strict'),
    ('Dot/Stop upper','dot_shang_valid_liberal','dot_shang_valid_strict'),
    ('CPT parsed doc','cpt_doc_valid','cpt_doc_valid'),
]
avail_rows=[]
for task, lf, sf in task_flags:
    avail_rows.append({'task_block':task,'n_liberal_available':int(base[lf].fillna(False).sum()),'n_strict_valid':int(base[sf].fillna(False).sum()),'n_total_experiment_ids':int(base.shape[0]),'strict_loss':int(base[lf].fillna(False).sum()-base[sf].fillna(False).sum())})
avail = pd.DataFrame(avail_rows)
avail.to_csv(OUT/'cleaning_task_availability.csv', index=False, encoding='utf-8-sig')

# CPT label counts and group counts
count_rows=[]
for col in ['group_code','group_label_tentative','CPT_label_clean','CPT_class_strict','CPT_class_broad']:
    vc = base[col].value_counts(dropna=False).sort_index() if col!='group_label_tentative' else base[col].value_counts(dropna=False)
    for k,v in vc.items():
        count_rows.append({'variable':col,'value':str(k),'n':int(v)})
counts = pd.DataFrame(count_rows)
counts.to_csv(OUT/'cleaning_group_CPT_counts.csv', index=False, encoding='utf-8-sig')

# ---------- exploratory cleaned stats ----------
selected_metrics = [
    'CIAS_total','Young_total','DSM_total1','DSM_total2','CAARS_total',
    'stroop_acc_mean_all','stroop_rt_mean_all','stroop_rt_spread_maxmin',
    'bart_total_earnings','bart_explosions','bart_adj_avg_pumps',
    'nback_acc','nback_rt','nback_rts','nback_dprime','nback_beta','nback_acc_load_drop_3minus0','nback_rt_load_increase_3minus0','nback_dprime_load_drop_3minus0',
    'ddt_sum','ddt_k','ddt_lnk','ddt_fit_r',
    'dot_xia_ACCxia','dot_xia_yizhixingxia','dot_shang_ACCshang','dot_shang_yizhixingshang',
    'cpt_control_combined','cpt_attention_combined','cpt_hyperactivity_events','cpt_hyperactivity_quotient','cpt_sustained_auditory','cpt_sustained_visual',
    'cold_exec_index_z','hot_reward_index_z','attention_cpt_index_z'
]
desc=[]
for c in selected_metrics:
    if c not in base.columns: continue
    x=to_num(base[c])
    desc.append({'variable':c,'n':int(x.notna().sum()),'mean':float(x.mean()) if x.notna().any() else np.nan,'sd':float(x.std(ddof=1)) if x.notna().sum()>1 else np.nan,'min':float(x.min()) if x.notna().any() else np.nan,'median':float(x.median()) if x.notna().any() else np.nan,'max':float(x.max()) if x.notna().any() else np.nan})
desc_df=pd.DataFrame(desc)
desc_df.to_csv(OUT/'cleaned_metric_descriptives.csv', index=False, encoding='utf-8-sig')

# Spearman correlations: CAARS/CIAS with experimental metrics; using cleaned main variables
qvars = ['CAARS_total','CIAS_total','Young_total','DSM_total1','DSM_total2']
metric_for_corr = [c for c in selected_metrics if c not in qvars]
cor_rows=[]
for q in qvars:
    for mcol in metric_for_corr:
        if mcol not in base.columns: continue
        r,p,n=spearman_pair(base[q], base[mcol])
        if not pd.isna(r):
            cor_rows.append({'questionnaire':q,'metric':mcol,'spearman_rho':r,'p_value':p,'n':n,'abs_rho':abs(r)})
cor_df = pd.DataFrame(cor_rows).sort_values(['questionnaire','abs_rho'], ascending=[True,False])
cor_df.to_csv(OUT/'cleaned_questionnaire_task_spearman_all.csv', index=False, encoding='utf-8-sig')
cor_df.head(80).to_csv(OUT/'cleaned_questionnaire_task_spearman_top80.csv', index=False, encoding='utf-8-sig')

# Effect sizes by CPT strict N vs ADHD (I+C)
effect_rows=[]
mask_strict = base['CPT_class_strict'].isin(['Normal','Inattentive','Combined'])
for mcol in selected_metrics:
    if mcol not in base.columns: continue
    normal = base.loc[base['CPT_class_strict'].eq('Normal'), mcol]
    adhd = base.loc[base['CPT_class_strict'].isin(['Inattentive','Combined']), mcol]
    n0, n1 = to_num(normal).notna().sum(), to_num(adhd).notna().sum()
    if n0 >= 5 and n1 >= 5:
        d = cohen_d(normal, adhd)
        try:
            u,p=mannwhitneyu(to_num(normal).dropna(), to_num(adhd).dropna(), alternative='two-sided')
        except Exception:
            p=np.nan
        effect_rows.append({'metric':mcol,'N_normal':int(n0),'N_ADHD_IC':int(n1),'mean_Normal':float(to_num(normal).mean()),'mean_ADHD_IC':float(to_num(adhd).mean()),'cohen_d_ADHD_minus_Normal':d,'mannwhitney_p':float(p) if not pd.isna(p) else np.nan,'abs_d':abs(d) if not pd.isna(d) else np.nan})
effect_df = pd.DataFrame(effect_rows).sort_values('abs_d', ascending=False)
effect_df.to_csv(OUT/'cleaned_CPT_N_vs_ADHD_effect_sizes.csv', index=False, encoding='utf-8-sig')

# CPT class group summaries for core variables
group_summary=[]
for cls in ['Normal','Inattentive','Combined']:
    sub=base[base['CPT_class_strict'].eq(cls)]
    for c in ['CAARS_total','CIAS_total','Young_total','DSM_total1','DSM_total2','cpt_attention_combined','cpt_control_combined','cpt_hyperactivity_events','stroop_rt_mean_all','bart_adj_avg_pumps','nback_acc','ddt_k']:
        if c in base.columns:
            x=to_num(sub[c])
            group_summary.append({'CPT_class_strict':cls,'variable':c,'n':int(x.notna().sum()),'mean':float(x.mean()) if x.notna().sum() else np.nan,'sd':float(x.std(ddof=1)) if x.notna().sum()>1 else np.nan,'median':float(x.median()) if x.notna().sum() else np.nan})
group_summary_df=pd.DataFrame(group_summary)
group_summary_df.to_csv(OUT/'cleaned_CPT_group_summary.csv', index=False, encoding='utf-8-sig')

# ---------- data dictionary ----------
dict_rows=[]
for col in clean.columns:
    desc=''
    if col in ['main_id','experiment_id']:
        desc='Linking ID only; no name/contact included.'
    elif col.startswith('CIAS'):
        desc='CIAS/Chen Internet Addiction Scale total/subscale, inferred from CIASSUM/I-items.'
    elif col.startswith('Young'):
        desc='Young Internet Addiction diagnostic questionnaire total, inferred from YOUNGSUM/Y-items.'
    elif col.startswith('DSM'):
        desc='DSM-related internet/gaming/addiction criterion score, inferred from DSMSUM/D-items.'
    elif col.startswith('CAARS'):
        desc='CAARS/ADHD trait total, inferred from CAARSSUM/C-items.'
    elif col.startswith('CPT_') or col.startswith('cpt_'):
        desc='CPT label/report metric. C=Combined, I=Inattentive, N=Normal; ? indicates uncertain/unknown.'
    elif col.startswith('stroop_'):
        desc='Stroop summary metric from spreadsheet. Trial-level data not available.'
    elif col.startswith('bart_'):
        desc='BART/risk-taking summary metric.'
    elif col.startswith('nback_'):
        desc='n-back working memory summary metric.'
    elif col.startswith('ddt_'):
        desc='Delay discounting task metric. Cleaned sheet preferred when available.'
    elif col.startswith('dot_'):
        desc='Dot-probe/stop-signal summary metric; exact task coding needs codebook confirmation.'
    elif col.endswith('_valid_liberal'):
        desc='Task block has at least one usable metric.'
    elif col.endswith('_valid_strict'):
        desc='Task block passed conservative range/quality rules defined in cleaning script.'
    elif 'tentative' in col or col=='group_code':
        desc='Experimental group coding; mapping is provisional and must be confirmed.'
    dict_rows.append({'variable':col,'description':desc})
dd = pd.DataFrame(dict_rows)
dd.to_csv(OUT/'cleaned_data_dictionary.csv', index=False, encoding='utf-8-sig')

# ---------- human-readable report ----------
report_lines=[]
report_lines.append('# ADHD/网络成瘾实验数据清洗报告\n')
report_lines.append('## 1. 本轮清洗结论\n')
report_lines.append('- 已将问卷主表、Stroop、BART、n-back、DDT、点探测/停止信号表，以及 CPT 原始 Word 报告合并为一张去标识化分析表。\n')
report_lines.append('- CPT 原始 ZIP 已成功读取；使用 antiword 提取了每个 `.doc` 报告中的 Q 值、控制力、注意力、多动事件、持续性等指标。\n')
report_lines.append('- 之前“ADHD 特质与实验任务关系弱”的说法只能作为未清洗初步现象；本报告不把它当结论。清洗后应以 `cleaned_questionnaire_task_spearman_all.csv` 和 `cleaned_CPT_N_vs_ADHD_effect_sizes.csv` 为准。\n')
report_lines.append('- 分组代码 1–6 的含义目前按口头说明暂定；正式论文中建议优先使用 `CPT_label_clean` 的 N/I/C 做分类，或把 1–6 作为待确认变量。\n')
report_lines.append('- `.1` 后缀总分与主问卷总分明显不一致，本轮清洗保留审计但不用于主分析。\n')

report_lines.append('\n## 2. 量表名称和当前解释\n')
report_lines.append('- `CIAS/CIASSUM/I1–I26`：CIAS，中文网络成瘾相关量表；本数据中总分等于 I1–I26 求和。\n')
report_lines.append('- `Young/YOUNGSUM/Y1–Y8`：Young 网络成瘾诊断问卷；本数据中总分等于 Y1–Y8 求和。\n')
report_lines.append('- `DSM/DSMSUM1/DSMSUM2/D1–D22`：DSM 相关网络/游戏成瘾诊断条目；D1–D9 对应 DSMSUM1，D10–D22 对应 DSMSUM2。\n')
report_lines.append('- `CAARS/CAARSSUM/C1–C26`：CAARS/ADHD 特质量表；前面说的 `C总分` 应理解为 CAARS 总分，而不是 CIAS。\n')
report_lines.append('- 反向计分：当前文件中各总分都等于条目直接求和；如果原问卷有反向题，也已经体现在编码后的条目中。没有原始问卷手册前，不应再额外反向。\n')

report_lines.append('\n## 3. CPT 标签解释\n')
report_lines.append('- `N`：Normal/正常。\n')
report_lines.append('- `I`：Inattentive/注意缺陷型。\n')
report_lines.append('- `C`：Combined/混合型。\n')
report_lines.append('- `I?`、`C?`：疑似注意缺陷型/疑似混合型，正式主分析建议先作为不确定分类。\n')
report_lines.append('- `?`：未知或无法确定。\n')

report_lines.append('\n## 4. 样本和任务可用性\n')
report_lines.append(avail.to_markdown(index=False))
report_lines.append('\n')
report_lines.append('\n## 5. CPT 分类计数\n')
report_lines.append(counts[counts['variable'].eq('CPT_label_clean')].to_markdown(index=False))
report_lines.append('\n')
report_lines.append('\n## 6. 量表信度/计分审计\n')
report_lines.append(scale_audit[['scale','n_items','n_total_nonmissing','total_min','total_max','n_itemsum_total_discrepancies','max_abs_itemsum_total_diff','cronbach_alpha_raw_items']].to_markdown(index=False))
report_lines.append('\n')
report_lines.append('\n## 7. 清洗后探索性结果提示\n')
# Top CAARS correlations and CPT effect sizes
caars_top = cor_df[cor_df['questionnaire'].eq('CAARS_total')].head(12)
report_lines.append('### CAARS_total 与实验/CPT指标的 Spearman 相关 Top 12\n')
report_lines.append(caars_top[['metric','spearman_rho','p_value','n']].to_markdown(index=False))
report_lines.append('\n')
report_lines.append('### CPT: Normal vs I/C 的效应量 Top 12，d 为 ADHD(I/C) - Normal\n')
report_lines.append(effect_df.head(12)[['metric','N_normal','N_ADHD_IC','mean_Normal','mean_ADHD_IC','cohen_d_ADHD_minus_Normal','mannwhitney_p']].to_markdown(index=False))
report_lines.append('\n')
report_lines.append('\n## 8. 建议的主分析原则\n')
report_lines.append('1. 第一篇论文主分类建议用 `CPT_label_clean` 中确定的 N/I/C；`I?`、`C?`、`?` 用于敏感性分析。\n')
report_lines.append('2. 问卷中的 ADHD 特质主变量用 `CAARS_total`；网络成瘾主变量用 `CIAS_total`，辅以 `Young_total` 和 `DSM_total1/2`。\n')
report_lines.append('3. 实验任务用任务特异 QC flag，不建议一刀切删除整行。\n')
report_lines.append('4. CPT 原始报告本身可以作为持续注意/分类依据，也可作为真实行为指标。\n')
report_lines.append('5. 正式论文中对“ADHD 特质与实验任务关系弱/强”的判断，应基于清洗后的相关、效应量和稳健性分析，不再基于初步审计。\n')

(OUT/'ADHD_data_cleaning_report.md').write_text('\n'.join(report_lines), encoding='utf-8')

# Bundle outputs
bundle_files = [
    'clean_ADHD_experiment_master_liberal.csv',
    'clean_ADHD_experiment_master_strict_flags.csv',
    'CPT_parsed_metrics.csv',
    'cleaned_data_dictionary.csv',
    'scale_score_reliability_audit.csv',
    'alternative_totals_do_not_use_audit.csv',
    'cleaning_task_availability.csv',
    'cleaning_group_CPT_counts.csv',
    'cleaned_metric_descriptives.csv',
    'cleaned_questionnaire_task_spearman_all.csv',
    'cleaned_questionnaire_task_spearman_top80.csv',
    'cleaned_CPT_N_vs_ADHD_effect_sizes.csv',
    'cleaned_CPT_group_summary.csv',
    'ADHD_data_cleaning_report.md',
    'clean_adhd_experiment.py',
]
with zipfile.ZipFile(OUT/'ADHD_cleaned_outputs.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for fn in bundle_files:
        p=OUT/fn
        if p.exists(): z.write(p, arcname=fn)

# brief stdout summary
print(json.dumps({
    'n_base_rows': int(base.shape[0]),
    'n_cpt_docs': int(len(cpt_df)),
    'n_cpt_parsed_ok': int(cpt_df['cpt_parse_ok'].fillna(False).sum()),
    'outputs': bundle_files,
}, ensure_ascii=False, indent=2))
