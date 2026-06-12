#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token-Optimized Prompt Ablation Runner
=====================================

What is optimized?
------------------
The original runner calls the model once per prompt per repeat. For the
5-condition ablation file, this means:

    125 prompts × 50 repeats = 6250 API calls per model.

This script asks the model to return multiple Monte-Carlo samples in one API
call. For example, with --target-samples 50 and --samples-per-call 10:

    125 prompts × 5 calls = 625 API calls per model.

Input tokens are reduced substantially because the same long prompt is not sent
50 times. Output tokens are still roughly proportional to the number of samples.

Important scientific note
-------------------------
Batched samples are not perfectly equivalent to 50 independent API calls because
samples generated in the same response may be correlated. Recommended use:

- Cost-saving pilot / ablation screening: --samples-per-call 10
- Main paper if you want stronger independence: --samples-per-call 5
- Maximum independence, maximum cost: --samples-per-call 1

The script preserves sample-level metadata:
run_id, call_id, provider, model, profile_id, task_id, ablation_condition,
repeat_id, batch_id, sample_in_call.

It sends ONLY the prompt's "system" and "user" fields to the model. Top-level
metadata such as profile_id is used only for local analysis and is not leaked to
the model, which is important for score-only conditions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from tqdm import tqdm

try:
    import openai
except Exception:
    openai = None

try:
    import anthropic
except Exception:
    anthropic = None


DEFAULT_BASE_URLS = {
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com",
    # Change to your MiniMax endpoint if needed.
    "minimax": "https://api.minimax.chat/v1",
}

ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "minimax": "MINIMAX_API_KEY",
}


# ----------------------------
# JSON helpers
# ----------------------------

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"Invalid JSONL at line {lineno}: {e}") from e
    return records


def append_jsonl(record: Dict[str, Any], path: Path) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl_if_exists(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    if text is None:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    # JSON in markdown block
    m = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass

    # First {...}
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


# ----------------------------
# Prompt/schema helpers
# ----------------------------

def get_required_keys(prompt_record: Dict[str, Any]) -> Dict[str, str]:
    """Support both the ablation JSONL and older pilot JSONL formats."""
    user = prompt_record.get("user", {})
    if isinstance(user, dict):
        ro = user.get("required_output", {})
        keys = ro.get("json_keys")
        if isinstance(keys, dict):
            return dict(keys)

        task = user.get("task", {})
        expected = task.get("expected_json_keys")
        if isinstance(expected, list):
            return {k: "number" for k in expected if "rationale" not in k.lower()}

    # Fallback by task_id
    task_id = prompt_record.get("task_id", prompt_record.get("task_code", "")).lower()
    if "stroop" in task_id:
        return {
            "accuracy": "number between 0 and 1",
            "mean_rt_ms": "number in milliseconds",
            "rt_sd_ms": "number in milliseconds",
            "interference_effect_ms": "number in milliseconds",
        }
    if "nback" in task_id or "n-back" in task_id:
        return {
            "overall_accuracy": "number between 0 and 1",
            "accuracy_1back": "number between 0 and 1",
            "accuracy_2back": "number between 0 and 1",
            "accuracy_3back": "number between 0 and 1",
        }
    if "bart" in task_id:
        return {
            "adjusted_average_pumps": "number",
            "total_earnings": "number",
            "explosion_count": "number",
            "risk_preference_0_1": "number between 0 and 1",
        }
    if "ddt" in task_id:
        return {
            "discounting_k": "positive number",
            "log_discounting_k": "number",
            "immediate_choice_proportion": "number between 0 and 1",
        }
    if "questionnaire" in task_id:
        return {
            "caars_total": "number",
            "cias_total": "number",
            "young_total": "number",
            "dsm_total1": "number",
            "dsm_total2": "number",
        }
    raise ValueError(f"Cannot infer required keys for prompt_id={prompt_record.get('prompt_id')}")


def build_batched_schema(required_keys: Dict[str, str], sample_count: int) -> Dict[str, Any]:
    item_properties: Dict[str, Any] = {
        "sample_id": {
            "type": "integer",
            "minimum": 1,
            "maximum": sample_count,
            "description": "1-based sample index within this API call.",
        }
    }
    required = ["sample_id"]
    for k in required_keys:
        item_properties[k] = {
            "type": "number",
            "description": required_keys[k],
        }
        required.append(k)

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "samples": {
                "type": "array",
                "minItems": sample_count,
                "maxItems": sample_count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": item_properties,
                    "required": required,
                },
            }
        },
        "required": ["samples"],
    }


