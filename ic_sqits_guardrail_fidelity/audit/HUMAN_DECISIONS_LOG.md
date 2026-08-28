# Human Decisions Log

## 2026-08-27

### Decision 001
- Decision: Work in existing repository on `main`; do not create isolated worktree.
- Source: User instruction.
- Impact: All step execution proceeds in place.

### Decision 002
- Decision: Use `ETECOM_IEEE_ETECOM_2026_FINAL_MERGED_3AUTHORS_v2.docx` as readable equivalent source for ETECOM overlap review.
- Source: User instruction.
- Impact: Step 2 novelty audit uses DOCX source instead of unreadable PDF extraction path.

### Decision 003
- Decision: Use terse caveman-style user-facing updates.
- Source: User instruction.
- Impact: Affects interaction style only, not experiment artifacts.

### Decision 004
- Decision: Reviewed `audit/PRIOR_WORK_BOUNDARY.md` and approved `audit/NOVELTY_FREEZE.md`.
- Source: User instruction.
- Impact: Step 2 complete. Step 3 may begin.

### Decision 005
- Decision: Approved frozen wording for RQ1-RQ4 including same-prompt multi-model treatment as secondary factor only.
- Source: User instruction.
- Impact: Step 3 complete. `rq_version: 1.0` recorded in config.

### Decision 006
- Decision: Approved frozen metric policy with stage-separated validity reporting, executed-row denominators for primary detection metrics, separate execution-failure reporting, and pre-frozen-only unsupported/ambiguous exclusions.
- Source: User instruction.
- Impact: Step 4 complete. `research/METRICS_SPEC.md` frozen for downstream analysis and reporting.

### Decision 007
- Decision: Approved frozen statistical reporting plan with descriptive-first reporting, Wilson confidence intervals where appropriate, paired shared-row logic for F0/F1/F2, and exploratory-only hypothesis testing.
- Source: User instruction.
- Impact: Step 5 complete. `research/ANALYSIS_PLAN.md` frozen before requirement drafting.

### Decision 008
- Decision: Approved `requirements/requirements_v1.yaml` as the human-selected final Step 7 requirement set.
- Source: User instruction and created selection artifact.
- Impact: Step 7 complete. Step 8 obligation-checklist drafting proceeds from frozen requirement set.

### Decision 009
- Decision: Approved finalized Step 8 obligation checklist files under `requirements/obligation_checklists/FINAL/` as human-reviewed completion artifacts.
- Source: User instruction after completing Step 8 review.
- Impact: Step 8 complete. Step 9 provenance audit may begin.

### Decision 010
- Decision: Approved Step 11 F0/F1 semantic-equivalence review recorded in `requirements/formulation_equivalence.csv`.
- Source: User instruction after completing Step 11 review.
- Impact: Step 11 complete. Step 12 F2 generation may begin.
