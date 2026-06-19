# ADHD and Problematic Digital Use LLM Simulation Experiments

This repository supports a manuscript on whether large language models (LLMs) can be used as simulated participants for clinically or behaviorally meaningful profiles. The primary stress test concerns ADHD-related traits and CPT-defined attention profiles. A secondary generalization check examines problematic digital-use (PDU) profiles.

The central claim is that LLM-generated profiles can appear psychologically plausible while failing human-benchmark and individual-prediction validity checks. The repository therefore emphasizes prompt transparency, cue-sensitivity audits, aggregate human benchmarks, and reproducible analysis outputs.

## Research questions

- Do LLMs generate coherent ADHD-like or PDU-like behavioral task profiles?
- Do those profiles match human benchmark data, or do they reflect stereotype-oriented patterns?
- Which prompt cues drive the simulations: labels, anonymized numeric scores, or symptom-language descriptions?
- Can LLM outputs predict real individuals' task behavior from anonymized questionnaire information?

## Repository structure

```text
├── main_experiment/                         # Main LLM profile simulations
├── ablation_experiment/                     # Label/score/symptom/full/conflict prompt ablations
├── Cue-Competition Model/                   # 2^3 factorial cue-competition experiments
├── individual_prediction/                   # Individual-level prompt generation and prediction analyses
├── it-addiction-outputs/                    # Consolidated PDU LLM outputs
├── internet_addiction_deepseek_strict_package(1)/
│   └── internet_addiction_deepseek_strict_package/
│       ├── deepseek_ia_strict_runner.py
│       ├── validate_strict_ia_outputs.py
│       └── *_strict_*.jsonl
├── supplement/                              # Supplemental methods, aggregate tables, codebook
│   ├── Supplemental_Material.md
│   ├── ADHD_data_cleaning_report.md
│   ├── ADHD_data_cleaning_rules.md
│   ├── clean_adhd_experiment.py
│   ├── tables/
│   └── codebook/
├── manuscript/                              # Curated manuscript copy
├── scripts/manuscript/                      # Manuscript editing/checking scripts
├── OPEN_PRACTICES.md                        # Data and code availability details
├── CITATION.cff
├── LICENSE
└── requirements.txt
```

## Experiments

### 1. Main profile simulation

LLMs generated numeric task outcomes for profile conditions varying attention-related and problematic digital-use cues. The manuscript reports five model families: DeepSeek, Qwen, MiniMax, Claude, and GPT-5.5.

### 2. Prompt ablation

Prompt conditions isolate different information sources:

- label-only cues
- anonymized numeric-score cues
- symptom-language cues
- full-profile cues
- conflict cues with inconsistent label and score information

### 3. Cue-competition analysis

The cue-competition design crosses three cue types in a 2^3 factorial design:

- label cue
- numeric-score cue
- symptom-language cue

Cue-contribution analyses estimate whether simulated task behavior is driven primarily by clinical semantic information or anonymized quantitative information.

### 4. Individual prediction

Individual-prediction prompts use anonymized real-participant information. Task outcomes are withheld from the model. Predictions are compared with statistical baselines using correlations, RMSE, and out-of-sample R².

### 5. Secondary PDU generalization check

The PDU extension tests whether a similar cue-driven mechanism appears when the label domain changes from ADHD-related traits to problematic digital use. It is treated as supportive evidence for generality, not as a second primary clinical study.

## Human benchmark and supplemental tables

Cleaned aggregate ADHD human benchmark outputs are in `supplement/`. Raw individual-level human data and raw CPT report files are not publicly released because they contain sensitive mental-health-related and behavioral measures.

Key supplemental outputs include:

- task availability and exclusion summaries
- scale reliability and score-audit checks
- questionnaire-task correlations
- CPT group summaries
- Hedges g task-level contrasts
- cleaned variable dictionary
- data-cleaning report and rules

See `supplement/Supplemental_Material.md` and `OPEN_PRACTICES.md` for details.

## Installation

Python 3.8+ is recommended.

```bash
pip install -r requirements.txt
```

## API keys

Set only the keys needed for the model provider you are running:

```bash
export DEEPSEEK_API_KEY="your_deepseek_key"
export OPENAI_API_KEY="your_openai_key"
export DASHSCOPE_API_KEY="your_dashscope_key"
export MINIMAX_API_KEY="your_minimax_key"
export MINIMAX_BASE_URL="your_minimax_base_url"
export ANTHROPIC_API_KEY="your_anthropic_key"
```

Do not commit API keys or `.env` files.

## Example commands

### Cue-competition experiment

```bash
cd "Cue-Competition Model/"
python cue_competition_runner.py \
  --input cue_competition_missing4_core3tasks.jsonl \
  --output-dir outputs_deepseek_v4pro_core3 \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

### Cue-competition analysis

```bash
cd "Cue-Competition Model/"
python cue_competition_analyze.py \
  --input cue_competition_prompt_index.csv \
  --llm-csv \
    outputs_deepseek_v4pro_core3/sample_level_outputs.csv \
    outputs_qwen_plus_core3/sample_level_outputs.csv \
    outputs_minimax_m25_core3/sample_level_outputs.csv \
  --output-dir cue_analysis_outputs
```

### DeepSeek strict range validation

```bash
cd internet_addiction_deepseek_strict_package\(1\)/internet_addiction_deepseek_strict_package/
python deepseek_ia_strict_runner.py \
  --input ia_main_profile_prompts_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_main_strict_problem_tasks \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume

python validate_strict_ia_outputs.py \
  --input outputs_deepseek_ia_main_strict_problem_tasks/sample_level_outputs.csv \
  --output-dir outputs_deepseek_ia_main_strict_problem_tasks/validation
```

## Data protection

This is a computational simulation and aggregate-analysis repository. It is not a clinical diagnostic tool. Publications should refer to ADHD-related traits, CPT-defined attention profiles, ADHD-like simulated profiles, and problematic digital-use profiles rather than diagnosed clinical groups unless clinically diagnosed data are actually used.

Raw individual-level human data, raw CPT reports, and other potentially identifiable source files are excluded from the public repository.

## Citation

Please cite the repository using `CITATION.cff` and cite the associated manuscript when available.

## License

Code is released under the MIT License. See `LICENSE`.

## Contact

For questions or collaborations, please open an issue on GitHub.

**Last updated:** 19 June 2026
