# ADHD and Internet Addiction LLM Simulation Experiments

This repository contains Large Language Model (LLM) simulation experiments investigating ADHD (Attention-Deficit/Hyperactivity Disorder) and problematic digital use / internet addiction profiles through behavioral task performance and questionnaire responses.

## 📖 Overview

The project uses LLMs to simulate behavioral and cognitive profiles associated with ADHD and internet addiction by having models complete cognitive tasks (Go/No-Go, n-back, BART) and respond to clinical questionnaires (CAARS, CIAS, Young's Internet Addiction Test, DSM criteria) under different profile conditions.

**Key Research Questions:**
- Can LLMs simulate distinct ADHD and internet addiction behavioral profiles?
- How do different prompt components (labels, scores, symptom descriptions) influence LLM behavior?
- Can individual-level predictions be made from questionnaire data alone?
- What is the relative contribution of different cue types (label, quantitative, descriptive)?

## 🗂️ Repository Structure

```
├── main_experiment/                 # Main experiments (all 5 models)
│   ├── deepseek-v4pro/              # DeepSeek v4 Pro experiments
│   ├── qwen-plus/                   # Qwen Plus experiments
│   ├── gpt-5.5/                     # GPT-5.5 experiments
│   ├── minimax-m2.5/                # MiniMax M2.5 experiments
│   └── claude-opus-4-7/             # Claude Opus 4.7 experiments
├── ablation_experiment/             # Ablation experiments
│   ├── deepseekv4-pro/              # DeepSeek ablation results
│   ├── minimax-m2.5/                # MiniMax ablation results
│   ├── qwen-plus/                   # Qwen Plus ablation results
│   ├── llm_prompt_templates_ablation_5conditions.jsonl
│   └── token_optimized_ablation_runner.py
├── individual_prediction/           # Individual prediction experiments
│   ├── internet_addiction_experiment_package(1)/
│   │   └── internet_addiction_experiment_package/
│   │       ├── run_ia_experiment.py
│   │       ├── analyze_ia_profile_ablation_cue.py
│   │       ├── analyze_ia_individual_prediction.py
│   │       ├── generate_ia_individual_prompts.py
│   │       ├── outputs/             # Experiment outputs
│   │       └── *.jsonl              # Prompt files for all experiments
│   ├── qs-only-out/                 # Questionnaire-only outputs
│   ├── ques-plus_out/               # Questionnaire + label outputs
│   └── token_optimized_ablation_runner.py
├── Cue-Competition Model/           # Cue competition experiments
│   ├── create_cue_prompts.py
│   ├── cue_competition_runner.py
│   ├── cue_competition_analyze.py
│   └── outputs_*/                   # Model-specific outputs (deepseek, qwen, minimax)
├── it-addiction-outputs/            # Consolidated output directory
│   ├── deepseek_v4pro_main/
│   ├── deepseek_v4pro_ablation/
│   ├── deepseek_v4pro_cue_8conditions_core3/
│   ├── deepseek_v4pro_individual_only/
│   ├── deepseek_v4pro_individual_plusslabel/
│   ├── qwen_plus_main/
│   ├── qwen_plus_ablation/
│   ├── qwen_plus_cue_8conditions_core3/
│   ├── qwenplus_individual_only/
│   ├── qwenplus_individual_plusslabel/
│   └── minimax_m25_main/
└── internet_addiction_deepseek_strict_package(1)/  # DeepSeek strict range validation
    └── internet_addiction_deepseek_strict_package/
        ├── deepseek_ia_strict_runner.py
        ├── validate_strict_ia_outputs.py
        └── *_strict_*.jsonl            # Strict range prompt files
```

## 🧪 Experiments

### 1. Main Profile Simulation

Simulates five distinct profiles across five behavioral tasks:

**Profiles:**
- **P1**: Low problematic digital use (PDU) / Low attention difficulties (ATT)
- **P2**: Moderate PDU / Low ATT
- **P3**: High PDU / Low ATT
- **P4**: High PDU / High ATT (comorbid)
- **P5**: High ATT / Low PDU

**Tasks:**
- Go/No-Go (inhibitory control)
- n-back (working memory)
- BART (risk-taking behavior)
- Clinical questionnaires (CAARS, CIAS, Young, DSM)

**Design:** 5 profiles × 5 tasks = 25 prompts, 50 samples per prompt

### 2. Prompt Ablation Study

Tests the contribution of different prompt components:

**Conditions:**
- **Label-only**: Profile label only (e.g., "high ADHD")
- **Score-only**: Quantitative scores without questionnaire names
- **Symptom-only**: Symptom descriptions without labels
- **Full-profile**: All information combined
- **Conflict**: Contradictory label and score information

**Design:** 5 conditions × 5 profiles × 5 tasks = 125 prompts

### 3. Individual Prediction

Generates predictions from real participant data:

**Two variants:**
- `questionnaire_only`: Anonymized scale scores (Scale A-D) without diagnostic labels
- `questionnaire_plus_ia_label`: Includes derived problematic digital use severity label

**Input:** Individual participant data with age, sex, CAARS, CIAS, Young, DSM totals

### 4. Cue-Competition Model

Full 2³ factorial design testing three cue types:
- **L**: Label cue (diagnostic/severity label)
- **Q**: Quantitative score cue (numeric totals)
- **D**: Descriptive symptom cue (symptom language)

**Design:** 8 conditions (all combinations of L, Q, D present/absent) × tasks

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+
pip install requests pandas tqdm
```

### API Keys Setup

```bash
# For DeepSeek v4 Pro
export DEEPSEEK_API_KEY="your_deepseek_key"

# For GPT-5.5
export OPENAI_API_KEY="your_openai_key"

# For Qwen Plus
export DASHSCOPE_API_KEY="your_dashscope_key"

# For MiniMax M2.5
export MINIMAX_API_KEY="your_minimax_key"
export MINIMAX_BASE_URL="your_minimax_base_url"

# For Claude Opus 4.7
export ANTHROPIC_API_KEY="your_anthropic_key"
```

### Running Main Experiments

The main experiments test **five LLM models** on ADHD and internet addiction profile simulation. All models use the same prompt files and experimental protocol.

#### DeepSeek v4 Pro
```bash
cd individual_prediction/internet_addiction_experiment_package(1)/internet_addiction_experiment_package/

export DEEPSEEK_API_KEY="your_deepseek_key"

python run_ia_experiment.py \
  --input ia_main_profile_prompts.jsonl \
  --provider deepseek \
  --model deepseek-chat \
  --output-dir outputs_ia_main_deepseek \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

#### GPT-5.5
```bash
export OPENAI_API_KEY="your_openai_key"

python run_ia_experiment.py \
  --input ia_main_profile_prompts.jsonl \
  --provider openai \
  --model gpt-5.5 \
  --output-dir outputs_ia_main_gpt55 \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

#### Qwen Plus
```bash
export DASHSCOPE_API_KEY="your_dashscope_key"

python run_ia_experiment.py \
  --input ia_main_profile_prompts.jsonl \
  --provider qwen \
  --model qwen-plus \
  --output-dir outputs_ia_main_qwen \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

#### MiniMax M2.5
```bash
export MINIMAX_API_KEY="your_minimax_key"
export MINIMAX_BASE_URL="your_minimax_base_url"

python run_ia_experiment.py \
  --input ia_main_profile_prompts.jsonl \
  --provider minimax \
  --model minimax-m2.5 \
  --output-dir outputs_ia_main_minimax \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

#### Claude Opus 4.7
```bash
export ANTHROPIC_API_KEY="your_anthropic_key"

python run_ia_experiment.py \
  --input ia_main_profile_prompts.jsonl \
  --provider anthropic \
  --model claude-opus-4-7 \
  --output-dir outputs_ia_main_claude \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

**Note:** All five models are run with identical experimental parameters to ensure fair comparison across models.

### Running Cue-Competition Experiments

```bash
cd "Cue-Competition Model/"
export DEEPSEEK_API_KEY="your_key"

python cue_competition_runner.py \
  --input cue_competition_missing4_core3tasks.jsonl \
  --output-dir outputs_deepseek_v4pro_core3 \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume
```

### DeepSeek Strict Range Validation

The DeepSeek strict range package addresses numeric range validity issues:

```bash
cd internet_addiction_deepseek_strict_package\(1\)/internet_addiction_deepseek_strict_package/

# Main profile experiment with strict ranges
python deepseek_ia_strict_runner.py \
  --input ia_main_profile_prompts_strict_problem_tasks.jsonl \
  --output-dir outputs_deepseek_ia_main_strict_problem_tasks \
  --model deepseek-chat \
  --target-samples 50 \
  --samples-per-call 5 \
  --temperature 0.7 \
  --resume

# Validate outputs
python validate_strict_ia_outputs.py \
  --input outputs_deepseek_ia_main_strict_problem_tasks/sample_level_outputs.csv \
  --output-dir outputs_deepseek_ia_main_strict_problem_tasks/validation
```

**Strict Range Constraints:**
- Accuracy and proportions: 0–1
- BART `adjusted_average_pumps`: 0–64
- BART `explosion_count`: 0–30
- `caars_total`: 0–78
- `cias_total`: 26–104
- `young_total`: 0–8
- DSM totals: 0–9 and 0–13

## 📊 Analysis

### Main / Ablation / Cue Analysis

```bash
cd individual_prediction/internet_addiction_experiment_package(1)/internet_addiction_experiment_package/

python analyze_ia_profile_ablation_cue.py \
  --human-input ia_individual_prediction_input_with_labels.csv \
  --llm-csv \
    outputs_ia_main_deepseek/sample_level_outputs.csv \
    outputs_ia_main_gpt55/sample_level_outputs.csv \
    outputs_ia_main_qwen/sample_level_outputs.csv \
    outputs_ia_main_minimax/sample_level_outputs.csv \
    outputs_ia_main_claude/sample_level_outputs.csv \
  --output-dir ia_analysis_outputs
```

### Individual Prediction Analysis

```bash
cd individual_prediction/internet_addiction_experiment_package(1)/internet_addiction_experiment_package/

python analyze_ia_individual_prediction.py \
  --human-input ia_individual_prediction_input_with_labels.csv \
  --llm-csv \
    outputs_ia_individual_deepseek/sample_level_outputs.csv \
    outputs_ia_individual_gpt55/sample_level_outputs.csv \
    outputs_ia_individual_qwen/sample_level_outputs.csv \
    outputs_ia_individual_minimax/sample_level_outputs.csv \
    outputs_ia_individual_claude/sample_level_outputs.csv \
  --output-dir ia_individual_prediction_analysis
```

### Cue-Competition Full Analysis

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

## 📁 Output Files

Each experiment run generates:
- `raw_calls.jsonl`: Raw API calls and responses
- `sample_level_outputs.jsonl`: Valid parsed samples (JSONL)
- `sample_level_outputs.csv`: Valid parsed samples (CSV format)
- `invalid_samples.jsonl`: Out-of-range or malformed samples
- `run_summary.json`: Experiment metadata and statistics

## ⚙️ Design Notes

**Important Considerations:**
- Metadata fields (e.g., `profile_id`, `task_id`) are **not** sent to models
- Only `system` and `user` message fields are sent to the API
- In `score-only` and `questionnaire-only` conditions, questionnaire names (CAARS, CIAS, Young, DSM) are **not** included in prompts
- All task outputs are numeric-only JSON samples
- Invalid samples are logged separately and excluded from analysis
- The `--resume` flag allows continuation of interrupted runs

**Ethical Guidelines:**
- This is a **computational simulation study**, not clinical diagnosis
- Describe as "ADHD-like" or "internet-addiction-like" profile simulation in publications
- Do not claim diagnostic or clinical validity
- Real clinical assessment requires professional evaluation

## 🔧 Supported Models

**Main Experiment Models (all five):**
- **DeepSeek v4 Pro**: `deepseek-chat` (via DeepSeek API)
- **GPT-5.5**: `gpt-5.5` (via OpenAI API)
- **Qwen Plus**: `qwen-plus` (via DashScope API)
- **MiniMax M2.5**: `minimax-m2.5` (via OpenAI-compatible API)
- **Claude Opus 4.7**: `claude-opus-4-7` (via Anthropic API)

**Additional Models:**
- Generic OpenAI-compatible endpoints supported via `--provider openai`

## 📝 Citation

If you use this code or data in your research, please cite:

```bibtex
@misc{adhd-ia-llm-simulation,
  author = {Tian, Songjie},
  title = {ADHD and Internet Addiction LLM Simulation Experiments},
  year = {2024},
  publisher = {GitHub},
  url = {https://github.com/melt502/adhd-it-addiction-experiment}
}
```

## 📄 License

[Specify your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📧 Contact

For questions or collaborations, please open an issue on GitHub.

---

**Last Updated:** June 2024
