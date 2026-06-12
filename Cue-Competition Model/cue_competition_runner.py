#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cue-Competition Model Runner
============================

Runs DeepSeek, Qwen, and MiniMax cue-competition prompts with batched samples per API call.

Main output:
  sample_level_outputs.csv  # one row per valid sample
  raw_calls.jsonl           # one row per API call
  invalid_calls.jsonl       # invalid or failed calls
  completion_summary.csv

Environment variables:
  DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
  DASHSCOPE_API_KEY or QWEN_API_KEY, QWEN_BASE_URL
  MINIMAX_API_KEY, MINIMAX_BASE_URL

Recommended:
  --target-samples 50 --samples-per-call 5 --resume
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from tqdm import tqdm

REQUEST_TIMEOUT = 180


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(obj: Any, n: int = 16) -> str:
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"Invalid JSONL line {i}: {e}")
    return rows


def append_jsonl(record: Dict[str, Any], path: Path) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_csv_rows(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    df = pd.DataFrame(rows)
    header = not path.exists()
    df.to_csv(path, mode="a", header=header, index=False, encoding="utf-8-sig")


def get_json_keys(prompt: Dict[str, Any]) -> Dict[str, str]:
    user = prompt.get("user")
    if not isinstance(user, dict):
        raise ValueError("prompt['user'] must be an object containing required_output.json_keys")
    keys = user.get("required_output", {}).get("json_keys")
    if not isinstance(keys, dict) or not keys:
        raise ValueError(f"Missing required_output.json_keys for prompt_id={prompt.get('prompt_id')}")
    return keys


def get_api_config(provider: str, api_key: Optional[str], base_url: Optional[str]) -> tuple[str, str]:
    provider = provider.lower()
    if provider == "deepseek":
        key = api_key or os.getenv("DEEPSEEK_API_KEY")
        url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    elif provider == "qwen":
        key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        url = base_url or os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    elif provider == "minimax":
        key = api_key or os.getenv("MINIMAX_API_KEY")
        url = base_url or os.getenv("MINIMAX_BASE_URL")
    elif provider == "openai_compatible":
        key = api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY")
        url = base_url or os.getenv("OPENAI_COMPATIBLE_BASE_URL")
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    if not key:
        raise ValueError(f"Missing API key for provider={provider}. Pass --api-key or set environment variable.")
    if not url:
        raise ValueError(f"Missing base_url for provider={provider}. Pass --base-url or set environment variable.")
    return key, url.rstrip("/")


def user_payload_text(prompt: Dict[str, Any]) -> str:
    """Only send system/user content; do NOT send top-level metadata such as profile_id."""
    user = prompt.get("user", "")
    if isinstance(user, str):
        return user
    return json.dumps(user, ensure_ascii=False, indent=2)


def make_batched_messages(prompt: Dict[str, Any], n_samples: int, batch_id: str) -> tuple[str, str]:
    required = get_json_keys(prompt)
    example = {"sample_id": 1}
    for k in required:
        example[k] = "number"

    system = str(prompt.get("system", "")) + (
        "\n\nYou must return exactly one valid JSON object. No prose, no markdown, no comments. "
        "All task output fields must be numeric."
    )

    wrapper = {
        "batch_id": batch_id,
        "number_of_samples": n_samples,
        "task": "Return multiple independent Monte-Carlo prediction samples for the same prompt condition.",
        "strict_output_format": {"samples": [example]},
        "rules": [
            f"Return exactly {n_samples} samples.",
            "The top-level JSON object must contain exactly one key named samples.",
            "samples must be an array.",
            "Each sample must contain sample_id and every required numeric field.",
            "sample_id must be an integer from 1 to number_of_samples.",
            "All task output fields must be numbers only; do not use strings.",
            "Do not use qualitative words such as low, medium, high, normal, typical, severe, elevated, or moderate as output values.",
            "Do not include explanations or markdown."
        ],
        "original_prediction_prompt": user_payload_text(prompt),
    }
    user = json.dumps(wrapper, ensure_ascii=False, indent=2)
    return system, user


def call_chat_completion(
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    timeout: int,
) -> Dict[str, Any]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def extract_text(response: Dict[str, Any]) -> str:
    return response["choices"][0]["message"]["content"]


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
    if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
        return parsed
    if isinstance(parsed, dict):
        for key in ["samples", "data", "responses"]:
            if isinstance(parsed.get(key), list):
                return parsed[key]
        for wrapper in ["input", "response", "output", "result"]:
            inner = parsed.get(wrapper)
            if isinstance(inner, dict) and isinstance(inner.get("samples"), list):
                return inner["samples"]
    return None


def to_number(x: Any) -> Optional[float]:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if re.fullmatch(r"[-+]?\d+(\.\d+)?([eE][-+]?\d+)?", s):
            return float(s)
    return None


def validate_samples(samples: List[Dict[str, Any]], required: Dict[str, str], expected_n: int) -> tuple[List[Dict[str, float]], List[Dict[str, Any]]]:
    valid: List[Dict[str, float]] = []
    invalid: List[Dict[str, Any]] = []
    if len(samples) != expected_n:
        # Continue validating, but mark at call level later.
        pass
    for i, sample in enumerate(samples, start=1):
        row: Dict[str, float] = {}
        ok = True
        for k in required:
            val = to_number(sample.get(k))
            if val is None:
                ok = False
                break
            row[k] = val
        if ok:
            sid = to_number(sample.get("sample_id"))
            row["sample_id"] = int(sid) if sid is not None else i
            valid.append(row)
        else:
            invalid.append(sample)
    return valid, invalid


def completed_counts(sample_csv: Path) -> Dict[str, int]:
    if not sample_csv.exists():
        return {}
    try:
        df = pd.read_csv(sample_csv)
    except Exception:
        return {}
    if "prompt_id" not in df.columns:
        return {}
    return df.groupby("prompt_id").size().to_dict()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="cue prompt JSONL file")
    ap.add_argument("--provider", required=True, choices=["deepseek", "qwen", "minimax", "openai_compatible"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--target-samples", type=int, default=50)
    ap.add_argument("--samples-per-call", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prompts = load_jsonl(Path(args.input))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    sample_csv = out / "sample_level_outputs.csv"
    raw_path = out / "raw_calls.jsonl"
    invalid_path = out / "invalid_calls.jsonl"

    api_key, base_url = get_api_config(args.provider, args.api_key, args.base_url)
    run_id = f"cue_{args.provider}_{args.model}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"

    done = completed_counts(sample_csv) if args.resume else {}
    plan = []
    for p in prompts:
        pid = p.get("prompt_id")
        n_done = int(done.get(pid, 0))
        remaining = max(0, args.target_samples - n_done)
        if remaining > 0:
            plan.append((p, n_done, remaining))

    print(f"Loaded prompts: {len(prompts)}")
    print(f"Need prompts: {len(plan)}")
    print(f"Target samples per prompt: {args.target_samples}")
    print(f"Provider/model: {args.provider}/{args.model}")
    print(f"Base URL: {base_url}")

    if args.dry_run:
        total_samples = sum(x[2] for x in plan)
        approx_calls = sum((x[2] + args.samples_per_call - 1)//args.samples_per_call for x in plan)
        print(f"Planned new samples: {total_samples}")
        print(f"Planned API calls: {approx_calls}")
        for p, n_done, rem in plan[:10]:
            print(p.get("prompt_id"), "done=", n_done, "remaining=", rem)
        return

    call_counter = 0
    for prompt, n_done, remaining in tqdm(plan, desc="prompts"):
        required = get_json_keys(prompt)
        pid = prompt["prompt_id"]
        produced = n_done
        while produced < args.target_samples:
            n_this = min(args.samples_per_call, args.target_samples - produced)
            call_counter += 1
            call_id = str(uuid.uuid4())
            batch_id = f"{pid}__batch_{call_counter:06d}"
            system, user = make_batched_messages(prompt, n_this, batch_id)
            prompt_hash = stable_hash({"system": system, "user": user})

            call_record = {
                "run_id": run_id,
                "call_id": call_id,
                "batch_id": batch_id,
                "timestamp_utc": now(),
                "provider": args.provider,
                "model": args.model,
                "temperature": args.temperature,
                "prompt_id": pid,
                "condition_id": prompt.get("condition_id"),
                "ablation_condition": prompt.get("ablation_condition"),
                "condition_name": prompt.get("condition_name"),
                "label_cue": prompt.get("label_cue"),
                "score_cue": prompt.get("score_cue"),
                "symptom_cue": prompt.get("symptom_cue"),
                "profile_id": prompt.get("profile_id"),
                "task_id": prompt.get("task_id"),
                "task_code": prompt.get("task_code"),
                "requested_samples": n_this,
                "prompt_hash": prompt_hash,
            }

            raw_text = None
            last_error = None
            for attempt in range(1, args.max_retries + 1):
                try:
                    response = call_chat_completion(
                        provider=args.provider,
                        api_key=api_key,
                        base_url=base_url,
                        model=args.model,
                        system=system,
                        user=user,
                        temperature=args.temperature,
                        timeout=args.timeout,
                    )
                    raw_text = extract_text(response)
                    parsed = extract_json(raw_text)
                    samples = normalize_samples(parsed)
                    if samples is None:
                        raise ValueError("Could not find samples array in model output")
                    valid, invalid = validate_samples(samples, required, n_this)
                    if len(valid) == n_this:
                        rows = []
                        for j, sample in enumerate(valid, start=1):
                            produced += 1
                            row = dict(call_record)
                            row.update({
                                "repeat_id": produced,
                                "sample_in_call": j,
                                "success": True,
                            })
                            row.update({k: v for k, v in sample.items() if k != "sample_id"})
                            rows.append(row)
                        append_csv_rows(rows, sample_csv)
                        append_jsonl({**call_record, "success": True, "raw_output": raw_text}, raw_path)
                        break
                    else:
                        raise ValueError(f"Valid samples {len(valid)}/{n_this}; invalid={invalid[:2]}")
                except Exception as e:
                    last_error = repr(e)
                    time.sleep(min(2 * attempt, 10))
            else:
                rec = {**call_record, "success": False, "error": last_error, "raw_output": raw_text}
                append_jsonl(rec, invalid_path)
                print(f"[WARN] failed prompt={pid} n={n_this}: {last_error}")
                # Avoid infinite loop; skip this call. User can resume later.
                break
            time.sleep(args.sleep)

    if sample_csv.exists():
        df = pd.read_csv(sample_csv)
        summary = df.groupby(["condition_id", "profile_id", "task_id"]).size().reset_index(name="n")
        summary.to_csv(out / "completion_summary.csv", index=False, encoding="utf-8-sig")
        print("Saved:", sample_csv)
        print("Saved:", out / "completion_summary.csv")
    print("Done.")


if __name__ == "__main__":
    main()
