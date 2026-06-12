#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze IA/PDU main, ablation, and cue-competition outputs."""
from __future__ import annotations
import argparse, math, json
from pathlib import Path
import pandas as pd
import numpy as np

TASK_METRICS={
 'stroop': [('accuracy',-1,'control_impairment'),('mean_rt_ms',1,'control_impairment')],
 'nback': [('overall_accuracy',-1,'working_memory_impairment')],
 'bart': [('adjusted_average_pumps',1,'reward_risk_stereotype')],
 'ddt': [('immediate_choice_proportion',1,'reward_risk_stereotype')],
 'questionnaire': [('cias_total',1,'digital_use_questionnaire'),('young_total',1,'digital_use_questionnaire'),('dsm_total1',1,'digital_use_questionnaire'),('dsm_total2',1,'digital_use_questionnaire')]
}
HUMAN_MAP={
 'accuracy':'true_stroop_accuracy','mean_rt_ms':'true_stroop_mean_rt_ms',
 'overall_accuracy':'true_nback_overall_accuracy','adjusted_average_pumps':'true_bart_adjusted_average_pumps',
 'immediate_choice_proportion':None,
}
IA_PROFILES=['P2_moderate_PDU_low_ATT','P3_high_PDU_low_ATT','P4_high_PDU_high_ATT']
BASE='P1_low_PDU_low_ATT'
CUE_MAP={
 'C000_no_cue':frozenset(), 'C100_label_only':frozenset(['L']), 'C010_score_only':frozenset(['Q']), 'C001_symptom_only':frozenset(['D']),
 'C110_label_score':frozenset(['L','Q']), 'C101_label_symptom':frozenset(['L','D']), 'C011_score_symptom':frozenset(['Q','D']), 'C111_full_profile':frozenset(['L','Q','D']),
}

def read_many(paths):
    dfs=[]
    for p in paths:
        df=pd.read_csv(p)
        dfs.append(df)
    return pd.concat(dfs,ignore_index=True)

def human_ref(path):
    refs={}
    if not path: return refs
    h=pd.read_csv(path)
    for llm_metric,hcol in HUMAN_MAP.items():
        if hcol and hcol in h.columns:
            vals=pd.to_numeric(h[hcol],errors='coerce').dropna()
            if len(vals)>5:
                refs[llm_metric]=(vals.mean(), vals.std() if vals.std()>0 else 1.0)
    return refs

def longify(df, refs):
    rows=[]
    for _,r in df.iterrows():
        task=r.get('task_id')
        for metric, direction, domain in TASK_METRICS.get(task,[]):
            if metric in df.columns and pd.notna(r.get(metric)):
                y=float(r.get(metric))
                mu,sd=refs.get(metric,(df.loc[df['task_id']==task,metric].mean(), df.loc[df['task_id']==task,metric].std()))
                sd=sd if sd and not pd.isna(sd) and sd>0 else 1.0
                rows.append({**{k:r.get(k) for k in ['provider','model','experiment_type','condition_id','condition_name','label_cue','score_cue','symptom_cue','profile_id','task_id','repeat_id']},
                             'metric':metric,'domain':domain,'direction':direction,'y':y,'stereo_z':direction*(y-mu)/sd})
    return pd.DataFrame(rows)

def contrasts(ldf):
    group_cols=['model','condition_id','condition_name','domain','metric']
    means=ldf.groupby(group_cols+['profile_id'])['stereo_z'].mean().reset_index()
    out=[]
    for keys,g in means.groupby(group_cols):
        base=g.loc[g['profile_id']==BASE,'stereo_z']
        ia=g.loc[g['profile_id'].isin(IA_PROFILES),'stereo_z']
        if len(base) and len(ia):
            row=dict(zip(group_cols,keys)); row['baseline_mean']=base.mean(); row['ia_like_mean']=ia.mean(); row['contrast_ia_minus_p1']=ia.mean()-base.mean(); out.append(row)
    return pd.DataFrame(out)

def shapley_for_group(f):
    cues=['L','Q','D']; phi={c:0.0 for c in cues}
    from itertools import combinations
    for j in cues:
        others=[x for x in cues if x!=j]
        for r in range(len(others)+1):
            for comb in combinations(others,r):
                S=frozenset(comb); Sj=S|{j}
                weight=math.factorial(len(S))*math.factorial(3-len(S)-1)/math.factorial(3)
                if S in f and Sj in f:
                    phi[j]+=weight*(f[Sj]-f[S])
    return phi

def analyze(args):
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    df=read_many(args.llm_csv)
    refs=human_ref(args.human_input)
    ldf=longify(df,refs); ldf.to_csv(out/'ia_metric_long_stereo_z.csv',index=False)
    cont=contrasts(ldf); cont.to_csv(out/'ia_condition_metric_contrasts.csv',index=False)
    # condition/domain/model summary
    dom=cont.groupby(['model','condition_id','condition_name','domain'])['contrast_ia_minus_p1'].mean().reset_index()
    dom.to_csv(out/'ia_condition_domain_summary.csv',index=False)
    # Shapley: require 8 cue conditions
    shap=[]
    for (model,domain),g in dom.groupby(['model','domain']):
        f={CUE_MAP[cid]: val for cid,val in zip(g['condition_id'],g['contrast_ia_minus_p1']) if cid in CUE_MAP}
        if len(f)==8:
            phi=shapley_for_group(f)
            denom=sum(abs(v) for v in phi.values()) or np.nan
            shap.append({'model':model,'domain':domain,'phi_label':phi['L'],'phi_score':phi['Q'],'phi_symptom':phi['D'],
                         'semantic_dominance':(abs(phi['L'])+abs(phi['D']))/denom if denom else np.nan,
                         'score_reliance':abs(phi['Q'])/denom if denom else np.nan})
    s=pd.DataFrame(shap); s.to_csv(out/'ia_cue_shapley_by_model_domain.csv',index=False)
    if not s.empty:
        s.groupby('model')[['phi_label','phi_score','phi_symptom','semantic_dominance','score_reliance']].mean().reset_index().to_csv(out/'ia_cue_shapley_by_model_overall.csv',index=False)
    # core report
    with open(out/'ia_analysis_report.md','w',encoding='utf-8') as f:
        f.write('# Internet-addiction / problematic digital-use LLM analysis report\n\n')
        f.write(f'Total LLM rows: {len(df)}; long metric rows: {len(ldf)}.\n\n')
        if not s.empty:
            f.write('## Cue contribution summary\n\n')
            f.write(s.groupby('model')[['phi_label','phi_score','phi_symptom','semantic_dominance','score_reliance']].mean().to_markdown())
            f.write('\n')
    print('Analysis outputs saved to',out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--llm-csv',nargs='+',required=True)
    ap.add_argument('--human-input',default=None)
    ap.add_argument('--output-dir',required=True)
    analyze(ap.parse_args())
if __name__=='__main__': main()
