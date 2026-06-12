#!/usr/bin/env python3
"""
Resume LLM simulation runner – continues only missing (profile_id, task_id) samples.

Usage:
    export OPENAI_API_KEY="..."
    export OPENAI_BASE_URL="..."   # optional
    python resume_runner.py --target-valid 20 --temperature 0.8
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
# Configuration (大部分与原脚本相同)
# -----------------------------------------------------------------------------
DEFAULT_INPUT_JSONL = Path(os.getenv("INPUT_JSONL", "llm_prompt_templates.jsonl"))
DEFAULT_OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "formal_outputs_openai"))

# 这些值可以从环境变量读取，也可以保持原样（注意原脚本中 API_KEY 是硬编码的）
API_KEY = "sk-VM9Up21KTOEnS5OWuZXYnUUGeOTYPyQHQ0raKtkRxR7VteGP"
BASE_URL = "https://newapi.boundlessai.tech/v1"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "90.0"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
SLEEP_SECONDS = float(os.getenv("LLM_SLEEP_SECONDS", "0.2"))

# 续跑专用默认值
DEFAULT_TARGET_VALID = 20
DEFAULT_TEMPERATURE = 0.8

# 运行 ID：续跑时生成新的 ID，但追加到已有文件
RUN_ID = os.getenv("RUN_ID") or datetime.now(timezone.utc).strftime("resume_%Y%m%dT%H%M%SZ")


# -----------------------------------------------------------------------------
# Task schemas (与原脚本完全相同)
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
# IO helpers (与原脚本相同)
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
# Schema / validation helpers (与原脚本相同)
# -----------------------------------------------------------------------------
def function_for_task(task_id: str) -> Dict[str, Any]:
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
    choice = response.choices[0]
    message = choice.message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "record_simulation":
                args = json.loads(tool_call.function.arguments)
                return args
    return None


def response_text_fallback(response: Any) -> str:
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
# OpenAI call (与原脚本相同，但接受 temperature 参数)
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
    temperature: float,
) -> Dict[str, Any]:
    messages, system_prompt = convert_to_openai_format(record, task_id)

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
        "temperature": temperature,
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
            temperature=temperature,
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
# Output helpers
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


def write_resume_manifest(output_dir: Path, target_valid: int, temperature: float) -> None:
    manifest = {
        "run_id": RUN_ID,
        "type": "resume",
        "model": MODEL,
        "temperature": temperature,
        "target_valid_samples_per_cell": target_valid,
        "sleep_seconds": SLEEP_SECONDS,
        "request_timeout": REQUEST_TIMEOUT,
        "max_tokens": MAX_TOKENS,
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / f"resume_manifest_{RUN_ID}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def update_summary_and_counts(output_dir: Path, valid_rows: List[Dict[str, Any]], invalid_rows: List[Dict[str, Any]]) -> None:
    """追加新数据到已有的CSV文件，并重新生成汇总统计"""
    parsed_csv = output_dir / "formal_parsed_outputs.csv"
    invalid_csv = output_dir / "formal_invalid_outputs.csv"

    # 追加 valid 行
    if valid_rows:
        new_df = pd.DataFrame(valid_rows)
        if parsed_csv.exists():
            existing_df = pd.read_csv(parsed_csv)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        combined_df.to_csv(parsed_csv, index=False)

    # 追加 invalid 行
    if invalid_rows:
        new_invalid_df = pd.DataFrame(invalid_rows)
        if invalid_csv.exists():
            existing_invalid = pd.read_csv(invalid_csv)
            combined_invalid = pd.concat([existing_invalid, new_invalid_df], ignore_index=True)
        else:
            combined_invalid = new_invalid_df
        combined_invalid.to_csv(invalid_csv, index=False)

    # 重新生成汇总统计（基于完整 valid 数据）
    if parsed_csv.exists():
        full_valid = pd.read_csv(parsed_csv)
        if not full_valid.empty:
            group_cols = ["model", "profile_id", "task_id"]
            numeric_cols = [
                c for c in full_valid.columns
                if c not in {"repeat_id", "temperature"}
                and pd.api.types.is_numeric_dtype(full_valid[c])
            ]
            if numeric_cols:
                summary = full_valid.groupby(group_cols, dropna=False)[numeric_cols].agg(["count", "mean", "std", "min", "max"])
                summary.to_csv(output_dir / "formal_summary_by_profile_task.csv")

            counts = full_valid.groupby(["profile_id", "task_id"], dropna=False).size().reset_index(name="n_valid")
            counts.to_csv(output_dir / "formal_valid_counts.csv", index=False)

    qc = {
        "n_valid_total": int(len(valid_rows)) + (0 if not parsed_csv.exists() else len(pd.read_csv(parsed_csv))),
        "n_invalid_total": int(len(invalid_rows)) + (0 if not invalid_csv.exists() else len(pd.read_csv(invalid_csv))),
    }
    (output_dir / "qc_summary.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# 续跑核心逻辑
# -----------------------------------------------------------------------------
def load_existing_valid_counts(parsed_csv: Path) -> Dict[Tuple[str, str], int]:
    """从已有的 formal_parsed_outputs.csv 读取每个 (profile_id, task_id) 的有效样本数"""
    if not parsed_csv.exists():
        return {}
    df = pd.read_csv(parsed_csv)
    if df.empty:
        return {}
    # 确保列存在
    if "profile_id" not in df or "task_id" not in df:
        return {}
    counts = df.groupby(["profile_id", "task_id"]).size().to_dict()
    # 转换 key 为元组
    return {k: v for k, v in counts.items()}


def get_next_global_repeat_id(raw_log_path: Path) -> int:
    """从已有的 raw_outputs.jsonl 中找到最大的 repeat_id，返回 next = max+1"""
    if not raw_log_path.exists():
        return 1
    max_id = 0
    with raw_log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                rid = rec.get("repeat_id")
                if isinstance(rid, int) and rid > max_id:
                    max_id = rid
            except json.JSONDecodeError:
                continue
    return max_id + 1


def main():
    parser = argparse.ArgumentParser(description="Resume OpenAI simulation to reach target valid samples per cell.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_JSONL, help="Prompt JSONL file.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument("--target-valid", type=int, default=DEFAULT_TARGET_VALID, help="Target valid samples per (profile_id, task_id).")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="Temperature for generation.")
    parser.add_argument("--dry-run", action="store_true", help="Only show missing counts, do not call API.")
    args = parser.parse_args()

    input_path: Path = args.input
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"Missing input file: {input_path}")

    # 加载所有 prompts
    prompts = load_prompts(input_path)
    if not prompts:
        raise SystemExit(f"No prompt records found in {input_path}")

    # 标准化每个 prompt 的 profile_id 和 task_id
    normalized: List[Tuple[Dict[str, Any], str, str]] = []
    for rec in prompts:
        task_id = normalize_task_id(rec.get("task_id", rec.get("task")), rec)
        profile_id = normalize_profile_id(rec.get("profile_id", rec.get("profile")), rec)
        normalized.append((rec, profile_id, task_id))

    # 读取已有有效计数
    parsed_csv = output_dir / "formal_parsed_outputs.csv"
    existing_counts = load_existing_valid_counts(parsed_csv)

    # 确定需要补充的组合
    required: List[Tuple[Dict[str, Any], str, str, int]] = []  # (record, profile_id, task_id, needed)
    for record, profile_id, task_id in normalized:
        key = (profile_id, task_id)
        current = existing_counts.get(key, 0)
        needed = args.target_valid - current
        if needed > 0:
            required.append((record, profile_id, task_id, needed))

    if not required:
        print(f"所有组合均已达到目标 {args.target_valid} 个有效样本，无需续跑。")
        return

    print(f"续跑配置:")
    print(f"  目标有效样本数: {args.target_valid}")
    print(f"  temperature: {args.temperature}")
    print(f"  需要补充的组合数: {len(required)}")
    for rec, pid, tid, need in required:
        print(f"    {pid} / {tid}: 已有 {existing_counts.get((pid, tid), 0)} / {args.target_valid}, 需要 {need}")

    if args.dry_run:
        return

    # 准备输出文件路径
    raw_path = output_dir / "formal_raw_outputs.jsonl"
    next_repeat_id = get_next_global_repeat_id(raw_path)
    print(f"将从 repeat_id = {next_repeat_id} 开始生成新样本")

    client = make_client()

    valid_rows: List[Dict[str, Any]] = []
    invalid_rows: List[Dict[str, Any]] = []

    # 对每个需要补充的组合，循环调用直到满足需要数量
    for record, profile_id, task_id, needed in required:
        print(f"\n开始补充: {profile_id} / {task_id} (需要 {needed} 个有效样本)")
        successes = 0
        attempts = 0
        while successes < needed:
            rid = next_repeat_id
            next_repeat_id += 1
            attempts += 1
            print(f"  [attempt {attempts}] repeat_id={rid} ...", end=" ", flush=True)
            result = run_one(
                client,
                record,
                repeat_id=rid,
                profile_id=profile_id,
                task_id=task_id,
                run_id=RUN_ID,
                temperature=args.temperature,
            )
            append_jsonl(raw_path, result)

            if result.get("ok") and result.get("parse_success") and result.get("validation_success"):
                valid_rows.append(flatten_valid_record(result))
                successes += 1
                print(f"SUCCESS (now {successes}/{needed})")
            else:
                invalid_rows.append(result)
                error_msg = result.get("error", "validation failed")
                print(f"FAILED: {error_msg}")

            time.sleep(SLEEP_SECONDS)

        print(f"  完成 {profile_id}/{task_id}: 获得 {successes} 个有效样本 (尝试 {attempts} 次)")

    # 更新输出文件
    print("\n更新输出文件...")
    update_summary_and_counts(output_dir, valid_rows, invalid_rows)
    write_resume_manifest(output_dir, args.target_valid, args.temperature)

    print(f"\n续跑完成。新增有效样本: {len(valid_rows)}，无效/错误: {len(invalid_rows)}")
    print(f"原始日志: {raw_path}")
    print(f"更新后的 parsed CSV: {output_dir / 'formal_parsed_outputs.csv'}")


if __name__ == "__main__":
    # 注意：原脚本中使用了 re，这里需要导入
    import re
    main()