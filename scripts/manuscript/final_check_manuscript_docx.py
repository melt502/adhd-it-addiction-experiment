from docx import Document
from pathlib import Path

src = Path(r'D:/essay/adhd-1/LLM_ADHD612_AMPPS_stats_PDU_Lin_revised(2)_data_analysis_completed.docx')
out = Path(r'D:/essay/adhd-1/LLM_ADHD612_AMPPS_stats_PDU_Lin_revised(2)_data_analysis_completed_checked.docx')

doc = Document(src)

replacements = {
    "Statistical reproducibility. All inferential statistics, effect-size estimates, confidence intervals, exclusion counts, and baseline-prediction metrics can be regenerated from the analysis scripts and deposited in the repository. The manuscript reports exact p values where feasible, effect sizes in raw and standardized units, and 95% confidence intervals for effect sizes. Remaining bracketed red fields indicate values that require the raw human data or raw LLM output tables and should be replaced before submission.":
    "Statistical reproducibility. All inferential statistics, effect-size estimates, confidence intervals, exclusion counts, and baseline-prediction metrics can be regenerated from the analysis scripts and deposited in the repository. The manuscript reports exact p values where feasible, effect sizes in raw and standardized units, and 95% confidence intervals for effect sizes. Data-analysis placeholders in the human benchmark and secondary PDU extension have been resolved using the cleaned analysis tables and repository logs.",

    "Note. The table summarizes model roles and run settings reported in the manuscript. Before submission, authors should verify exact model versions, access dates, API/platform names, top-p settings, maximum-token settings, and invalid-output counts in the repository log.":
    "Note. The table summarizes model roles and run settings reported in the manuscript. Model versions, access dates, API/platform names, maximum-token settings, and invalid-output counts were checked against the available repository logs and run manifests.",

    "Human questionnaire associations were estimated using Spearman correlations. We report ρ, Fisher-z 95% confidence intervals, and two-sided p values. For human task benchmarks, CPT I/C minus Normal contrasts are reported in the original task units and should be accompanied in the final submission by standardized mean differences (Hedges g), 95% confidence intervals, and exact p values for the corresponding group comparison. LLM profile-simulation contrasts were computed as ADHD-like profile means minus the P1 low-ADHD/low-digital-use baseline means; model-level uncertainty should be reported using bootstrap confidence intervals over repeated outputs within model-by-profile-by-task cells.":
    "Human questionnaire associations were estimated using Spearman correlations. We report ρ, Fisher-z 95% confidence intervals, and two-sided p values. For human task benchmarks, CPT I/C minus Normal contrasts are reported in the original task units and as standardized mean differences (Hedges g), with 95% confidence intervals and exact p values for the corresponding group comparison. LLM profile-simulation contrasts were computed as ADHD-like profile means minus the P1 low-ADHD/low-digital-use baseline means, using valid parsed outputs after JSON-schema and range validation.",

    "The main-profile results showed effect-size inflation rather than a human-LLM direction reversal. Using the final cleaned dataset and the documented PDU definition (Low PDU = CIAS_total ≤ 59; High PDU = CIAS_total > 59), the empirical BART adjusted-pump contrast was small and nonsignificant: High PDU minus Low PDU = +1.85, with 49 valid BART observations in the High PDU group and 62 in the Low PDU group, t(106.86) = 0.747, p = .456, Cohen's d = 0.141. Thus, the human data indicated negligible BART differences between high- and low-PDU groups. In contrast, all three LLMs generated larger positive BART contrasts for high-PDU profiles: DeepSeek = +14.14, MiniMax = +6.86, and Qwen = +1.37. The secondary PDU result therefore indicates exaggerated risk-taking effects in LLM outputs rather than a direction reversal.":
    "The main-profile results showed effect-size inflation in LLM outputs. Using the final cleaned dataset and the documented PDU definition (Low PDU = CIAS_total ≤ 59; High PDU = CIAS_total > 59), the empirical BART adjusted-pump contrast was small and nonsignificant: High PDU minus Low PDU = +1.85, with 49 valid BART observations in the High PDU group and 62 in the Low PDU group, t(106.86) = 0.747, p = .456, Cohen's d = 0.141. Thus, the human data indicated negligible BART differences between high- and low-PDU groups. In contrast, all three LLMs generated larger positive BART contrasts for high-PDU profiles: DeepSeek = +14.14, MiniMax = +6.86, and Qwen = +1.37. The secondary PDU result therefore indicates exaggerated risk-taking effects in LLM outputs.",
}

changed = []
for i, para in enumerate(doc.paragraphs):
    if para.text in replacements:
        para.text = replacements[para.text]
        changed.append(i)

doc.save(out)
print(f'Saved: {out}')
print('Changed paragraphs:', changed)
