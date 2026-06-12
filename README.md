# ADHD and Problematic Digital Use LLM Simulation Project

## Overview

This repository contains data, prompts, model outputs, and analysis scripts for the study:

**From Plausible Profiles to Predictive Failure: Evaluating LLM-Simulated Participants Using ADHD-Related Traits and Problematic Digital Use Profiles**

The project evaluates whether large language models (LLMs) can serve as valid simulated participants in psychological research.

Using human benchmark data and multiple LLMs, we examine:

1. Whether LLMs reproduce human group-level behavioral differences.
2. Which information sources drive simulated behavior (labels, questionnaire scores, or symptom descriptions).
3. Whether LLM-generated responses predict the behavior of real participants.
4. Whether these patterns generalize from ADHD-related traits to problematic digital-use profiles.

The central methodological question is:

> Do LLM-simulated participants demonstrate behavioral predictive validity, or do they primarily reproduce semantic stereotypes associated with psychologically meaningful labels?

---

## Human Benchmark Dataset

### Questionnaire Sample

* N = 2,016 young adults
* ADHD-related traits assessed using CAARS
* Problematic digital-use symptoms assessed using:

  * CIAS
  * Young's Internet Addiction Test
  * DSM-derived digital-use indicators

### Experimental Subsample

* N = 157 participants
* Behavioral tasks:

  * Stroop
  * n-back
  * BART
  * Delay Discounting Task (DDT)
  * Continuous Performance Test (CPT)

CPT-derived labels were used as task-based attention-profile indicators and were not treated as clinical ADHD diagnoses.

---

## LLM Models

The project includes simulations conducted using:

* GPT-5.5
* Claude Sonnet
* DeepSeek
* Qwen
* MiniMax

Models were used as simulated participants rather than as analytical tools.

---

## Repository Structure

```text
.
├── prompts/
│   ├── ADHD/
│   ├── PDU/
│   ├── ablation/
│   └── individual_prediction/
│
├── outputs/
│   ├── GPT/
│   ├── DeepSeek/
│   ├── Qwen/
│   ├── Claude/
│   └── MiniMax/
│
├── human_data/
│   ├── aggregate_tables/
│   └── benchmark_statistics/
│
├── analysis/
│   ├── cue_contribution/
│   ├── individual_prediction/
│   ├── robustness_checks/
│   └── visualization/
│
├── figures/
│
├── supplement/
│
└── README.md
```

---

## Main Analyses

### Study 1: Human Benchmark

Characterization of ADHD-related traits, problematic digital-use symptoms, and behavioral task performance.

### Study 2: Profile-Level Simulation

Comparison of LLM-generated behavioral profiles with human benchmark profiles.

### Study 3: Cue-Contribution Analysis

Decomposition of the influence of:

* Labels (L)
* Questionnaire scores (Q)
* Symptom descriptions (D)

Conditions include:

```text
Null
L only
Q only
D only
L + Q
L + D
Q + D
Full
```

### Study 4: Individual Prediction

Prediction of real participant behavior using:

* Questionnaire information
* LLM-generated predictions

Benchmarks include:

* Mean prediction
* CPT-group mean
* Ridge regression
* Random forest

### Study 5: Generalization to Problematic Digital Use

Evaluation of whether semantic-label dominance extends beyond ADHD-related traits to problematic digital-use profiles.

---

## Key Finding

Across multiple models and behavioral tasks, LLM-generated profiles often appeared psychologically plausible at the group level.

However, individual-level prediction analyses indicated that:

* Semantic labels and symptom descriptions exerted substantially stronger influence than anonymized numerical scores.
* Behavioral predictive validity was limited.
* Profile-level plausibility should not be interpreted as evidence of individual-level predictive accuracy.

These findings suggest that LLM-simulated participants may reproduce psychologically meaningful stereotypes without accurately modeling real human behavior.

---

## Reproducibility

This repository contains:

* Prompt templates
* Model outputs
* Analysis scripts
* Figure-generation code
* Supplementary materials

All analyses reported in the manuscript can be reproduced using the scripts provided in the `analysis/` directory.

---

## Ethical Statement

All human participant procedures were approved by the appropriate institutional ethics committee.

Only de-identified and aggregate human data are included in this repository.

Individual-level participant data are not publicly shared because they contain sensitive psychological and behavioral information.

Researchers interested in restricted-access data may contact the corresponding author.

---

## Citation

If you use this repository, please cite:

Long, Y., Tian, S., Zhao, C., & Zhang, W. (2026).

*From Plausible Profiles to Predictive Failure: Evaluating LLM-Simulated Participants Using ADHD-Related Traits and Problematic Digital Use Profiles.*

Manuscript under review.

---

## License

This repository is released for academic and non-commercial research purposes.

Please contact the authors regarding commercial use.

---

## Contact

Corresponding Author:

Wei Zhang

Email: [INSERT EMAIL]

Project Repository:

https://github.com/melt502/llm-simulated-participants-validation
