# LLM Run Inventory

This file lists run-quality and summary files available in the repository. Use these files to verify component-specific output counts, invalid-output rates, and model/task/profile coverage.

## `ablation_experiment/deepseekv4-pro/completion_summary.csv`

Rows including header: 126
Columns: ablation_condition, profile_id, task_id, n_samples

## `ablation_experiment/minimax-m2.5/completion_summary.csv`

Rows including header: 126
Columns: ablation_condition, profile_id, task_id, n_samples

## `ablation_experiment/qwen-plus/completion_summary.csv`

Rows including header: 126
Columns: ablation_condition, profile_id, task_id, n_samples

## `Cue-Competition Model/outputs_deepseek_v4pro_core3/completion_summary.csv`

Rows including header: 61
Columns: condition_id, profile_id, task_id, n

## `Cue-Competition Model/outputs_minimax_m25_core3/completion_summary.csv`

Rows including header: 61
Columns: condition_id, profile_id, task_id, n

## `Cue-Competition Model/outputs_qwen_plus_core3/completion_summary.csv`

Rows including header: 61
Columns: condition_id, profile_id, task_id, n

## `individual_prediction/qs-only-out/deepseek/completion_summary.csv`

Rows including header: 441
Columns: ablation_condition, profile_id, task_id, n_samples

## `individual_prediction/qs-only-out/minimax-m2.5/completion_summary.csv`

Rows including header: 441
Columns: ablation_condition, profile_id, task_id, n_samples

## `individual_prediction/qs-only-out/qwen-plus/completion_summary.csv`

Rows including header: 441
Columns: ablation_condition, profile_id, task_id, n_samples

## `individual_prediction/ques-plus_out/deepseek/completion_summary.csv`

Rows including header: 441
Columns: ablation_condition, profile_id, task_id, n_samples

## `individual_prediction/ques-plus_out/minimax/completion_summary.csv`

Rows including header: 441
Columns: ablation_condition, profile_id, task_id, n_samples

## `individual_prediction/ques-plus_out/qwen/completion_summary.csv`

Rows including header: 441
Columns: ablation_condition, profile_id, task_id, n_samples

## `it-addiction-outputs/deepseek_v4pro_cue_8conditions_core3/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `it-addiction-outputs/deepseek_v4pro_individual_only/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `it-addiction-outputs/deepseek_v4pro_individual_plusslabel/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `it-addiction-outputs/minimax_individual_plus_label/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `it-addiction-outputs/minimax_individual_qonly/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `it-addiction-outputs/qwen_plus_cue_8conditions_core3/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `it-addiction-outputs/qwenplus_individual_only/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `it-addiction-outputs/qwenplus_individual_plusslabel/completion_summary.csv`

Rows including header: 1
Columns: experiment_type, condition_id, profile_id, task_id, feature_condition, n

## `main_experiment/claude-opus-4-7/claude_results/formal_summary_by_profile_task.csv`

Rows including header: 28
Columns: , , , prompt_index, prompt_index, prompt_index, prompt_index, prompt_index, input_tokens, input_tokens, input_tokens, input_tokens, input_tokens, output_tokens, output_tokens, output_tokens, output_tokens, output_tokens, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, accuracy, accuracy, accuracy, accuracy, accuracy, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, total_earnings, total_earnings, total_earnings, total_earnings, total_earnings, explosion_count, explosion_count, explosion_count, explosion_count, explosion_count, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, discounting_k, discounting_k, discounting_k, discounting_k, discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, caars_total, caars_total, caars_total, caars_total, caars_total, cias_total, cias_total, cias_total, cias_total, cias_total, young_total, young_total, young_total, young_total, young_total, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total2, dsm_total2, dsm_total2, dsm_total2, dsm_total2

## `main_experiment/claude-opus-4-7/claude_results/qc_summary.json`

Top-level fields: n_valid, n_invalid, expected_valid

## `main_experiment/deepseek-v4pro/formal_outputs_deepseek-v4pro/formal_summary_by_profile_task.csv`

