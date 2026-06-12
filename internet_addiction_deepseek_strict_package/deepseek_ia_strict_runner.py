#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek strict-range runner for problematic digital-use / internet-addiction experiments.

This runner is designed for rerunning DeepSeek outputs that previously produced
out-of-range values in n-back, BART, and questionnaire tasks.

Main features
-------------
1. OpenAI-compatible DeepSeek API call with JSON mode.
2. Batched repeated sampling: one API call returns multiple independent samples.
3. Strict local range validation for every output field.
4. Invalid samples are rejected and logged, not clamped by default.
5. Metadata preservation: run_id, call_id, batch_id, model, prompt_id,
   experiment_type, condition_id, profile_id, task_id, repeat_id.
6. Resume support: existing valid samples are counted and only missing samples are run.
7. Outputs:
   - sample_level_outputs.csv
   - sample_level_outputs.jsonl
   - raw_calls.jsonl
   - invalid_samples.jsonl
   - completion_summary.csv
   - validation_summary.csv

Environment variables
---------------------
DEEPSEEK_API_KEY       API key
DEEPSEEK_BASE_URL      Default: https://api.deepseek.com/v1

Example
-------
python deepseek_ia_strict_runner.py \
  --input ia_main_profile_prompts_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_main_strict \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from tqdm import tqdm

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
REQUEST_TIMEOUT = 180

TASK_RANGES = {
    "stroop": {
        "accuracy": ("number", 0.0, 1.0),
        "mean_rt_ms": ("number", 150.0, 3000.0),
        "rt_sd_ms": ("number", 0.0, 2000.0),
        "interference_effect_ms": ("number", -500.0, 1500.0),
    },
    "nback": {
        "overall_accuracy": ("number", 0.0, 1.0),
        "accuracy_1back": ("number", 0.0, 1.0),
        "accuracy_2back": ("number", 0.0, 1.0),
        "accuracy_3back": ("number", 0.0, 1.0),
    },
    "bart": {
        "adjusted_average_pumps": ("number", 0.0, 64.0),
        "total_earnings": ("number", 0.0, 64.0),
        "explosion_count": ("integer", 0, 30),
        "risk_preference_0_1": ("number", 0.0, 1.0),
    },
    "ddt": {
        "discounting_k": ("number", 0.0, 1.0),
        "log_discounting_k": ("number", -20.0, 0.0),
        "immediate_choice_proportion": ("number", 0.0, 1.0),
    },
    "questionnaire": {
        "caars_total": ("number", 0.0, 78.0),
        "cias_total": ("number", 26.0, 104.0),
        "young_total": ("number", 0.0, 8.0),
        "dsm_total1": ("number", 0.0, 9.0),
        "dsm_total2": ("number", 0.0, 13.0),
    },
}

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def stable_hash(obj: Any, n: int = 12) -> str:
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"Invalid JSON at line {line_no}: {e}")
    return records

def append_jsonl(record: Dict[str, Any], path: Path) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def append_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    exists = path.exists()
    # Expand all keys across rows
    keys = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    if exists:
        try:
            old_cols = list(pd.read_csv(path, nrows=0).columns)
            for k in old_cols:
                if k not in seen:
                    keys.insert(0, k)
            for k in list(seen):
                if k not in old_cols:
                    old_cols.append(k)
            keys = old_cols
        except Exception:
            pass
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for r in rows:
            writer.writerow(r)

