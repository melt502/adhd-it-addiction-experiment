# Supplemental Material

This supplemental package supports the manuscript on semantic cue dominance and predictive validity in LLM-simulated ADHD-like and problematic digital-use profiles.

## Contents

### 1. Human data cleaning and task metrics

- `ADHD_data_cleaning_report.md`: Narrative summary of questionnaire and task cleaning.
- `ADHD_data_cleaning_rules.md`: Detailed cleaning rules, validity criteria, and measurement decisions.
- `clean_adhd_experiment.py`: Script used to generate cleaned aggregate outputs.
- `tables/cleaning_task_availability.csv`: Task-wise availability and strict-valid counts.
- `tables/cleaning_group_CPT_counts.csv`: CPT/group count summaries.
- `tables/scale_score_reliability_audit.csv`: Scale-score range checks, item-total checks, and reliability summaries.
- `tables/cleaned_metric_descriptives.csv`: Descriptive statistics for cleaned questionnaire and task variables.
- `codebook/cleaned_data_dictionary.csv`: Variable dictionary for the cleaned aggregate dataset.

### 2. Human benchmark results

- `tables/cleaned_questionnaire_task_spearman_all.csv`: Questionnaire-task Spearman correlations.
- `tables/cleaned_questionnaire_task_spearman_top80.csv`: Top questionnaire-task associations by absolute correlation.
- `tables/task_level_hedges_g.csv`: Hedges g, confidence intervals, and group contrasts for task-level benchmarks.
- `tables/cleaned_CPT_group_summary.csv`: CPT-profile group summaries.
- `tables/cleaned_CPT_N_vs_ADHD_effect_sizes.csv`: Normal versus I/C standardized contrasts.

### 3. Data-quality and sensitivity checks

- `tables/alternative_totals_do_not_use_audit.csv`: Audit of alternative totals that were not used for the primary analysis.

### 4. LLM prompt, output, and run materials

LLM prompt templates, JSON schemas, parsed outputs, invalid-output logs, and run summaries are stored in the main experiment directories:

- `main_experiment/`
- `ablation_experiment/`
- `Cue-Competition Model/`
- `individual_prediction/`
- `it-addiction-outputs/`
- `internet_addiction_deepseek_strict_package(1)/`

### 5. Cue-contribution and individual-prediction analyses

Cue-contribution scripts and outputs are available under `Cue-Competition Model/` and related output folders. Individual-prediction scripts and outputs are available under `individual_prediction/`.

### 6. Problematic digital-use extension

Problematic digital-use outputs and strict rerun materials are available under `it-addiction-outputs/` and `internet_addiction_deepseek_strict_package(1)/`.

## Data protection

Raw individual-level human data and raw CPT report files are not included in the public repository. Only cleaned aggregate tables, reproducibility scripts, and de-identified summary outputs are provided.
