#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create JSONL prompt files for the 2^3 Cue-Competition experiment.

Factors:
  L = diagnostic/profile label cue
  Q = anonymized quantitative score cue
  D = symptom-language cue

Outputs:
  cue_competition_factorial_8conditions_full5tasks.jsonl
  cue_competition_factorial_8conditions_core3tasks.jsonl
  cue_competition_missing4_full5tasks.jsonl
  cue_competition_missing4_core3tasks.jsonl
  cue_competition_prompt_index.csv
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Any, List

OUT = Path(__file__).resolve().parent

PROFILES: Dict[str, Dict[str, Any]] = {
    "P1_low_ADHD_low_IA": {
        "label": "low ADHD-trait and low problematic digital-use profile",
        "score": {"A": 22, "B": 40, "C": 2, "D1": 1, "D2": 2},
        "symptom": "The participant is described as generally able to sustain attention, inhibit inappropriate responses, persist on tasks, and regulate digital-media use. Occasional distraction may occur, but no prominent attention, self-regulation, or problematic digital-use difficulties are described.",
    },
    "P2_inattentive_ADHD": {
        "label": "inattentive ADHD-like profile",
        "score": {"A": 48, "B": 58, "C": 3, "D1": 3, "D2": 4},
        "symptom": "The participant is described as having marked difficulty sustaining attention, frequent distractibility, forgetfulness, disorganization, and reduced task persistence, with comparatively less prominent overt hyperactivity or risk-seeking behavior.",
    },
    "P3_combined_ADHD": {
        "label": "combined ADHD-like profile",
        "score": {"A": 62, "B": 74, "C": 5, "D1": 6, "D2": 8},
        "symptom": "The participant is described as having difficulties with sustained attention, inhibitory control, task persistence, restlessness, and impulsive decision-making across everyday contexts.",
    },
    "P4_ADHD_high_IA": {
        "label": "combined ADHD-like profile with high problematic digital-use profile",
        "score": {"A": 62, "B": 89, "C": 6, "D1": 7, "D2": 10},
        "symptom": "The participant is described as having difficulties with sustained attention, inhibitory control, task persistence, and impulsive decision-making, together with strong attraction to immediate digital rewards, difficulty stopping online activity, and interference of digital use with daily functioning.",
    },
    "P5_high_IA_low_ADHD": {
        "label": "low ADHD-trait profile with high problematic digital-use profile",
        "score": {"A": 18, "B": 89, "C": 6, "D1": 7, "D2": 10},
        "symptom": "The participant is described as generally capable of sustained attention and behavioral self-regulation in non-digital settings, but shows strong attraction to digital rewards, difficulty stopping online activity, and interference of digital use with daily routines.",
    },
}

CONDITIONS: Dict[str, Dict[str, Any]] = {
    "C000_no_cue": {"label_cue": 0, "score_cue": 0, "symptom_cue": 0, "condition_name": "no-cue"},
    "C100_label_only": {"label_cue": 1, "score_cue": 0, "symptom_cue": 0, "condition_name": "label-only"},
    "C010_score_only": {"label_cue": 0, "score_cue": 1, "symptom_cue": 0, "condition_name": "score-only"},
    "C001_symptom_only": {"label_cue": 0, "score_cue": 0, "symptom_cue": 1, "condition_name": "symptom-only"},
    "C110_label_score": {"label_cue": 1, "score_cue": 1, "symptom_cue": 0, "condition_name": "label+score"},
    "C101_label_symptom": {"label_cue": 1, "score_cue": 0, "symptom_cue": 1, "condition_name": "label+symptom"},
    "C011_score_symptom": {"label_cue": 0, "score_cue": 1, "symptom_cue": 1, "condition_name": "score+symptom"},
    "C111_full_profile": {"label_cue": 1, "score_cue": 1, "symptom_cue": 1, "condition_name": "full-profile"},
}

MISSING4 = ["C000_no_cue", "C110_label_score", "C101_label_symptom", "C011_score_symptom"]

TASKS: Dict[str, Dict[str, Any]] = {
    "stroop": {
        "task_code": "T1_stroop",
        "task_text": "Stroop color-word task",
        "instruction": "Predict the participant's performance on a computerized Stroop color-word task.",
        "json_keys": {
            "accuracy": "number between 0 and 1",
            "mean_rt_ms": "number in milliseconds",
            "rt_sd_ms": "number in milliseconds",
            "interference_effect_ms": "number in milliseconds"
        },
    },
    "nback": {
        "task_code": "T2_nback",
        "task_text": "n-back working-memory task",
        "instruction": "Predict the participant's performance on a computerized n-back working-memory task with 1-back, 2-back, and 3-back blocks.",
        "json_keys": {
            "overall_accuracy": "number between 0 and 1",
            "accuracy_1back": "number between 0 and 1",
            "accuracy_2back": "number between 0 and 1",
            "accuracy_3back": "number between 0 and 1"
        },
    },
    "bart": {
        "task_code": "T3_bart",
        "task_text": "Balloon Analogue Risk Task",
        "instruction": "Predict the participant's performance on the Balloon Analogue Risk Task.",
        "json_keys": {
            "adjusted_average_pumps": "number between 0 and 64",
            "total_earnings": "number",
            "explosion_count": "number",
            "risk_preference_0_1": "number between 0 and 1"
        },
    },
    "ddt": {
        "task_code": "T4_ddt",
        "task_text": "delay discounting task",
        "instruction": "Predict the participant's performance on a delay discounting task.",
        "json_keys": {
            "discounting_k": "positive number",
            "log_discounting_k": "number",
            "immediate_choice_proportion": "number between 0 and 1"
        },
    },
    "questionnaire": {
        "task_code": "T5_questionnaire",
        "task_text": "questionnaire totals",
        "instruction": "Estimate questionnaire total scores for this participant profile. This task is mainly recorded for completeness and should not be used as the primary behavioral cue-competition outcome.",
        "json_keys": {
            "caars_total": "number between 0 and 78",
            "cias_total": "number between 26 and 104",
            "young_total": "number between 0 and 8",
            "dsm_total1": "number between 0 and 9",
            "dsm_total2": "number between 0 and 13"
        },
    },
}

