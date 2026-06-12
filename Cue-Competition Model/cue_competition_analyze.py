#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cue-Competition Model Analysis
==============================

Inputs:
  --llm-csv one or more sample_level_outputs.csv files from cue_competition_runner.py
  --human-input individual_prediction_input.csv

Outputs:
  metric_long_with_stereo_z.csv
  condition_metric_summary.csv
  cue_competition_ols_coefficients.csv
  cue_dominance_indices.csv
  model_condition_summary.csv
  analysis_report.md
  plots/*.png

Model:
  stereo_z ~ label_cue * score_cue * symptom_cue + C(profile_id) + C(metric_id) + C(model_key)

For per-model results:
  stereo_z ~ label_cue * score_cue * symptom_cue + C(profile_id) + C(metric_id)
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd

try:
    import statsmodels.formula.api as smf
except Exception:
    smf = None

import matplotlib.pyplot as plt


METRICS = [
    {
        "metric_id": "stroop_accuracy",
        "task_id": "stroop",
        "llm_col": "accuracy",
        "human_col": "true_stroop_accuracy",
        "valid_col": "stroop_valid_strict",
        "direction": -1,
        "description": "Stroop accuracy; stereotype direction = lower accuracy",
    },
    {
        "metric_id": "stroop_mean_rt_ms",
        "task_id": "stroop",
        "llm_col": "mean_rt_ms",
        "human_col": "true_stroop_mean_rt_ms",
        "valid_col": "stroop_valid_strict",
        "direction": +1,
        "description": "Stroop mean RT; stereotype direction = slower responses",
    },
    {
        "metric_id": "nback_overall_accuracy",
        "task_id": "nback",
        "llm_col": "overall_accuracy",
        "human_col": "true_nback_overall_accuracy",
        "valid_col": "nback_valid_strict",
        "direction": -1,
        "description": "n-back overall accuracy; stereotype direction = lower accuracy",
    },
    {
        "metric_id": "bart_adjusted_average_pumps",
        "task_id": "bart",
        "llm_col": "adjusted_average_pumps",
        "human_col": "true_bart_adjusted_average_pumps",
        "valid_col": "bart_valid_strict",
        "direction": +1,
        "description": "BART adjusted average pumps; stereotype direction = higher risk-taking",
    },
    {
        "metric_id": "ddt_log_discounting_k",
        "task_id": "ddt",
        "llm_col": "log_discounting_k",
        "human_col": "true_ddt_log_discounting_k",
        "valid_col": "ddt_valid_strict",
        "direction": +1,
        "description": "DDT log k; stereotype direction = stronger delay discounting",
    },
]

# Map previous ablation condition names to factorial cue indicators.
CONDITION_MAP = {
    "C000_no_cue": (0, 0, 0, "no-cue"),
    "C100_label_only": (1, 0, 0, "label-only"),
    "A_label_only": (1, 0, 0, "label-only"),
    "C010_score_only": (0, 1, 0, "score-only"),
    "B_score_only": (0, 1, 0, "score-only"),
    "C001_symptom_only": (0, 0, 1, "symptom-only"),
    "C_symptom_only": (0, 0, 1, "symptom-only"),
    "C110_label_score": (1, 1, 0, "label+score"),
    "C101_label_symptom": (1, 0, 1, "label+symptom"),
    "C011_score_symptom": (0, 1, 1, "score+symptom"),
    "C111_full_profile": (1, 1, 1, "full-profile"),
    "D_full_profile": (1, 1, 1, "full-profile"),
}

FACTORIAL_CONDITIONS = set(CONDITION_MAP.keys())


def read_llm(paths: List[Path]) -> pd.DataFrame:
    dfs = []
    for p in paths:
        df = pd.read_csv(p)
        df["source_file"] = str(p)
        dfs.append(df)
    out = pd.concat(dfs, ignore_index=True)
    if "model_key" not in out.columns:
        out["model_key"] = out.get("model", out.get("provider", "unknown")).astype(str)
    else:
        out["model_key"] = out["model_key"].astype(str)
    if "condition_id" not in out.columns:
        out["condition_id"] = out.get("ablation_condition")
    out["condition_id"] = out["condition_id"].fillna(out.get("ablation_condition", "")).astype(str)
    return out


def human_reference(human_path: Path) -> pd.DataFrame:
    h = pd.read_csv(human_path)
    rows = []
    for spec in METRICS:
        col = spec["human_col"]
        valid_col = spec["valid_col"]
        if col not in h.columns:
            raise ValueError(f"Missing human column: {col}")
        x = h[col]
        if valid_col in h.columns:
            mask = h[valid_col].astype(str).str.lower().isin(["true", "1", "yes"])
            x = h.loc[mask, col]
        x = pd.to_numeric(x, errors="coerce").dropna()
        rows.append({
            "metric_id": spec["metric_id"],
            "task_id": spec["task_id"],
            "human_col": col,
            "human_mean": float(x.mean()),
            "human_sd": float(x.std(ddof=1)),
            "human_n": int(x.shape[0]),
            "stereotype_direction": spec["direction"],
            "description": spec["description"],
        })
    ref = pd.DataFrame(rows)
    # Avoid division by zero.
    ref["human_sd"] = ref["human_sd"].replace(0, np.nan)
    return ref


def to_metric_long(llm: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ref_map = ref.set_index("metric_id").to_dict("index")
    for spec in METRICS:
        task = spec["task_id"]
        col = spec["llm_col"]
        mid = spec["metric_id"]
        if col not in llm.columns:
            continue
        sub = llm.loc[llm["task_id"].astype(str) == task].copy()
        if sub.empty:
            continue
        sub["value"] = pd.to_numeric(sub[col], errors="coerce")
        sub = sub.dropna(subset=["value"])
        if sub.empty:
            continue
        rr = ref_map[mid]
        sub["metric_id"] = mid
        sub["human_mean"] = rr["human_mean"]
        sub["human_sd"] = rr["human_sd"]
        sub["stereotype_direction"] = rr["stereotype_direction"]
        sub["stereo_z"] = sub["stereotype_direction"] * (sub["value"] - sub["human_mean"]) / sub["human_sd"]
        keep = [
            "source_file", "provider", "model", "model_key", "temperature", "prompt_id", "condition_id",
            "ablation_condition", "condition_name", "label_cue", "score_cue", "symptom_cue",
            "profile_id", "task_id", "repeat_id", "sample_in_call", "success",
            "metric_id", "value", "human_mean", "human_sd", "stereotype_direction", "stereo_z"
        ]
        for k in keep:
            if k not in sub.columns:
                sub[k] = np.nan
        rows.append(sub[keep])
    if not rows:
        raise ValueError("No valid LLM metric rows found")
    long = pd.concat(rows, ignore_index=True)
    # Fill factor indicators from condition map where necessary.
    for idx, row in long.iterrows():
        cid = str(row.get("condition_id"))
        if cid in CONDITION_MAP:
            L, Q, D, cname = CONDITION_MAP[cid]
            long.at[idx, "label_cue"] = L
            long.at[idx, "score_cue"] = Q
            long.at[idx, "symptom_cue"] = D
            long.at[idx, "condition_name"] = cname
    long["label_cue"] = pd.to_numeric(long["label_cue"], errors="coerce")
    long["score_cue"] = pd.to_numeric(long["score_cue"], errors="coerce")
    long["symptom_cue"] = pd.to_numeric(long["symptom_cue"], errors="coerce")
    long = long.dropna(subset=["label_cue", "score_cue", "symptom_cue", "stereo_z"])
    long["label_cue"] = long["label_cue"].astype(int)
    long["score_cue"] = long["score_cue"].astype(int)
    long["symptom_cue"] = long["symptom_cue"].astype(int)
    return long


def summarize(long: pd.DataFrame, outdir: Path) -> None:
    summary = (
        long.groupby(["model_key", "condition_id", "condition_name", "label_cue", "score_cue", "symptom_cue", "task_id", "metric_id"])
        .agg(n=("stereo_z", "size"), mean_z=("stereo_z", "mean"), sd_z=("stereo_z", "std"), mean_value=("value", "mean"))
        .reset_index()
    )
    summary.to_csv(outdir / "condition_metric_summary.csv", index=False, encoding="utf-8-sig")

    model_cond = (
        long.groupby(["model_key", "condition_id", "condition_name", "label_cue", "score_cue", "symptom_cue"])
        .agg(n=("stereo_z", "size"), mean_stereo_z=("stereo_z", "mean"), sd_stereo_z=("stereo_z", "std"))
        .reset_index()
    )
    model_cond.to_csv(outdir / "model_condition_summary.csv", index=False, encoding="utf-8-sig")


def run_ols(long: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    if smf is None:
        raise RuntimeError("statsmodels is required for OLS. Install with: pip install statsmodels")
    formula = (
        "stereo_z ~ label_cue * score_cue * symptom_cue + "
        "C(profile_id) + C(metric_id) + C(model_key)"
    )
    fit = smf.ols(formula, data=long).fit(cov_type="HC3")
    coef = pd.DataFrame({
        "term": fit.params.index,
        "estimate": fit.params.values,
        "std_error": fit.bse.values,
        "z_or_t": fit.tvalues.values,
        "p_value": fit.pvalues.values,
        "ci_low": fit.conf_int()[0].values,
        "ci_high": fit.conf_int()[1].values,
    })
    coef.to_csv(outdir / "cue_competition_ols_coefficients_pooled.csv", index=False, encoding="utf-8-sig")

    # Per-model coefficients.
    all_pm = []
    for model, sub in long.groupby("model_key"):
        if sub["label_cue"].nunique() < 2 or sub["score_cue"].nunique() < 2 or sub["symptom_cue"].nunique() < 2:
            continue
        f2 = "stereo_z ~ label_cue * score_cue * symptom_cue + C(profile_id) + C(metric_id)"
        fit2 = smf.ols(f2, data=sub).fit(cov_type="HC3")
        pm = pd.DataFrame({
            "model_key": model,
            "term": fit2.params.index,
            "estimate": fit2.params.values,
            "std_error": fit2.bse.values,
            "z_or_t": fit2.tvalues.values,
            "p_value": fit2.pvalues.values,
            "ci_low": fit2.conf_int()[0].values,
            "ci_high": fit2.conf_int()[1].values,
        })
        all_pm.append(pm)
    if all_pm:
        pd.concat(all_pm, ignore_index=True).to_csv(outdir / "cue_competition_ols_coefficients_by_model.csv", index=False, encoding="utf-8-sig")
    return coef


def dominance_indices(outdir: Path) -> pd.DataFrame:
    path = outdir / "cue_competition_ols_coefficients_by_model.csv"
    if not path.exists():
        return pd.DataFrame()
    coef = pd.read_csv(path)
    rows = []
    for model, sub in coef.groupby("model_key"):
        terms = sub.set_index("term")["estimate"].to_dict()
        bL = float(terms.get("label_cue", np.nan))
        bQ = float(terms.get("score_cue", np.nan))
        bD = float(terms.get("symptom_cue", np.nan))
        denom = abs(bL) + abs(bQ) + abs(bD)
        rows.append({
            "model_key": model,
            "beta_label": bL,
            "beta_score": bQ,
            "beta_symptom": bD,
            "label_dominance_index": abs(bL) / denom if denom else np.nan,
            "score_reliance_index": abs(bQ) / denom if denom else np.nan,
            "symptom_language_dominance_index": abs(bD) / denom if denom else np.nan,
            "semantic_cue_share_label_plus_symptom": (abs(bL) + abs(bD)) / denom if denom else np.nan,
        })
    out = pd.DataFrame(rows)
    out.to_csv(outdir / "cue_dominance_indices.csv", index=False, encoding="utf-8-sig")
    return out


def make_plots(outdir: Path) -> None:
    plots = outdir / "plots"
    plots.mkdir(exist_ok=True)
    cond = pd.read_csv(outdir / "model_condition_summary.csv")
    # Condition mean z plot.
    pivot = cond.pivot_table(index="condition_name", columns="model_key", values="mean_stereo_z", aggfunc="mean")
    desired_order = ["no-cue", "label-only", "score-only", "symptom-only", "label+score", "label+symptom", "score+symptom", "full-profile"]
    pivot = pivot.reindex([x for x in desired_order if x in pivot.index])
    ax = pivot.plot(kind="bar", figsize=(10, 5))
    ax.set_ylabel("Mean stereotype-oriented z-score")
    ax.set_xlabel("Cue condition")
    ax.set_title("Cue-Competition: stereotype-oriented output by condition")
    plt.tight_layout()
    plt.savefig(plots / "condition_mean_stereo_z.png", dpi=200)
    plt.close()

    dom_path = outdir / "cue_dominance_indices.csv"
    if dom_path.exists():
        dom = pd.read_csv(dom_path)
        if not dom.empty:
            cols = ["label_dominance_index", "score_reliance_index", "symptom_language_dominance_index"]
            ax = dom.set_index("model_key")[cols].plot(kind="bar", figsize=(9, 5))
            ax.set_ylabel("Relative absolute contribution")
            ax.set_xlabel("Model")
            ax.set_title("Cue dominance indices")
            plt.tight_layout()
            plt.savefig(plots / "cue_dominance_indices.png", dpi=200)
            plt.close()


def write_report(outdir: Path, ref: pd.DataFrame, coef: pd.DataFrame, dom: pd.DataFrame, long: pd.DataFrame) -> None:
    def coef_line(term: str) -> str:
        row = coef.loc[coef["term"] == term]
        if row.empty:
            return f"- `{term}`: not estimated"
        r = row.iloc[0]
        return f"- `{term}`: estimate = {r['estimate']:.3f}, 95% CI [{r['ci_low']:.3f}, {r['ci_high']:.3f}], p = {r['p_value']:.3g}"

    lines = []
    lines.append("# Cue-Competition Model Analysis Report")
    lines.append("")
    lines.append("## Human reference metrics")
    lines.append(ref.to_markdown(index=False))
    lines.append("")
    lines.append("## Main pooled cue effects")
    for term in ["label_cue", "score_cue", "symptom_cue", "label_cue:score_cue", "label_cue:symptom_cue", "score_cue:symptom_cue", "label_cue:score_cue:symptom_cue"]:
        lines.append(coef_line(term))
    lines.append("")
    lines.append("## Dominance indices by model")
    if dom is not None and not dom.empty:
        lines.append(dom.to_markdown(index=False))
    else:
        lines.append("No per-model dominance indices were estimated.")
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("- Positive `label_cue`, `score_cue`, or `symptom_cue` coefficients mean that the corresponding cue increases outputs in the ADHD-stereotyped direction after human-standardization.")
    lines.append("- A high label dominance index indicates that diagnostic/profile labels contribute more strongly than anonymized scores or symptom-language cues.")
    lines.append("- A high semantic cue share, i.e. label + symptom dominance, supports the interpretation that semantic clinical cues dominate quantitative individual information.")
    lines.append("")
    lines.append(f"Total metric-level rows analyzed: {len(long)}")
    (outdir / "analysis_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm-csv", nargs="+", required=True, help="sample_level_outputs CSV files")
    ap.add_argument("--human-input", required=True, help="individual_prediction_input.csv")
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    llm = read_llm([Path(x) for x in args.llm_csv])
    ref = human_reference(Path(args.human_input))
    ref.to_csv(outdir / "human_metric_reference.csv", index=False, encoding="utf-8-sig")
    long = to_metric_long(llm, ref)

    # Keep only full factorial conditions for main model.
    long = long[long["condition_name"].isin(["no-cue", "label-only", "score-only", "symptom-only", "label+score", "label+symptom", "score+symptom", "full-profile"])].copy()
    long.to_csv(outdir / "metric_long_with_stereo_z.csv", index=False, encoding="utf-8-sig")
    summarize(long, outdir)
    coef = run_ols(long, outdir)
    dom = dominance_indices(outdir)
    make_plots(outdir)
    write_report(outdir, ref, coef, dom, long)
    print("Analysis complete. Outputs in", outdir)


if __name__ == "__main__":
    main()
