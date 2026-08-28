# STEP_16_REPORT

- status: COMPLETE

## Selected IDs

- `R001`, `R003`, `R013`, `R016`, `R024`, `R026`, `R033`, `R036`, `R040`, `R042`, `R045`, `R047`, `R053`, `R057`

## Files created

- `requirements/F5_SELECTION_WORKING_NOTE.md`
- `requirements/formulations/F5/authorization_security.yaml`
- `requirements/formulations/F5/data_protection_logging.yaml`
- `requirements/formulations/F5/validation_input_constraints.yaml`
- `requirements/formulations/F5/state_transitions_business_invariants.yaml`
- `requirements/formulations/F5/reliability_idempotency.yaml`
- `requirements/formulations/F5/observability_audit.yaml`
- `requirements/formulations/F5/F5_ANSWER_KEY.md`

## Files modified

- `reports/STEP_16_REPORT.md`

## Commands run

- read `requirements/F5_SELECTION_WORKING_NOTE.md`
- read `requirements/requirements_v1.yaml`
- read `requirements/formulations/F5/*.yaml`
- read `requirements/formulations/F5/F5_ANSWER_KEY.md`
- run comprehensive Step 16 structural validation against
  `requirements/requirements_v1.yaml`
- run `git diff --check`

## Errors / failures

- none

## Difficult syntax coverage

- Selection-note syntax-tag counts: `negation` 8, `exception` 1,
  `compound_boolean` 11, `temporal_ordering` 9, `only_if` 4, and `until` 3.
- The hidden answer key provides a difficult-syntax description for all 14 selected
  requirements.
- Coverage includes negated identity and non-mutation, exception-path inclusion,
  changed exception and temporal scope, nested conjunction and XOR, only-if
  admissibility, universal field quantification, aggregate thresholds, request-pair
  relations, attempt and worker cardinality, event selection, and interval-scoped
  suppression.

## Allocation counts

- `preserve_semantics`: 7
- `near_miss`: 7

## Validation results

- Selection status is `APPROVED_BY_HUMAN`; first human selection gate passed on
  2026-08-28.
- Answer-key status is `approved`; second human answer-key validation gate passed on
  2026-08-28 after post-review corrections to R026, R036, R047, and R053.
- The selected list contains exactly the 14 approved IDs, with no duplicates.
- All 14 approved IDs exist in canonical `requirements/requirements_v1.yaml`.
- Each approved ID appears in exactly one public F5 row; no extra rows exist.
- All six expected public F5 YAML files parse successfully.
- Every public row has exactly `requirement_id`, `f0_text`, and `f5_text`.
- Embedded F0 text exactly matches canonical F0 for all 14 rows.
- Public metadata has the correct date, review status, formulation family, category,
  and canonical source path in every file.
- Public filenames are neutral, and public rows contain no classification fields.
- The hidden answer key has exact ID parity with the public corpus, one entry per ID,
  canonical category parity, all required review fields, and a 7/7 classification
  split.
- `git diff --check` passes.

## Hidden answer key

- `requirements/formulations/F5/F5_ANSWER_KEY.md`

## Human gates

- First selection gate: passed on 2026-08-28; the exact 14-requirement selection
  remains recorded as `APPROVED_BY_HUMAN`.
- Second answer-key validation gate: passed on 2026-08-28 after post-review
  corrections to R026, R036, R047, and R053 were reviewed and approved by human.
