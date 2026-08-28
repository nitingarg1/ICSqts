# STEP_17_REPORT

- status: HUMAN_GATE_REQUIRED

## Files created

- `application/APPLICATION_SPEC.md`
- `reports/STEP_17_REPORT.md`

## Files modified

- none

## Commands run

- extracted runbook text from `IC_SQITS_2026_Exact_Experiment_Execution_Runbook_48_Steps.docx`
- read `README.md`
- read `requirements/requirements_v1.yaml`
- read all six `requirements/obligation_checklists/FINAL/*.yaml`
- read `requirements/formulation_equivalence.csv`
- read prior step reports for Phase C context
- run `git diff --check`

## Errors / failures

- none

## Draft summary

- Created `application/APPLICATION_SPEC.md` for Phase D Step 17.
- Defined minimal controlled payment-service benchmark surface needed to exercise the frozen 48-requirement corpus.
- Spec includes endpoints, entities, roles, payment and job state models, idempotency and replay behavior, audit/logging/metric surfaces, provider simulator behavior, persistent-state expectations, and unified error model.
- Added explicit requirement-to-surface mapping for all 48 frozen requirement IDs.
- Included deterministic control surfaces needed for expiry, retry, crash-recovery, and stale-lock scenarios without requiring external infrastructure.
- Included guardrail-block recording hook so later H/L0/L1 guardrails can execute against same application interface.

## Validation results

- `application/APPLICATION_SPEC.md` exists.
- All 48 requirement IDs from `requirements/requirements_v1.yaml` appear in the requirement-to-surface mapping table.
- Every mapping row references one or more observable surfaces documented in the spec.
- No external-provider dependency is required; all provider behavior is described as local deterministic simulation.
- `git diff --check` passes.

## Unresolved decisions

- Human must confirm that chosen payment/job/application surfaces are sufficient and not overbuilt relative to the frozen requirement corpus.
- Human should review implementation-constant interpretations for ambiguous source requirements, especially `R025`, `R027`, `R054`, and `R055`, before Step 18 implementation hardens them.

## Human gate required

- Yes. Step 17 is owned by agent draft plus human approval. Human must confirm all 48 requirements are exercisable from `application/APPLICATION_SPEC.md` before Step 18 begins.
