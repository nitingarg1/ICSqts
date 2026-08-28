# IC-SQITS Guardrail Fidelity Study Repository

Controlling protocol: `inputs/IC_SQITS_RUNBOOK_48_STEPS.docx`

Study title:
`Who Guards the Guardrails? Evaluating Semantic Fidelity and Robustness of LLM-Generated Security Controls for AI-Written Software`

This repository is reserved for IC-SQITS experiment artifacts only.

Rules fixed at repository creation:
- Do not copy prior experiment results into `raw/`, `processed/`, or `final_results/`.
- Keep GAISS, ETECOM, and manuscript inputs under `inputs/` as `PRIOR_WORK_ONLY` material.
- Preserve all raw generation and execution artifacts exactly as produced.
- Stop at every `HUMAN_GATE_REQUIRED` and `MODEL_SWITCH_REQUIRED` checkpoint in runbook.

Current environment summary:
- Timestamp (UTC): `2026-08-27T22:31:26Z`
- OS: `macOS 26.6 (25G72)`
- Python: `Python 3.14.6`
- Git: `git version 2.55.0`
- Current repo HEAD before scaffold commit: `d7af2b2f6d0df58020fe310a74a5c53576dec918`
- Repository root commit: `189a4b7a6d01fca093f851e2f0dbae7f0fe5d515`

Prior-work inputs:
- `inputs/GAISS_FINAL.docx`
- `inputs/ETECOM_FINAL_OR_SUBMITTED.pdf`
- `inputs/ETECOM_IEEE_ETECOM_2026_FINAL_MERGED_3AUTHORS_v2.docx`
- `inputs/IC_SQITS_FIRST_DRAFT.docx`
- `inputs/IC_SQITS_FIRST_DRAFT.md`
- `inputs/IC_SQITS_RUNBOOK_48_STEPS.docx`
- `inputs/PRIOR_WORK_ONLY.md`

Status at repository creation:
- No IC-SQITS raw experiment results created yet.
- `raw/`, `processed/`, and `final_results/` contain no prior-study results.
- Step reports are stored under `reports/`.

Top-level layout:
- `inputs/` source documents and prior-work inputs
- `audit/` change log, human decisions, novelty boundary, freezes
- `requirements/` requirement corpus, provenance, formulations, obligation checklists
- `application/` benchmark application specification and implementation
- `variants/` compliant, violating, valid-alternative, and boundary variants
- `prompts/` prompt templates and versions
- `guardrails/` human and LLM-generated guardrails
- `experiment/` runner, evaluator, validators, schemas, freeze utilities
- `raw/` raw generation, execution, log, and failure artifacts
- `processed/` recomputable processed outputs only
- `analysis/` analysis scripts and reports
- `freeze/` environment and experiment freeze artifacts
- `final_results/` verified results package only after final freeze
- `research/` working research notes
- `reports/` step reports