def build_user_prompt(prompt_record: Dict[str, Any], required_keys: Dict[str, str], sample_count: int) -> str:
    """
    Compact prompt. It intentionally sends only prompt_record["user"] to avoid
    leaking top-level profile_id/task_id into score-only or conflict conditions.
    """
    user_payload = prompt_record.get("user", {})
    required_key_list = list(required_keys.keys())

    wrapper = {
        "task_payload": user_payload,
        "monte_carlo_instruction": {
            "n_samples": sample_count,
            "meaning": (
                "Generate exactly n_samples plausible independent numeric predictions "
                "for the same participant profile and task. Samples should reflect "
                "reasonable uncertainty; do not copy identical values unless the task "
                "is truly deterministic."
            ),
            "return_format": (
                "Return one JSON object only: {\"samples\":[...]} . "
                "Each sample must contain sample_id plus the exact numeric keys. "
                "No markdown. No prose. No categories. No rationale."
            ),
            "required_numeric_keys": required_key_list,
        },
    }
    return compact_json(wrapper)


def normalize_samples(parsed: Any) -> Optional[List[Dict[str, Any]]]:
    if not isinstance(parsed, dict):
        return None
    if "samples" in parsed and isinstance(parsed["samples"], list):
        return parsed["samples"]

    # Robust fallback: some models wrap output as {"input": {"samples": [...]}}
    for outer_key in ("input", "response", "output", "arguments"):
        val = parsed.get(outer_key)
        if isinstance(val, dict) and isinstance(val.get("samples"), list):
            return val["samples"]

    # If a model returned one sample directly, wrap it.
    if any(isinstance(v, (int, float)) for v in parsed.values()):
        return [parsed]
    return None


def validate_samples(samples: List[Dict[str, Any]], required_keys: Dict[str, str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    valid: List[Dict[str, Any]] = []
    errors: List[str] = []

    for i, s in enumerate(samples, start=1):
        if not isinstance(s, dict):
            errors.append(f"sample_{i}: not object")
            continue

        row = dict(s)
        if "sample_id" not in row or not isinstance(row.get("sample_id"), int):
            row["sample_id"] = i

        ok = True
        for k in required_keys:
            if k not in row:
                errors.append(f"sample_{i}: missing {k}")
                ok = False
                break
            v = row[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                errors.append(f"sample_{i}: {k} is not numeric: {repr(v)}")
                ok = False
                break

        if ok:
            # keep only sample_id + required keys
            clean = {"sample_id": int(row["sample_id"])}
            clean.update({k: float(row[k]) for k in required_keys})
            valid.append(clean)

    return valid, errors


def prompt_hash(record: Dict[str, Any]) -> str:
    raw = compact_json({"system": record.get("system"), "user": record.get("user")})
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ----------------------------
# Provider calls
# ----------------------------

def call_openai(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    temperature: float,
    max_tokens: int,
    schema_mode: str,
) -> str:
    if openai is None:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    client = openai.OpenAI(api_key=api_key)

    if schema_mode in ("auto", "json_schema", "strict"):
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "batched_predictions",
                "strict": True,
                "schema": schema,
            },
        }
    else:
        response_format = {"type": "json_object"}

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_format,
    )
    return resp.choices[0].message.content or ""


def call_anthropic(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    temperature: float,
    max_tokens: int,
    schema_mode: str,
) -> str:
    if anthropic is None:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    # Prefer tool-use because it constrains the output more strongly.
    if schema_mode in ("auto", "tool", "json_schema", "strict"):
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[
                {
                    "name": "return_predictions",
                    "description": "Return the batched numeric predictions.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": "return_predictions"},
        )
        # Return the tool input as JSON text.
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                return json.dumps(block.input, ensure_ascii=False)
        # fallback to first text block
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return ""

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return resp.content[0].text


def call_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    temperature: float,
    max_tokens: int,
    schema_mode: str,
    timeout: int,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Most compatible endpoints support json_object. Some support json_schema;
    # use --schema-mode json_schema only if your endpoint supports it.
    if schema_mode in ("json_schema", "strict"):
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "batched_predictions",
                "strict": True,
                "schema": schema,
            },
        }
    else:
        response_format = {"type": "json_object"}

    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": response_format,
    }

    r = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"] or ""


def call_model(
    provider: str,
    api_key: str,
    base_url: Optional[str],
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    temperature: float,
    max_tokens: int,
    schema_mode: str,
    timeout: int,
) -> str:
    if provider == "openai":
        return call_openai(api_key, model, system_prompt, user_prompt, schema, temperature, max_tokens, schema_mode)
    if provider == "anthropic":
        return call_anthropic(api_key, model, system_prompt, user_prompt, schema, temperature, max_tokens, schema_mode)
    if provider in ("qwen", "deepseek", "minimax"):
        if not base_url:
            base_url = DEFAULT_BASE_URLS.get(provider)
        if not base_url:
            raise ValueError(f"base_url required for provider={provider}")
        return call_openai_compatible(api_key, base_url, model, system_prompt, user_prompt, schema, temperature, max_tokens, schema_mode, timeout)
    raise ValueError(f"Unknown provider: {provider}")