Rows including header: 28
Columns: , , , prompt_index, prompt_index, prompt_index, prompt_index, prompt_index, input_tokens, input_tokens, input_tokens, input_tokens, input_tokens, output_tokens, output_tokens, output_tokens, output_tokens, output_tokens, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, accuracy, accuracy, accuracy, accuracy, accuracy, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, total_earnings, total_earnings, total_earnings, total_earnings, total_earnings, explosion_count, explosion_count, explosion_count, explosion_count, explosion_count, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, discounting_k, discounting_k, discounting_k, discounting_k, discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, caars_total, caars_total, caars_total, caars_total, caars_total, cias_total, cias_total, cias_total, cias_total, cias_total, young_total, young_total, young_total, young_total, young_total, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total2, dsm_total2, dsm_total2, dsm_total2, dsm_total2

## `main_experiment/deepseek-v4pro/formal_outputs_deepseek-v4pro/qc_summary.json`

Top-level fields: n_valid, n_invalid, expected_valid

## `main_experiment/gpt-5.5/formal_outputs_openai/formal_summary_by_profile_task.csv`

Rows including header: 28
Columns: , , , prompt_index, prompt_index, prompt_index, prompt_index, prompt_index, input_tokens, input_tokens, input_tokens, input_tokens, input_tokens, output_tokens, output_tokens, output_tokens, output_tokens, output_tokens, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, accuracy, accuracy, accuracy, accuracy, accuracy, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, explosion_count, explosion_count, explosion_count, explosion_count, explosion_count, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, total_earnings, total_earnings, total_earnings, total_earnings, total_earnings, discounting_k, discounting_k, discounting_k, discounting_k, discounting_k, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, caars_total, caars_total, caars_total, caars_total, caars_total, cias_total, cias_total, cias_total, cias_total, cias_total, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total2, dsm_total2, dsm_total2, dsm_total2, dsm_total2, young_total, young_total, young_total, young_total, young_total

## `main_experiment/gpt-5.5/formal_outputs_openai/qc_summary.json`

Top-level fields: n_valid_total, n_invalid_total

## `main_experiment/minimax-m2.5/formal_outputs_minimax/formal_summary_by_profile_task-mini.csv`

Rows including header: 28
Columns: , , , prompt_index, prompt_index, prompt_index, prompt_index, prompt_index, input_tokens, input_tokens, input_tokens, input_tokens, input_tokens, output_tokens, output_tokens, output_tokens, output_tokens, output_tokens, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, accuracy, accuracy, accuracy, accuracy, accuracy, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, total_earnings, total_earnings, total_earnings, total_earnings, total_earnings, explosion_count, explosion_count, explosion_count, explosion_count, explosion_count, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, discounting_k, discounting_k, discounting_k, discounting_k, discounting_k, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, caars_total, caars_total, caars_total, caars_total, caars_total, cias_total, cias_total, cias_total, cias_total, cias_total, young_total, young_total, young_total, young_total, young_total, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total2, dsm_total2, dsm_total2, dsm_total2, dsm_total2

## `main_experiment/minimax-m2.5/formal_outputs_minimax/qc_summary.json`

Top-level fields: n_valid, n_invalid, expected_valid

## `main_experiment/qwen-plus/formal_outputs_qwen/formal_summary_by_profile_task.csv`

Rows including header: 28
Columns: , , , prompt_index, prompt_index, prompt_index, prompt_index, prompt_index, input_tokens, input_tokens, input_tokens, input_tokens, input_tokens, output_tokens, output_tokens, output_tokens, output_tokens, output_tokens, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, elapsed_seconds, accuracy, accuracy, accuracy, accuracy, accuracy, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, interference_effect_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, mean_rt_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, rt_sd_ms, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, overall_accuracy, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_1back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_2back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, accuracy_3back, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, adjusted_average_pumps, explosion_count, explosion_count, explosion_count, explosion_count, explosion_count, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, risk_preference_0_1, total_earnings, total_earnings, total_earnings, total_earnings, total_earnings, discounting_k, discounting_k, discounting_k, discounting_k, discounting_k, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, immediate_choice_proportion, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, log_discounting_k, caars_total, caars_total, caars_total, caars_total, caars_total, cias_total, cias_total, cias_total, cias_total, cias_total, young_total, young_total, young_total, young_total, young_total, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total1, dsm_total2, dsm_total2, dsm_total2, dsm_total2, dsm_total2

## `main_experiment/qwen-plus/formal_outputs_qwen/qc_summary.json`

Top-level fields: n_valid, n_invalid, expected_valid
