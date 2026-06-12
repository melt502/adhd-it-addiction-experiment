# Internet-addiction / problematic digital-use LLM experiment package

This package mirrors the ADHD LLM-simulation project but targets problematic digital-use / internet-addiction-like profiles.

## Four experiments

1. **Main profile simulation**
   - Prompt file: `ia_main_profile_prompts.jsonl`
   - 5 profiles × 5 tasks = 25 prompts.

2. **Prompt ablation**
   - Prompt file: `ia_ablation_5conditions.jsonl`
   - Conditions: label-only, score-only, symptom-only, full-profile, conflict.
   - 5 conditions × 5 profiles × 5 tasks = 125 prompts.

3. **Individual prediction**
   - Prompt files: `ia_individual_questionnaire_only.jsonl`, `ia_individual_questionnaire_plus_ia_label.jsonl`
   - Generated from `individual_prediction_input.csv` using age, sex, CAARS, CIAS, Young, DSM totals.
   - `questionnaire_only` uses anonymized Scale A–D labels and does not include questionnaire names.
   - `questionnaire_plus_ia_label` additionally gives a low/moderate/high problematic digital-use profile label derived from the digital-use composite.

4. **Cue-Competition Model**
   - Prompt file: `ia_cue_competition_8conditions_full5tasks.jsonl`.
   - Full 2^3 factorial design over label cue L, quantitative score cue Q, and symptom-language cue D.
   - For token saving, use `ia_cue_competition_8conditions_core3tasks.jsonl` or the missing-condition files.

## Model profiles

- P1_low_PDU_low_ATT: low problematic digital use / low attention difficulties
- P2_moderate_PDU_low_ATT: moderate problematic digital use / low attention difficulties
- P3_high_PDU_low_ATT: high problematic digital use / low attention difficulties
- P4_high_PDU_high_ATT: high problematic digital use / elevated attention difficulties
- P5_high_ATT_low_PDU: elevated attention difficulties / low problematic digital use

## Run examples

### Qwen
```bash
export DASHSCOPE_API_KEY="YOUR_KEY"
python run_ia_experiment.py   --input ia_main_profile_prompts.jsonl   --provider qwen   --model qwen-plus   --output-dir outputs_ia_main_qwen   --target-samples 50   --samples-per-call 5   --temperature 0.7   --resume
```

### DeepSeek
```bash
export DEEPSEEK_API_KEY="YOUR_KEY"
python run_ia_experiment.py   --input ia_ablation_5conditions.jsonl   --provider deepseek   --model deepseek-chat   --output-dir outputs_ia_ablation_deepseek   --target-samples 50   --samples-per-call 5   --temperature 0.7   --resume
```

### MiniMax via OpenAI-compatible endpoint
```bash
export MINIMAX_API_KEY="YOUR_KEY"
export MINIMAX_BASE_URL="YOUR_MINIMAX_COMPATIBLE_BASE_URL"
python run_ia_experiment.py   --input ia_cue_competition_8conditions_core3tasks.jsonl   --provider minimax   --model minimax-m2.5   --output-dir outputs_ia_cue_minimax   --target-samples 50   --samples-per-call 5   --temperature 0.7   --resume
```

## Analyze main / ablation / cue results

```bash
python analyze_ia_profile_ablation_cue.py   --human-input ia_individual_prediction_input_with_labels.csv   --llm-csv outputs_ia_main_qwen/sample_level_outputs.csv outputs_ia_main_deepseek/sample_level_outputs.csv   --output-dir ia_analysis_outputs
```

For a full Cue-Competition analysis, pass CSVs containing all eight cue conditions.

## Analyze individual prediction

```bash
python analyze_ia_individual_prediction.py   --human-input ia_individual_prediction_input_with_labels.csv   --llm-csv outputs_ia_individual_qwen/sample_level_outputs.csv outputs_ia_individual_deepseek/sample_level_outputs.csv   --output-dir ia_individual_prediction_analysis
```

## Important design notes

- Metadata fields such as `profile_id` are **not** sent to models. Only the `system` and `user` fields are sent.
- In `score-only` and `questionnaire-only`, questionnaire names such as CAARS, CIAS, Young, DSM, ADHD, and internet addiction are not included in the model-facing prompt.
- All outputs are numeric-only JSON samples. Invalid samples are recorded separately.
- For a manuscript, describe this as problematic digital-use / internet-addiction-like profile simulation, not as clinical diagnosis.