def extract_json(text: str) -> Optional[Any]:
    if text is None:
        return None
    text = str(text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```json\s*(.*?)\s*```", text, flags=re.S | re.I)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None

def normalize_samples(parsed: Any) -> Optional[List[Dict[str, Any]]]:
    if parsed is None:
        return None
    if isinstance(parsed, list):
        return parsed if all(isinstance(x, dict) for x in parsed) else None
    if isinstance(parsed, dict):
        # common wrappers
        for key in ["samples", "response", "input", "result", "data"]:
            if key in parsed:
                value = parsed[key]
                if key == "samples" and isinstance(value, list):
                    return value
                if isinstance(value, dict) and "samples" in value and isinstance(value["samples"], list):
                    return value["samples"]
        # If no samples wrapper, treat as one sample
        return [parsed]
    return None

def expected_keys_for_task(task_id: str) -> List[str]:
    if task_id not in TASK_RANGES:
        raise ValueError(f"Unknown task_id: {task_id}")
    return list(TASK_RANGES[task_id].keys())

def validate_sample(sample: Dict[str, Any], task_id: str) -> Tuple[bool, Dict[str, Any], List[str]]:
    """Return (valid, clean_values, errors). No clamping."""
    errors = []
    clean: Dict[str, Any] = {}
    ranges = TASK_RANGES[task_id]
    for key, (typ, lo, hi) in ranges.items():
        if key not in sample:
            errors.append(f"missing:{key}")
            continue
        val = sample[key]
        # Reject booleans as numbers
        if isinstance(val, bool):
            errors.append(f"bool_not_number:{key}")
            continue
        try:
            num = float(val)
        except Exception:
            errors.append(f"not_numeric:{key}:{val}")
            continue
        if typ == "integer":
            if not float(num).is_integer():
                errors.append(f"not_integer:{key}:{num}")
                continue
            num = int(num)
        if not (lo <= num <= hi):
            errors.append(f"out_of_range:{key}:{num}:expected[{lo},{hi}]")
            continue
        clean[key] = num
    return (len(errors) == 0), clean, errors

def build_user_prompt(record: Dict[str, Any], n_samples: int) -> str:
    """Send only the user payload and strict constraints, never the metadata fields."""
    task_id = record.get("task_id")
    user = record.get("user", "")
    if isinstance(user, str):
        original = user
    else:
        original = json.dumps(user, ensure_ascii=False, indent=2)
    ranges = TASK_RANGES[task_id]
    fields = {
        k: {
            "type": typ,
            "minimum": lo,
            "maximum": hi
        }
        for k, (typ, lo, hi) in ranges.items()
    }
    wrapper = {
        "instruction": "Return multiple independent numeric prediction samples for the same prompt.",
        "number_of_samples": n_samples,
        "strict_output_format": {
            "samples": [
                {"sample_id": 1, **{k: f"{typ} in [{lo}, {hi}]" for k, (typ, lo, hi) in ranges.items()}}
            ]
        },
        "hard_rules": [
            f"Return exactly {n_samples} samples.",
            "Return one valid JSON object only with a top-level key named samples.",
            "Every sample must contain sample_id and all required fields.",
            "All output fields must be numeric and inside the specified min/max range.",
            "Proportions and accuracies must be decimals between 0 and 1, not percentages.",
            "BART adjusted_average_pumps must be between 0 and 64.",
            "risk_preference_0_1 must be between 0 and 1.",
            "Questionnaire totals must stay inside their legal scale ranges.",
            "Do not use words such as low, medium, high, typical, elevated, severe, or moderate.",
            "Do not include explanations, markdown, or extra keys."
        ],
        "field_ranges": fields,
        "original_prompt": original,
    }
    return json.dumps(wrapper, ensure_ascii=False, indent=2)

def build_system_prompt(record: Dict[str, Any]) -> str:
    base = str(record.get("system", "")).strip()
    extra = (
        "\nYou are a strict JSON generator. You must return only valid JSON. "
        "All values must satisfy the provided numeric min/max constraints. "
        "Out-of-range values are invalid."
    )
    return base + extra

def call_deepseek(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int = 2048,
) -> Tuple[str, Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
    }
    url = base_url.rstrip("/") + "/chat/completions"
    resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return text, usage

def load_existing_counts(output_dir: Path) -> Dict[str, int]:
    csv_path = output_dir / "sample_level_outputs.csv"
    counts: Dict[str, int] = {}
    if not csv_path.exists():
        return counts
    try:
        df = pd.read_csv(csv_path)
        if "prompt_id" not in df.columns:
            return counts
        for pid, g in df.groupby("prompt_id"):
            counts[str(pid)] = int(len(g))
    except Exception:
        pass
    return counts

def make_sample_row(
    record: Dict[str, Any],
    clean_values: Dict[str, Any],
    provider: str,
    model: str,
    run_id: str,
    call_id: str,
    batch_id: int,
    repeat_id: int,
    sample_in_call: int,
    temperature: float,
    prompt_hash: str,
    usage: Dict[str, Any],
) -> Dict[str, Any]:
    row = {
        "run_id": run_id,
        "call_id": call_id,
        "batch_id": batch_id,
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "timestamp_utc": utc_now(),
        "prompt_id": record.get("prompt_id"),
        "prompt_hash": prompt_hash,
        "experiment_type": record.get("experiment_type"),
        "condition_id": record.get("condition_id"),
        "condition_name": record.get("condition_name"),
        "label_cue": record.get("label_cue"),
        "score_cue": record.get("score_cue"),
        "symptom_cue": record.get("symptom_cue"),
        "profile_id": record.get("profile_id"),
        "profile_short": record.get("profile_short"),
        "ia_like_profile": record.get("ia_like_profile"),
        "task_id": record.get("task_id"),
        "task_name": record.get("task_name"),
        "repeat_id": repeat_id,
        "sample_in_call": sample_in_call,
        "input_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
        "output_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "range_valid": True,
    }
    row.update(clean_values)
    return row

def write_summaries(output_dir: Path) -> None:
    csv_path = output_dir / "sample_level_outputs.csv"
    if not csv_path.exists():
        return
    df = pd.read_csv(csv_path)
    keys = [c for c in ["provider", "model", "experiment_type", "condition_id", "profile_id", "task_id"] if c in df.columns]
    if keys:
        summary = df.groupby(keys).size().reset_index(name="valid_samples")
        summary.to_csv(output_dir / "completion_summary.csv", index=False)
    # validation summary from invalid file
    invalid_path = output_dir / "invalid_samples.jsonl"
    invalid_n = 0
    if invalid_path.exists():
        with invalid_path.open("r", encoding="utf-8") as f:
            invalid_n = sum(1 for _ in f)
    pd.DataFrame([{
        "valid_samples": len(df),
        "invalid_samples_logged": invalid_n,
        "valid_output_file": str(csv_path),
    }]).to_csv(output_dir / "validation_summary.csv", index=False)

def run(args):
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = args.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("Missing API key. Provide --api-key or set DEEPSEEK_API_KEY.")
    base_url = args.base_url or os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)

    records = load_jsonl(input_path)
    if args.tasks:
        allowed = set(args.tasks.split(","))
        records = [r for r in records if r.get("task_id") in allowed]
    if args.prompt_contains:
        records = [r for r in records if args.prompt_contains in str(r.get("prompt_id", ""))]

    print(f"Loaded prompts: {len(records)}")
    print(f"Provider: deepseek-compatible | Model: {args.model}")
    print(f"Target samples per prompt: {args.target_samples}")
    print(f"Samples per call: {args.samples_per_call}")
    print(f"Output dir: {output_dir}")

    if args.dry_run:
        for r in records[:20]:
            print(r.get("prompt_id"), r.get("task_id"), r.get("condition_id"), r.get("profile_id"))
        return

    run_id = args.run_id or f"deepseek_ia_strict_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    counts = load_existing_counts(output_dir) if args.resume else {}

    valid_csv = output_dir / "sample_level_outputs.csv"
    valid_jsonl = output_dir / "sample_level_outputs.jsonl"
    raw_jsonl = output_dir / "raw_calls.jsonl"
    invalid_jsonl = output_dir / "invalid_samples.jsonl"

    batch_id = 0
    global_repeat_counter = 0

    for record in tqdm(records, desc="Prompts"):
        pid = str(record.get("prompt_id"))
        already = counts.get(pid, 0)
        while already < args.target_samples:
            needed = args.target_samples - already
            n_call = min(args.samples_per_call, needed)
            batch_id += 1
            call_id = str(uuid.uuid4())
            prompt_hash = stable_hash(record)
            system_prompt = build_system_prompt(record)
            user_prompt = build_user_prompt(record, n_call)
            started = time.time()

            try:
                text, usage = call_deepseek(
                    api_key=api_key,
                    base_url=base_url,
                    model=args.model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                )
                raw = {
                    "run_id": run_id,
                    "call_id": call_id,
                    "batch_id": batch_id,
                    "timestamp_utc": utc_now(),
                    "prompt_id": pid,
                    "task_id": record.get("task_id"),
                    "model": args.model,
                    "temperature": args.temperature,
                    "requested_samples": n_call,
                    "raw_text": text,
                    "usage": usage,
                    "elapsed_seconds": time.time() - started,
                }
                append_jsonl(raw, raw_jsonl)

                parsed = extract_json(text)
                samples = normalize_samples(parsed)
                if samples is None:
                    append_jsonl({**raw, "error": "parse_failed"}, invalid_jsonl)
                    continue

                valid_rows = []
                for j, sample in enumerate(samples, start=1):
                    valid, clean_values, errors = validate_sample(sample, record.get("task_id"))
                    if valid:
                        global_repeat_counter += 1
                        row = make_sample_row(
                            record=record,
                            clean_values=clean_values,
                            provider="deepseek",
                            model=args.model,
                            run_id=run_id,
                            call_id=call_id,
                            batch_id=batch_id,
                            repeat_id=already + len(valid_rows) + 1,
                            sample_in_call=j,
                            temperature=args.temperature,
                            prompt_hash=prompt_hash,
                            usage=usage,
                        )
                        valid_rows.append(row)
                    else:
                        append_jsonl({
                            "run_id": run_id,
                            "call_id": call_id,
                            "batch_id": batch_id,
                            "prompt_id": pid,
                            "task_id": record.get("task_id"),
                            "sample_in_call": j,
                            "sample": sample,
                            "errors": errors,
                            "timestamp_utc": utc_now(),
                        }, invalid_jsonl)

                if valid_rows:
                    append_csv(valid_rows, valid_csv)
                    for row in valid_rows:
                        append_jsonl(row, valid_jsonl)
                    already += len(valid_rows)
                    counts[pid] = already

                if args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)

            except Exception as e:
                append_jsonl({
                    "run_id": run_id,
                    "call_id": call_id,
                    "batch_id": batch_id,
                    "prompt_id": pid,
                    "task_id": record.get("task_id"),
                    "error": repr(e),
                    "timestamp_utc": utc_now(),
                    "elapsed_seconds": time.time() - started,
                }, invalid_jsonl)
                time.sleep(max(args.sleep_seconds, 1.0))

    write_summaries(output_dir)
    print("Done.")
    print(f"Valid outputs: {valid_csv}")
    print(f"Invalid samples: {invalid_jsonl}")
    print(f"Raw calls: {raw_jsonl}")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Strict JSONL prompt file")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--model", default="deepseek-chat")
    p.add_argument("--api-key", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--target-samples", type=int, default=50)
    p.add_argument("--samples-per-call", type=int, default=5)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--sleep-seconds", type=float, default=0.2)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--tasks", default=None, help="Optional comma-separated tasks, e.g. nback,bart,questionnaire")
    p.add_argument("--prompt-contains", default=None, help="Optional substring filter for prompt_id")
    p.add_argument("--run-id", default=None)
    return p.parse_args()

if __name__ == "__main__":
    run(parse_args())