CORE_TASKS = ["stroop", "nback", "bart"]

SYSTEM = (
    "You are a behavioral prediction model used for a controlled prompt-cue experiment. "
    "Return only one valid JSON object matching the required numeric schema. "
    "Do not provide explanations, markdown, comments, or qualitative labels. "
    "All output values must be numeric."
)


def score_text(score: Dict[str, int]) -> str:
    return (
        f"Scale A total = {score['A']} out of 78; "
        f"Scale B total = {score['B']} out of 104; "
        f"Scale C total = {score['C']} out of 8; "
        f"Scale D1 total = {score['D1']} out of 9; "
        f"Scale D2 total = {score['D2']} out of 13. "
        "Higher Scale A indicates greater difficulties on an attention/self-regulation dimension. "
        "Higher Scale B, C, D1, and D2 indicate greater difficulties on digital-use-related dimensions. "
        "Do not infer or mention any diagnostic label from the scale names."
    )


def build_instruction(condition_id: str, profile_id: str, task_id: str) -> str:
    c = CONDITIONS[condition_id]
    p = PROFILES[profile_id]
    t = TASKS[task_id]

    pieces: List[str] = [t["instruction"]]

    if c["label_cue"]:
        pieces.append(f"Participant profile label: {p['label']}.")
    if c["score_cue"]:
        pieces.append(score_text(p["score"]))
    if c["symptom_cue"]:
        pieces.append(f"Symptom description: {p['symptom']}")
    if not (c["label_cue"] or c["score_cue"] or c["symptom_cue"]):
        pieces.append(
            "No diagnostic/profile label, questionnaire score, or symptom description is provided. "
            "Make a calibrated prediction for a young adult participant based only on the task context."
        )

    pieces.append(
        "Use calibrated numeric predictions for a young adult participant. "
        "Return only the required JSON object. Do not use words such as low, medium, high, normal, severe, typical, elevated, or moderate as output values."
    )
    return " ".join(pieces)


def make_record(condition_id: str, profile_id: str, task_id: str, prompt_index: int) -> Dict[str, Any]:
    c = CONDITIONS[condition_id]
    t = TASKS[task_id]
    prompt_id = f"{condition_id}__{profile_id}__{task_id}"
    return {
        "prompt_index": prompt_index,
        "prompt_id": prompt_id,
        "experiment_type": "cue_competition_factorial",
        "condition_id": condition_id,
        "ablation_condition": condition_id,
        "condition_name": c["condition_name"],
        "label_cue": c["label_cue"],
        "score_cue": c["score_cue"],
        "symptom_cue": c["symptom_cue"],
        "profile_id": profile_id,
        "task_id": task_id,
        "task_code": t["task_code"],
        "system": SYSTEM,
        "user": {
            "instruction": build_instruction(condition_id, profile_id, task_id),
            "required_output": {"json_keys": t["json_keys"]},
        },
    }


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def build_records(condition_ids: List[str], task_ids: List[str]) -> List[Dict[str, Any]]:
    records = []
    idx = 1
    for cid in condition_ids:
        for pid in PROFILES:
            for tid in task_ids:
                records.append(make_record(cid, pid, tid, idx))
                idx += 1
    return records


def main() -> None:
    all_cond = list(CONDITIONS.keys())
    full_records = build_records(all_cond, list(TASKS.keys()))
    core_records = build_records(all_cond, CORE_TASKS)
    missing_full = build_records(MISSING4, list(TASKS.keys()))
    missing_core = build_records(MISSING4, CORE_TASKS)

    write_jsonl(OUT / "cue_competition_factorial_8conditions_full5tasks.jsonl", full_records)
    write_jsonl(OUT / "cue_competition_factorial_8conditions_core3tasks.jsonl", core_records)
    write_jsonl(OUT / "cue_competition_missing4_full5tasks.jsonl", missing_full)
    write_jsonl(OUT / "cue_competition_missing4_core3tasks.jsonl", missing_core)

    with (OUT / "cue_competition_prompt_index.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "prompt_index", "prompt_id", "condition_id", "condition_name",
            "label_cue", "score_cue", "symptom_cue", "profile_id", "task_id", "task_code"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in full_records:
            writer.writerow({k: r.get(k) for k in fieldnames})

    print("Created prompt files in", OUT)
    print("Full 8-condition, 5-task prompts:", len(full_records))
    print("Core 8-condition, 3-task prompts:", len(core_records))
    print("Missing4, 5-task prompts:", len(missing_full))
    print("Missing4, 3-task prompts:", len(missing_core))


if __name__ == "__main__":
    main()
