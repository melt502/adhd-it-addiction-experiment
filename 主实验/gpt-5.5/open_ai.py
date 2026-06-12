"""
Formal LLM simulation runner - OpenAI API version

Key fixes relative to the pilot script:
1. REPEATS defaults to 50.
2. Uses OpenAI function calling with JSON schema to force structured output.
3. All task measurement fields are numeric: integer or number only.
4. Each saved record keeps run_id, model, profile_id, task_id, repeat_id.
5. Separates raw logs, valid parsed outputs, invalid outputs, and summary files.
6. Does NOT hard-code API keys. Set OPENAI_API_KEY in the environment.

Required input:
    llm_prompt_templates.jsonl
Each JSONL record should preferably contain:
    profile_id, task_id, and either messages or system/user/prompt.
If profile_id/task_id are missing, the script tries to infer them from common keys
or from the prompt text, but explicit IDs are strongly recommended.

Run example:
    export OPENAI_API_KEY="..."
    export OPENAI_BASE_URL="https://api.openai.com/v1"   # optional custom endpoint
    export OPENAI_MODEL="gpt-4o"
    python script.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    from openai import OpenAI
except ImportError as exc:
    raise SystemExit("请先安装 openai 包: pip install openai") from exc

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:
    raise SystemExit("请先安装 jsonschema 包: pip install jsonschema") from exc


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DEFAULT_INPUT_JSONL = Path(os.getenv("INPUT_JSONL", "llm_prompt_templates.jsonl"))
DEFAULT_OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "formal_outputs_openai"))

API_KEY = "sk-RYYlmrGCaZUe1ycWj9t1UrZ6BhPCGRZeJwe4uacCYRsiPJk8"
# optional, e.g., "https://api.openai.com/v1"
BASE_URL = "https://newapi.boundlessai.tech/v1"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
REPEATS = int(os.getenv("LLM_REPEATS", "50"))
SLEEP_SECONDS = float(os.getenv("LLM_SLEEP_SECONDS", "0.2"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "90.0"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))

# For reproducible and auditable runs.
RUN_ID = os.getenv("RUN_ID") or datetime.now(timezone.utc).strftime("openai_%Y%m%dT%H%M%SZ")


# -----------------------------------------------------------------------------
# Task schemas (unchanged)
# -----------------------------------------------------------------------------
COMMON_NUMERIC_FIELD_RULE = {
    "type": "number",
    "description": "Numeric value only. Do not use words such as low, medium, high, moderate, NA, or unknown.",
}

TASK_OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "stroop": {
        "type": "object",
        "additionalProperties": False,
        "required": ["accuracy", "mean_rt_ms", "rt_sd_ms", "interference_effect_ms"],
        "properties": {
            "accuracy": {"type": "number", "minimum": 0, "maximum": 1},
            "mean_rt_ms": {"type": "number", "minimum": 100, "maximum": 3000},
            "rt_sd_ms": {"type": "number", "minimum": 0, "maximum": 2000},
            "interference_effect_ms": {"type": "number", "minimum": -1000, "maximum": 2000},
        },
    },
    "nback": {
        "type": "object",
        "additionalProperties": False,
        "required": ["overall_accuracy", "accuracy_1back", "accuracy_2back", "accuracy_3back", "mean_rt_ms"],
        "properties": {
            "overall_accuracy": {"type": "number", "minimum": 0, "maximum": 1},
            "accuracy_1back": {"type": "number", "minimum": 0, "maximum": 1},
            "accuracy_2back": {"type": "number", "minimum": 0, "maximum": 1},
            "accuracy_3back": {"type": "number", "minimum": 0, "maximum": 1},
            "mean_rt_ms": {"type": "number", "minimum": 100, "maximum": 5000},
        },
    },
    "bart": {
        "type": "object",
        "additionalProperties": False,
        "required": ["adjusted_average_pumps", "total_earnings", "explosion_count", "risk_preference_0_1"],
        "properties": {
            "adjusted_average_pumps": {"type": "number", "minimum": 0, "maximum": 64},
            "total_earnings": {"type": "number", "minimum": 0, "maximum": 1000},
            "explosion_count": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_preference_0_1": {"type": "number", "minimum": 0, "maximum": 1},
        },
    },
    "ddt": {
        "type": "object",
        "additionalProperties": False,
        "required": ["discounting_k", "log_discounting_k", "immediate_choice_proportion"],
        "properties": {
            "discounting_k": {"type": "number", "minimum": 0, "maximum": 10},
            "log_discounting_k": {"type": "number", "minimum": -20, "maximum": 5},
            "immediate_choice_proportion": {"type": "number", "minimum": 0, "maximum": 1},
        },
    },
    "questionnaire": {
        "type": "object",
        "additionalProperties": False,
        "required": ["caars_total", "cias_total", "young_total", "dsm_total1", "dsm_total2"],
        "properties": {
            "caars_total": {"type": "number", "minimum": 0, "maximum": 78},
            "cias_total": {"type": "number", "minimum": 26, "maximum": 104},
            "young_total": {"type": "number", "minimum": 0, "maximum": 8},
            "dsm_total1": {"type": "number", "minimum": 0, "maximum": 9},
            "dsm_total2": {"type": "number", "minimum": 0, "maximum": 13},
        },
    },
}

TASK_ALIASES = {
    "stroop": "stroop",
    "color_word": "stroop",
    "color-word": "stroop",
    "n-back": "nback",
    "n_back": "nback",
    "nback": "nback",
    "bart": "bart",
    "risk": "bart",
    "balloon": "bart",
    "ddt": "ddt",
    "delay": "ddt",
    "delayed_discounting": "ddt",
    "delay_discounting": "ddt",
    "questionnaire": "questionnaire",
    "survey": "questionnaire",
    "scale": "questionnaire",
    "questionnaires": "questionnaire",
}

PROFILE_ALIASES = {
    "p1": "P1_low_ADHD_low_IA",
    "p2": "P2_inattentive_ADHD",
    "p3": "P3_combined_ADHD",
    "p4": "P4_ADHD_high_IA",
    "p5": "P5_high_IA_low_ADHD",
}


# -----------------------------------------------------------------------------
# IO helpers (unchanged)
# -----------------------------------------------------------------------------
def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_short(obj: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:length]


def deep_get(d: Any, path: List[str], default=None):
    for key in path:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return default
    return d


def load_prompts(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {lineno}: {exc}") from exc
            record.setdefault("prompt_index", len(records) + 1)
            records.append(record)

    for rec in records:
        if "profile_id" not in rec:
            pid = deep_get(rec, ["user", "participant_profile", "profile_id"])
            if pid is not None:
                rec["profile_id"] = pid
        if "task_id" not in rec:
            tid = deep_get(rec, ["user", "task", "task_id"])
            if tid is not None:
                rec["task_id"] = tid

    return records


def text_from_record(record: Dict[str, Any]) -> str:
    chunks: List[str] = []
    if "messages" in record:
        for msg in record.get("messages", []):
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            chunks.append(content)
    for key in ["system", "user", "prompt", "profile", "task", "profile_id", "task_id"]:
        if key in record:
            val = record[key]
            chunks.append(val if isinstance(val, str) else json.dumps(val, ensure_ascii=False))
    return "\n".join(chunks).lower()


def normalize_task_id(raw: Any, record: Dict[str, Any]) -> str:
    if raw is not None:
        candidate = str(raw).strip().lower().replace(" ", "_")
        if candidate in TASK_ALIASES:
            return TASK_ALIASES[candidate]
        for key, val in TASK_ALIASES.items():
            if key in candidate:
                return val

    text = text_from_record(record)
    for key, val in TASK_ALIASES.items():
        if key in text:
            return val

    raise ValueError(
        f"Cannot infer task_id for prompt_index={record.get('prompt_index')}. "
        f"Supported tasks: {sorted(TASK_OUTPUT_SCHEMAS)}"
    )


def normalize_profile_id(raw: Any, record: Dict[str, Any]) -> str:
    if raw is not None:
        s = str(raw).strip()
        low = s.lower().replace(" ", "_")
        if low in PROFILE_ALIASES:
            return PROFILE_ALIASES[low]
        return s

    text = text_from_record(record)
    for key, val in PROFILE_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", text, re.IGNORECASE):
            return val

    return f"profile_unknown_prompt_{record.get('prompt_index')}"


def convert_to_openai_format(record: Dict[str, Any], task_id: str) -> Tuple[List[Dict[str, str]], str]:
    """
    Convert prompt record to OpenAI chat messages.
    Returns (messages, system_prompt) where system_prompt is extracted if present.
    """
    messages: List[Dict[str, str]] = []
    system_prompt = ""

    if "messages" in record:
        for msg in record.get("messages", []):
            role = msg.get("role")
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            if role == "system":
                system_prompt = content
            elif role in {"user", "assistant"}:
                messages.append({"role": role, "content": content})
    else:
        raw_system = record.get("system")
        if raw_system is not None:
            system_prompt = raw_system if isinstance(raw_system, str) else json.dumps(raw_system, ensure_ascii=False)
        user = record.get("user", record.get("prompt", ""))
        if not isinstance(user, str):
            user = json.dumps(user, ensure_ascii=False)
        messages.append({"role": "user", "content": user})

    schema_instruction = (
        "\n\nIMPORTANT OUTPUT RULES:\n"
        "You must call the function `record_simulation` exactly once. "
        "Do not write prose outside the function call. "
        "All measurement fields must be numeric JSON values, not strings. "
        "Never use words such as low, medium, high, moderate, NA, or unknown in numeric fields. "
        f"The task schema is for task_id={task_id}."
    )
    if messages:
        messages[-1]["content"] += schema_instruction
    else:
        messages = [{"role": "user", "content": schema_instruction}]

    return messages, system_prompt


# -----------------------------------------------------------------------------
# Schema / validation helpers
# -----------------------------------------------------------------------------
def function_for_task(task_id: str) -> Dict[str, Any]:
    """Return OpenAI function definition for the task."""
    return {
        "type": "function",
        "function": {
            "name": "record_simulation",
            "description": (
                "Return the simulated participant's task outcome. "
                "Every measurement field must be a numeric JSON value."
            ),
            "parameters": TASK_OUTPUT_SCHEMAS[task_id],
        },
    }


def validator_for_task(task_id: str) -> Draft202012Validator:
    return Draft202012Validator(TASK_OUTPUT_SCHEMAS[task_id])


def extract_function_call(response: Any) -> Optional[Dict[str, Any]]:
    """Extract OpenAI function call arguments."""
    choice = response.choices[0]
    message = choice.message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "record_simulation":
                args = json.loads(tool_call.function.arguments)
                return args
    return None


def response_text_fallback(response: Any) -> str:
    """Extract text content from response."""
    choice = response.choices[0]
    message = choice.message
    if message.content:
        return message.content.strip()
    return ""


def validate_parsed(parsed: Dict[str, Any], task_id: str) -> Tuple[bool, List[str]]:
    errors = sorted(validator_for_task(task_id).iter_errors(parsed), key=lambda e: list(e.path))
    messages = []
    for err in errors:
        path = ".".join(str(p) for p in err.path) or "<root>"
        messages.append(f"{path}: {err.message}")
    return len(messages) == 0, messages


# -----------------------------------------------------------------------------
# OpenAI call
# -----------------------------------------------------------------------------
def make_client() -> OpenAI:
    if not API_KEY:
        raise SystemExit(
            "Missing API key. Please set OPENAI_API_KEY in the environment. "
            "Do not hard-code API keys in the script."
        )
    kwargs: Dict[str, Any] = {"api_key": API_KEY, "timeout": REQUEST_TIMEOUT}
    if BASE_URL:
        kwargs["base_url"] = BASE_URL
    return OpenAI(**kwargs)


def run_one(
    client: OpenAI,
    record: Dict[str, Any],
    *,
    repeat_id: int,
    profile_id: str,
    task_id: str,
    run_id: str,
) -> Dict[str, Any]:
    messages, system_prompt = convert_to_openai_format(record, task_id)

    # Insert system prompt as first message if present
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    started = time.time()
    prompt_hash = sha256_short(record)
    call_id = str(uuid.uuid4())

    base_meta = {
        "run_id": run_id,
        "call_id": call_id,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "profile_id": profile_id,
        "task_id": task_id,
        "repeat_id": repeat_id,
        "prompt_index": record.get("prompt_index"),
        "prompt_hash": prompt_hash,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=full_messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            tools=[function_for_task(task_id)],
            tool_choice={"type": "function", "function": {"name": "record_simulation"}},
            timeout=REQUEST_TIMEOUT,
        )

        parsed = extract_function_call(response)
        raw_text = response_text_fallback(response)
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else None,
            "output_tokens": response.usage.completion_tokens if response.usage else None,
        }

        if parsed is None:
            return {
                **base_meta,
                "ok": False,
                "parse_success": False,
                "validation_success": False,
                "error": "No record_simulation function call found in OpenAI response.",
                "response_text": raw_text,
                "usage": usage,
                "elapsed_seconds": time.time() - started,
            }

        is_valid, validation_errors = validate_parsed(parsed, task_id)
        return {
            **base_meta,
            "ok": True,
            "parse_success": True,
            "validation_success": is_valid,
            "parsed_output": parsed,
            "validation_errors": validation_errors,
            "response_text": raw_text,
            "usage": usage,
            "elapsed_seconds": time.time() - started,
        }
    except Exception as exc:
        return {
            **base_meta,
            "ok": False,
            "parse_success": False,
            "validation_success": False,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": time.time() - started,
        }


# -----------------------------------------------------------------------------
# Output helpers (unchanged)
# -----------------------------------------------------------------------------
def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def flatten_valid_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    parsed = rec.get("parsed_output", {}) or {}
    usage = rec.get("usage", {}) or {}
    base = {
        "run_id": rec.get("run_id"),
        "call_id": rec.get("call_id"),
        "model": rec.get("model"),
        "temperature": rec.get("temperature"),
        "profile_id": rec.get("profile_id"),
        "task_id": rec.get("task_id"),
        "repeat_id": rec.get("repeat_id"),
        "prompt_index": rec.get("prompt_index"),
        "prompt_hash": rec.get("prompt_hash"),
        "timestamp_utc": rec.get("timestamp_utc"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "elapsed_seconds": rec.get("elapsed_seconds"),
    }
    return {**base, **parsed}


def write_run_manifest(output_dir: Path, input_path: Path, prompt_count: int) -> None:
    manifest = {
        "run_id": RUN_ID,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "repeats": REPEATS,
        "sleep_seconds": SLEEP_SECONDS,
        "request_timeout": REQUEST_TIMEOUT,
        "max_tokens": MAX_TOKENS,
        "input_jsonl": str(input_path),
        "prompt_count": prompt_count,
        "output_dir": str(output_dir),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "schema_tasks": sorted(TASK_OUTPUT_SCHEMAS),
        "api_base_url_set": bool(BASE_URL),
        "api_key_source": "environment",
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_outputs(output_dir: Path, valid_rows: List[Dict[str, Any]], invalid_rows: List[Dict[str, Any]]) -> None:
    valid_df = pd.DataFrame(valid_rows)
    invalid_df = pd.DataFrame(invalid_rows)

    valid_df.to_csv(output_dir / "formal_parsed_outputs.csv", index=False)
    invalid_df.to_csv(output_dir / "formal_invalid_outputs.csv", index=False)

    if not valid_df.empty:
        group_cols = ["model", "profile_id", "task_id"]
        numeric_cols = [
            c for c in valid_df.columns
            if c not in {"repeat_id", "temperature"}
            and pd.api.types.is_numeric_dtype(valid_df[c])
        ]
        if numeric_cols:
            summary = valid_df.groupby(group_cols, dropna=False)[numeric_cols].agg(["count", "mean", "std", "min", "max"])
            summary.to_csv(output_dir / "formal_summary_by_profile_task.csv")

        counts = valid_df.groupby(["profile_id", "task_id"], dropna=False).size().reset_index(name="n_valid")
        counts.to_csv(output_dir / "formal_valid_counts.csv", index=False)

    qc = {
        "n_valid": int(len(valid_df)),
        "n_invalid": int(len(invalid_df)),
        "expected_valid": None,
    }
    (output_dir / "qc_summary.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Formal OpenAI LLM simulation runner with JSON schema enforcement.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_JSONL, help="Prompt JSONL file.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument("--dry-run", action="store_true", help="Validate prompt metadata and schemas without calling OpenAI.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path: Path = args.input
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"Missing input file: {input_path}")

    prompts = load_prompts(input_path)
    if not prompts:
        raise SystemExit(f"No prompt records found in {input_path}")

    normalized: List[Tuple[Dict[str, Any], str, str]] = []
    for rec in prompts:
        task_id = normalize_task_id(rec.get("task_id", rec.get("task")), rec)
        profile_id = normalize_profile_id(rec.get("profile_id", rec.get("profile")), rec)
        normalized.append((rec, profile_id, task_id))

    write_run_manifest(output_dir, input_path, len(prompts))

    print(f"Run ID: {RUN_ID}")
    print(f"Loaded {len(prompts)} prompt records from {input_path}.")
    print(f"Using model: {MODEL}")
    print(f"Repeats: {REPEATS}; expected calls: {REPEATS * len(prompts)}")
    print(f"Output directory: {output_dir}")

    if args.dry_run:
        rows = [
            {"prompt_index": rec.get("prompt_index"), "profile_id": profile_id, "task_id": task_id}
            for rec, profile_id, task_id in normalized
        ]
        pd.DataFrame(rows).to_csv(output_dir / "dry_run_prompt_metadata.csv", index=False)
        print("Dry run complete. Prompt metadata saved.")
        return

    client = make_client()
    raw_path = output_dir / "formal_raw_outputs.jsonl"

    valid_rows: List[Dict[str, Any]] = []
    invalid_rows: List[Dict[str, Any]] = []

    for repeat_id in range(1, REPEATS + 1):
        print(f"=== Repeat {repeat_id}/{REPEATS} ===")
        for j, (record, profile_id, task_id) in enumerate(normalized, start=1):
            rec = run_one(
                client,
                record,
                repeat_id=repeat_id,
                profile_id=profile_id,
                task_id=task_id,
                run_id=RUN_ID,
            )
            append_jsonl(raw_path, rec)

            if rec.get("ok") and rec.get("parse_success") and rec.get("validation_success"):
                valid_rows.append(flatten_valid_record(rec))
                status = "OK"
            else:
                invalid_rows.append(rec)
                status = "INVALID" if rec.get("ok") else "ERR"
            print(f"  Prompt {j}/{len(normalized)} | {profile_id} | {task_id}: {status}")
            time.sleep(SLEEP_SECONDS)

    summarize_outputs(output_dir, valid_rows, invalid_rows)
    print(f"\nFinished. Valid: {len(valid_rows)}, Invalid/Error: {len(invalid_rows)}")
    print(f"Raw log: {raw_path}")
    print(f"Parsed CSV: {output_dir / 'formal_parsed_outputs.csv'}")


if __name__ == "__main__":
    main()