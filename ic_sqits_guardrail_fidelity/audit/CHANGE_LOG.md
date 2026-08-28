# Change Log

## 2026-08-27T22:31:26Z - Step 1 scaffold created

- Created IC-SQITS study repository structure under `ic_sqits_guardrail_fidelity/`.
- Added repository `README.md`.
- Added `audit/HUMAN_DECISIONS_LOG.md` and this change log.
- Added `freeze/environment.txt` with initial environment summary.
- Added `inputs/PRIOR_WORK_ONLY.md` to mark prior-work materials.
- Copied readable ETECOM DOCX input: `inputs/ETECOM_IEEE_ETECOM_2026_FINAL_MERGED_3AUTHORS_v2.docx`.
- Preserved empty experiment directories with `.gitkeep` placeholders where needed.
- Confirmed no prior-study results were placed in `raw/`, `processed/`, or `final_results/`.

## 2026-08-27T22:31:26Z - Step 2 novelty audit drafted

- Drafted `audit/PRIOR_WORK_BOUNDARY.md`.
- Drafted unsigned `audit/NOVELTY_FREEZE.md` template for human approval.
- Stopped at required human gate before Step 3.

## 2026-08-27T22:31:26Z - Step 2 human approval recorded

- Recorded in-session human approval in `audit/NOVELTY_FREEZE.md`.
- Updated `audit/HUMAN_DECISIONS_LOG.md` to mark novelty freeze approved.

## 2026-08-27T22:31:26Z - Step 3 RQs frozen and Step 4 draft started

- Froze `research/RESEARCH_QUESTIONS.md` after in-session human approval.
- Created `experiment/config.yaml` with `rq_version: 1.0`.
- Created `reports/STEP_03_REPORT.md`.
- Drafted `research/METRICS_SPEC.md` for Step 4 human review.

## 2026-08-27T22:31:26Z - Step 4 metrics frozen and Step 5 draft started

- Froze `research/METRICS_SPEC.md` after in-session human approval.
- Recorded Step 4 metric-policy decision in `audit/HUMAN_DECISIONS_LOG.md`.
- Began Step 5 analysis-plan drafting from runbook instructions.

## 2026-08-27T22:31:26Z - Step 5 analysis plan drafted

- Drafted `research/ANALYSIS_PLAN.md` for human approval.
- Created `reports/STEP_04_REPORT.md` and `reports/STEP_05_REPORT.md`.
- Stopped at Step 5 required human gate before Step 6.

## 2026-08-27T22:31:26Z - Step 5 analysis plan frozen and Step 6 drafted

- Froze `research/ANALYSIS_PLAN.md` after in-session human approval.
- Recorded Step 5 analysis-plan decision in `audit/HUMAN_DECISIONS_LOG.md`.
- Began Step 6 candidate-requirement drafting for the payment/approval benchmark.

## 2026-08-27T22:31:26Z - Step 6 drafted and Step 7 human gate opened

- Created `requirements/candidate_requirements.yaml` with 60 draft requirements.
- Created `reports/STEP_06_REPORT.md` and `reports/STEP_07_REPORT.md`.
- Stopped at Step 7 required human selection gate.

## 2026-08-27T22:31:26Z - Step 7 frozen and Step 8 draft created

- Recorded human-selected `requirements/requirements_v1.yaml` as frozen Step 7 set.
- Updated `reports/STEP_07_REPORT.md` to complete Step 7.
- Drafted obligation checklist files under `requirements/obligation_checklists/DRAFT/`.
- Created `reports/STEP_08_REPORT.md` and stopped at Step 8 human gate.

## 2026-08-27T22:31:26Z - Step 8 frozen and Step 9 created

- Recorded human-approved finalized obligation checklist files under `requirements/obligation_checklists/FINAL/`.
- Updated `reports/STEP_08_REPORT.md` to complete Step 8.
- Recorded Step 8 approval in `audit/HUMAN_DECISIONS_LOG.md`.
- Created `requirements/provenance.csv` for Step 9 requirement provenance audit.

## 2026-08-28T00:00:00Z - Step 10 drafted and Step 11 human gate opened

- Created F1 equivalent paraphrase files under `requirements/formulations/F1/` for all 48 selected requirements.
- Preserved formulation ambiguity for `R054` by leaving F1 text identical to F0.
- Created `reports/STEP_10_REPORT.md` and `reports/STEP_11_REPORT.md`.
- Stopped at Step 11 required human equivalence-review gate.

## 2026-08-28T00:00:00Z - Step 11 frozen and Step 12 drafted

- Recorded completed F0/F1 human equivalence review in `requirements/formulation_equivalence.csv`.
- Updated `reports/STEP_11_REPORT.md` to complete Step 11.
- Recorded Step 11 approval in `audit/HUMAN_DECISIONS_LOG.md`.
- Created F2 clause-order permutation files under `requirements/formulations/F2/`.
- Created `reports/STEP_12_REPORT.md` and `reports/STEP_13_REPORT.md`.

## 2026-08-28T00:00:00Z - Step 14 and Step 15 drafted

- Created F3 clarification files under `requirements/formulations/F3/` for all 48 selected requirements.
- Used `CANNOT_CLARIFY_WITHOUT_ASSUMPTION` for F3 rows where clarification would require a non-entailed assumption: `R025`, `R028`, `R054`, and `R055`.
- Created F4 underspecified-variant files under `requirements/formulations/F4/` for all 48 selected requirements.
- Recorded one removed semantic detail per F4 row.
- Created `reports/STEP_14_REPORT.md` and `reports/STEP_15_REPORT.md`.
