# Open Practices and Data Availability

This repository supports the manuscript on LLM-simulated ADHD-like and problematic digital-use profiles. It is intended to make the computational experiments, aggregate analyses, and reporting pipeline reproducible while protecting sensitive individual-level human data.

## Publicly available materials

The repository provides:

- Prompt templates for main profile simulation, prompt ablation, cue-competition, and individual-prediction experiments.
- JSON output schemas and parsing/validation scripts.
- Parsed LLM outputs and run summaries for the reported model families where available.
- De-identified aggregate human-data summaries used for the human benchmark.
- Data-cleaning rules, task-availability summaries, scale reliability checks, and effect-size tables.
- Cue-contribution scripts and outputs.
- Individual-prediction scripts and summary metrics.
- Problematic digital-use extension outputs and summary tables.
- A codebook / variable dictionary for the cleaned aggregate dataset.
- Manuscript and supplemental-material files prepared for transparent review.

## Not publicly released

Raw individual-level human data are not included because they contain sensitive mental-health-related and behavioral measures. Raw CPT report files and other source records are also excluded from the public repository.

Qualified researchers may request access to restricted human data from the corresponding author, subject to institutional approval and a data-use agreement.

## Repository guide

- `main_experiment/`: Main LLM profile-simulation experiments.
- `ablation_experiment/`: Prompt-ablation experiments.
- `Cue-Competition Model/`: Factorial cue-competition experiments.
- `individual_prediction/`: Individual-level prediction prompt generation, runs, and analyses.
- `it-addiction-outputs/`: Consolidated problematic digital-use LLM outputs.
- `internet_addiction_deepseek_strict_package(1)/`: DeepSeek strict-range rerun package.
- `supplement/`: Supplemental methods, aggregate tables, codebook, and ADHD human benchmark cleaning materials.
- `manuscript/`: Curated manuscript copy.
- `scripts/manuscript/`: Scripts used to apply manuscript edits and reference cleanup.

## Reproducibility notes

The repository includes both primary analysis files and some historical/intermediate experiment outputs. When rerun outputs differ from earlier outputs, prefer the files described in `supplement/` and the strict rerun package, because these correspond most closely to the current manuscript.

Model outputs may vary across API versions and access dates. Run summaries and logs should therefore be consulted when comparing exact numeric reproduction with the manuscript.