# ----------------------------
# Resume/progress
# ----------------------------

def count_completed_samples(sample_path: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for rec in read_jsonl_if_exists(sample_path):
        if rec.get("success") and rec.get("prompt_id"):
            counts[rec["prompt_id"]] = counts.get(rec["prompt_id"], 0) + 1
    return counts


def append_sample_rows(
    sample_rows: List[Dict[str, Any]],
    sample_jsonl: Path,
) -> None:
    for row in sample_rows:
        append_jsonl(row, sample_jsonl)


def write_csv_from_jsonl(jsonl_path: Path, csv_path: Path) -> None:
    records = read_jsonl_if_exists(jsonl_path)
    if not records:
        return
    df = pd.DataFrame(records)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")


# ----------------------------
# Main runner
# ----------------------------

def run(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prompts = load_jsonl(input_path)
    if not prompts:
        raise SystemExit("No prompts loaded.")

    api_key = args.api_key or os.getenv(ENV_KEYS.get(args.provider, ""))
    if not api_key and not args.dry_run:
        raise SystemExit(f"Missing API key. Provide --api-key or set {ENV_KEYS.get(args.provider)}.")

    run_id = args.run_id or f"{args.provider}_{args.model}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    raw_calls_path = output_dir / "raw_calls.jsonl"
    samples_path = output_dir / "sample_level_outputs.jsonl"
    invalid_path = output_dir / "invalid_calls.jsonl"
    csv_path = output_dir / "sample_level_outputs.csv"

    completed_counts = count_completed_samples(samples_path) if args.resume else {}

    total_target = len(prompts) * args.target_samples
    already = sum(min(completed_counts.get(p.get("prompt_id", ""), 0), args.target_samples) for p in prompts)
    remaining = total_target - already
    estimated_calls = sum(
        math.ceil(max(args.target_samples - completed_counts.get(p.get("prompt_id", ""), 0), 0) / args.samples_per_call)
        for p in prompts
    )

    print("========================================")
    print("Token-optimized ablation runner")
    print("========================================")
    print(f"Input prompts      : {len(prompts)}")
    print(f"Provider/model     : {args.provider} / {args.model}")
    print(f"Target samples     : {args.target_samples} per prompt")
    print(f"Samples per call   : {args.samples_per_call}")
    print(f"Target sample rows : {total_target}")
    print(f"Already completed  : {already}")
    print(f"Remaining samples  : {remaining}")
    print(f"Estimated API calls: {estimated_calls}")
    print(f"Output dir         : {output_dir}")
    print("")

    if args.dry_run:
        print("DRY RUN. First 5 prompts:")
        for rec in prompts[:5]:
            print(
                f"  {rec.get('prompt_id')} | {rec.get('ablation_condition')} | "
                f"{rec.get('profile_id')} | {rec.get('task_id')}"
            )
        return

    progress = tqdm(total=remaining, desc="samples", unit="sample")

    for prompt_index, rec in enumerate(prompts, start=1):
        prompt_id = rec.get("prompt_id") or f"prompt_{prompt_index}"
        done = completed_counts.get(prompt_id, 0) if args.resume else 0

        while done < args.target_samples:
            needed = args.target_samples - done
            n_this = min(args.samples_per_call, needed)
            batch_id = str(uuid.uuid4())
            call_id = str(uuid.uuid4())
            required_keys = get_required_keys(rec)
            schema = build_batched_schema(required_keys, n_this)
            system_prompt = rec.get("system", "Return valid JSON only.")
            user_prompt = build_user_prompt(rec, required_keys, n_this)
            p_hash = prompt_hash(rec)

            raw_text = None
            parsed = None
            valid_samples: List[Dict[str, Any]] = []
            errors: List[str] = []
            success = False
            started = time.time()

            for attempt in range(1, args.max_retries + 1):
                try:
                    raw_text = call_model(
                        provider=args.provider,
                        api_key=api_key,
                        base_url=args.base_url,
                        model=args.model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        schema=schema,
                        temperature=args.temperature,
                        max_tokens=args.max_tokens,
                        schema_mode=args.schema_mode,
                        timeout=args.timeout,
                    )
                    parsed = extract_json(raw_text)
                    samples = normalize_samples(parsed)
                    if samples is None:
                        errors = ["No samples array found."]
                    else:
                        valid_samples, errors = validate_samples(samples, required_keys)
                    if len(valid_samples) >= n_this:
                        success = True
                        break
                except Exception as e:
                    errors = [repr(e)]
                    time.sleep(args.retry_sleep)

            elapsed = time.time() - started

            raw_call = {
                "run_id": run_id,
                "call_id": call_id,
                "batch_id": batch_id,
                "timestamp_utc": now_utc(),
                "provider": args.provider,
                "model": args.model,
                "temperature": args.temperature,
                "prompt_index": prompt_index,
                "prompt_hash": p_hash,
                "prompt_id": prompt_id,
                "ablation_condition": rec.get("ablation_condition"),
                "condition_name": rec.get("condition_name"),
                "profile_id": rec.get("profile_id"),
                "task_id": rec.get("task_id"),
                "task_code": rec.get("task_code"),
                "requested_samples": n_this,
                "valid_samples": len(valid_samples),
                "success": success,
                "errors": errors,
                "elapsed_seconds": elapsed,
                "raw_output": raw_text,
                "parsed_output": parsed,
            }
            append_jsonl(raw_call, raw_calls_path)

            if success:
                sample_rows = []
                # Keep exactly n_this samples; if extra valid samples somehow appear, ignore extras.
                for sample_in_call, s in enumerate(valid_samples[:n_this], start=1):
                    repeat_id = done + sample_in_call
                    row = {
                        "run_id": run_id,
                        "call_id": call_id,
                        "batch_id": batch_id,
                        "timestamp_utc": now_utc(),
                        "provider": args.provider,
                        "model": args.model,
                        "temperature": args.temperature,
                        "prompt_index": prompt_index,
                        "prompt_hash": p_hash,
                        "prompt_id": prompt_id,
                        "ablation_condition": rec.get("ablation_condition"),
                        "condition_name": rec.get("condition_name"),
                        "profile_id": rec.get("profile_id"),
                        "task_id": rec.get("task_id"),
                        "task_code": rec.get("task_code"),
                        "repeat_id": repeat_id,
                        "sample_in_call": sample_in_call,
                        "success": True,
                    }
                    for k in required_keys:
                        row[k] = s[k]
                    sample_rows.append(row)

                append_sample_rows(sample_rows, samples_path)
                done += len(sample_rows)
                progress.update(len(sample_rows))
            else:
                invalid_call = dict(raw_call)
                append_jsonl(invalid_call, invalid_path)
                print(f"\nINVALID: {prompt_id}; requested={n_this}; errors={errors}")

            if args.sleep > 0:
                time.sleep(args.sleep)

    progress.close()
    write_csv_from_jsonl(samples_path, csv_path)

    # Summary
    df = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()
    if not df.empty:
        summary = (
            df.groupby(["ablation_condition", "profile_id", "task_id"], dropna=False)
            .size()
            .reset_index(name="n_samples")
        )
        summary.to_csv(output_dir / "completion_summary.csv", index=False, encoding="utf-8-sig")
        print("\nSaved:")
        print(f"  sample JSONL: {samples_path}")
        print(f"  sample CSV  : {csv_path}")
        print(f"  raw calls   : {raw_calls_path}")
        print(f"  summary     : {output_dir / 'completion_summary.csv'}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()

    p.add_argument("--input", required=True, help="Input JSONL prompt file")
    p.add_argument("--provider", required=True, choices=["openai", "anthropic", "qwen", "deepseek", "minimax"])
    p.add_argument("--model", required=True)
    p.add_argument("--api-key", default=None, help="API key. Prefer environment variables.")
    p.add_argument("--base-url", default=None, help="Required for some OpenAI-compatible endpoints")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--run-id", default=None)

    p.add_argument("--target-samples", type=int, default=50, help="Final sample rows per prompt")
    p.add_argument("--samples-per-call", type=int, default=5, help="Number of sample rows requested in one API call")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--schema-mode", choices=["auto", "json_schema", "json_object", "tool", "strict", "none"], default="auto")
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--retry-sleep", type=float, default=1.0)
    p.add_argument("--sleep", type=float, default=0.2)

    p.add_argument("--resume", action="store_true", help="Resume from existing sample_level_outputs.jsonl")
    p.add_argument("--dry-run", action="store_true")

    args = p.parse_args()

    if args.samples_per_call < 1:
        raise SystemExit("--samples-per-call must be >= 1")
    if args.target_samples < 1:
        raise SystemExit("--target-samples must be >= 1")
    if args.samples_per_call > args.target_samples:
        args.samples_per_call = args.target_samples

    return args


if __name__ == "__main__":
    run(parse_args())
