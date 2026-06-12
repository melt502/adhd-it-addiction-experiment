#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze IA/PDU individual prediction outputs."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

TASK_TARGETS={
 'stroop': {'mean_rt_ms':'true_stroop_mean_rt_ms','accuracy':'true_stroop_accuracy'},
 'nback': {'overall_accuracy':'true_nback_overall_accuracy','accuracy_3back':'true_nback_accuracy_3back'},
 'bart': {'adjusted_average_pumps':'true_bart_adjusted_average_pumps','total_earnings':'true_bart_total_earnings'},
 'ddt': {'log_discounting_k':'true_ddt_log_discounting_k'}
}
FEATURES=['age_for_prediction','sex_code_for_prediction','CAARS_total','CIAS_total','Young_total','DSM_total1','DSM_total2']

def corr_safe(x,y,kind='pearson'):
    x=pd.to_numeric(x,errors='coerce'); y=pd.to_numeric(y,errors='coerce')
    mask=x.notna()&y.notna()
    if mask.sum()<5 or x[mask].nunique()<2 or y[mask].nunique()<2: return np.nan
    try:
        return (pearsonr(x[mask],y[mask])[0] if kind=='pearson' else spearmanr(x[mask],y[mask]).correlation)
    except Exception: return np.nan

def evaluate(y,p):
    y=pd.to_numeric(y,errors='coerce'); p=pd.to_numeric(p,errors='coerce')
    mask=y.notna()&p.notna(); y=y[mask]; p=p[mask]
    if len(y)<5: return {}
    rmse=mean_squared_error(y,p,squared=False); mae=mean_absolute_error(y,p)
    denom=((y-y.mean())**2).sum()
    r2=1-((y-p)**2).sum()/denom if denom>0 else np.nan
    return {'n':len(y),'pearson_r':corr_safe(y,p,'pearson'),'spearman_rho':corr_safe(y,p,'spearman'),'mae':mae,'rmse':rmse,'r2_vs_sample_mean':r2}

def analyze(args):
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    pred=pd.concat([pd.read_csv(p) for p in args.llm_csv],ignore_index=True)
    human=pd.read_csv(args.human_input)
    # average repeats
    group_cols=['model','provider','feature_condition','participant_uid','task_id']
    value_cols=[c for c in pred.columns if c in set(sum([list(v.keys()) for v in TASK_TARGETS.values()],[]))]
    avg=pred.groupby(group_cols)[value_cols].mean().reset_index()
    merged=avg.merge(human,on='participant_uid',how='left')
    merged.to_csv(out/'ia_individual_predictions_merged.csv',index=False)
    rows=[]
    for task,mp in TASK_TARGETS.items():
        sub=merged[merged['task_id']==task]
        for pred_col,true_col in mp.items():
            if pred_col not in sub.columns or true_col not in sub.columns: continue
            for (model,cond),g in sub.groupby(['model','feature_condition']):
                ev=evaluate(g[true_col],g[pred_col]); ev.update({'model':model,'feature_condition':cond,'task_id':task,'metric':pred_col,'true_metric':true_col,'method':'LLM'}); rows.append(ev)
    res=pd.DataFrame(rows); res.to_csv(out/'ia_llm_individual_prediction_validity.csv',index=False)
    # simple statistical baselines with 5-fold CV using human data only
    brow=[]
    for task,mp in TASK_TARGETS.items():
        task_df=human.copy()
        for pred_col,true_col in mp.items():
            if true_col not in task_df.columns: continue
            use=task_df[FEATURES+[true_col]].dropna()
            if len(use)<20: continue
            X=use[FEATURES].values; y=use[true_col].values
            kf=KFold(n_splits=5,shuffle=True,random_state=42)
            preds_mean=np.zeros(len(y)); preds_ridge=np.zeros(len(y)); preds_rf=np.zeros(len(y))
            for tr,te in kf.split(X):
                preds_mean[te]=y[tr].mean()
                ridge=make_pipeline(StandardScaler(),RidgeCV(alphas=[0.1,1,10,100])).fit(X[tr],y[tr]); preds_ridge[te]=ridge.predict(X[te])
                rf=RandomForestRegressor(n_estimators=200,random_state=42,min_samples_leaf=5).fit(X[tr],y[tr]); preds_rf[te]=rf.predict(X[te])
            for name,p in [('mean_baseline',preds_mean),('ridge',preds_ridge),('random_forest',preds_rf)]:
                ev=evaluate(pd.Series(y),pd.Series(p)); ev.update({'model':name,'feature_condition':'questionnaire_only','task_id':task,'metric':pred_col,'true_metric':true_col,'method':'statistical_baseline'}); brow.append(ev)
    base=pd.DataFrame(brow); base.to_csv(out/'ia_statistical_baselines.csv',index=False)
    pd.concat([res,base],ignore_index=True).to_csv(out/'ia_individual_prediction_validity_all_methods.csv',index=False)
    print('Outputs saved to',out)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--llm-csv',nargs='+',required=True); ap.add_argument('--human-input',required=True); ap.add_argument('--output-dir',required=True); analyze(ap.parse_args())
if __name__=='__main__': main()
