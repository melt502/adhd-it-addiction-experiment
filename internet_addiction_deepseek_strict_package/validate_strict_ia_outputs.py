#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate strict DeepSeek IA outputs and summarize range validity by task."""

from __future__ import annotations
import argparse
import pandas as pd
from pathlib import Path

TASK_RANGES = {
    "stroop": {"accuracy": (0,1), "mean_rt_ms": (150,3000), "rt_sd_ms": (0,2000), "interference_effect_ms": (-500,1500)},
    "nback": {"overall_accuracy": (0,1), "accuracy_1back": (0,1), "accuracy_2back": (0,1), "accuracy_3back": (0,1)},
    "bart": {"adjusted_average_pumps": (0,64), "total_earnings": (0,64), "explosion_count": (0,30), "risk_preference_0_1": (0,1)},
    "ddt": {"discounting_k": (0,1), "log_discounting_k": (-20,0), "immediate_choice_proportion": (0,1)},
    "questionnaire": {"caars_total": (0,78), "cias_total": (26,104), "young_total": (0,8), "dsm_total1": (0,9), "dsm_total2": (0,13)},
}

def validate_row(row):
    task = row.get("task_id")
    if task not in TASK_RANGES:
        return False
    for col, (lo, hi) in TASK_RANGES[task].items():
        if col not in row or pd.isna(row[col]):
            return False
        try:
            val = float(row[col])
        except Exception:
            return False
        if not (lo <= val <= hi):
            return False
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.input)
    df["range_valid_recheck"] = df.apply(validate_row, axis=1)
    df.to_csv(out / "range_rechecked_outputs.csv", index=False)
    keys = [c for c in ["model", "experiment_type", "condition_id", "profile_id", "task_id"] if c in df.columns]
    if keys:
        summary = df.groupby(keys)["range_valid_recheck"].agg(["count", "sum", "mean"]).reset_index()
        summary = summary.rename(columns={"count": "n", "sum": "n_valid", "mean": "valid_rate"})
        summary.to_csv(out / "range_validity_summary.csv", index=False)
    task_summary = df.groupby("task_id")["range_valid_recheck"].agg(["count","sum","mean"]).reset_index()
    task_summary = task_summary.rename(columns={"count":"n","sum":"n_valid","mean":"valid_rate"})
    task_summary.to_csv(out / "range_validity_by_task.csv", index=False)
    print(task_summary)

if __name__ == "__main__":
    main()
