# DeepSeek strict-range rerun package for problematic digital-use experiments

This package fixes the DeepSeek range-validity problem observed in the problematic digital-use / internet-addiction extension.

## What was changed

The prompt files now include explicit hard numeric range constraints:

- Accuracy and all proportions: **0–1**
- BART `adjusted_average_pumps`: **0–64**
- BART `risk_preference_0_1`: **0–1**
- BART `explosion_count`: integer **0–30**
- Questionnaire totals:
  - `caars_total`: **0–78**
  - `cias_total`: **26–104**
  - `young_total`: **0–8**
  - `dsm_total1`: **0–9**
  - `dsm_total2`: **0–13**

The runner also validates every returned sample locally. Invalid out-of-range samples are logged to `invalid_samples.jsonl` and are not included in `sample_level_outputs.csv`.

## Recommended rerun targets

Because the earlier DeepSeek output had the biggest problems in n-back, BART, and questionnaire, start with the problem-task files:

- `ia_main_profile_prompts_strict_problem_tasks.jsonl`
- `ia_ablation_5conditions_strict_problem_tasks.jsonl`
- `ia_cue_competition_8conditions_full5tasks_strict_problem_tasks.jsonl`
- `ia_individual_questionnaire_only_strict_problem_tasks.jsonl`
- `ia_individual_questionnaire_plus_ia_label_strict_problem_tasks.jsonl`

If you want the full rerun, use the `*_strict_ranges.jsonl` files.

## Run examples

### Main profile experiment, problem tasks only

```bash
export DEEPSEEK_API_KEY="your_key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"

python deepseek_ia_strict_runner.py \
  --input ia_main_profile_prompts_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_main_strict_problem_tasks \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

### Ablation experiment, problem tasks only

```bash
python deepseek_ia_strict_runner.py \
  --input ia_ablation_5conditions_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_ablation_strict_problem_tasks \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

### Cue-Competition experiment, problem tasks only

```bash
python deepseek_ia_strict_runner.py \
  --input ia_cue_competition_8conditions_full5tasks_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_cue_strict_problem_tasks \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

### Individual prediction, questionnaire-only, problem tasks only

```bash
python deepseek_ia_strict_runner.py \
  --input ia_individual_questionnaire_only_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_individual_qonly_strict_problem_tasks \
  --model deepseek-chat \
  --target-samples 5 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

### Individual prediction + IA label, problem tasks only

```bash
python deepseek_ia_strict_runner.py \
  --input ia_individual_questionnaire_plus_ia_label_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_individual_plus_label_strict_problem_tasks \
  --model deepseek-chat \
  --target-samples 5 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

## Custom gateway

If you use an OpenAI-compatible gateway, pass `--base-url` explicitly:

```bash
python deepseek_ia_strict_runner.py \
  --input ia_main_profile_prompts_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_gateway \
  --model deepseek-v4pro \
  --api-key "your_gateway_key" \
  --base-url "https://your-gateway/v1" \
  --target-samples 50 \
  --samples-per-call 5 \
  --resume
```

## Validate after running

```bash
python validate_strict_ia_outputs.py \
  --input outputs_deepseek_ia_main_strict_problem_tasks/sample_level_outputs.csv \
  --output-dir outputs_deepseek_ia_main_strict_problem_tasks/validation
```

## Notes

- The script sends only the `system` and `user` prompt to the model; metadata fields such as `profile_id` are not sent unless already written inside the user prompt.
- Invalid samples are not clamped. They are rejected and logged.
- For formal analysis, use only `sample_level_outputs.csv`.
