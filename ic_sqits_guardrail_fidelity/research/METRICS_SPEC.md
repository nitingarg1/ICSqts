# METRICS_SPEC

Date: 2026-08-27
Status: FROZEN

Human approval recorded: 2026-08-27

This file freezes metric definitions before final generation.

## Global row types

- Generated guardrail row:
  one generated artifact for one `requirement x formulation x generator condition x replicate x model`
- Implementation evaluation row:
  one executed verdict for one `guardrail x implementation variant`
- Obligation evaluation row:
  one `guardrail x obligation` judgment using frozen checklist and evidence
- Equivalent-formulation comparison row:
  one paired comparison across two guardrails over shared implementation IDs
- Validation decision row:
  one decision by validation pipeline about one generated guardrail

## Global treatment rules

- Generation failures are preserved as generated-guardrail rows with missing executable artifact and `generation_status = failure`.
- Execution failures are preserved as implementation evaluation rows with `execution_status = error` and no silent retry.
- Unsupported or ambiguous semantic cases must be explicitly labeled in frozen artifacts; they are never converted into positive outcomes.
- Unless otherwise noted, metrics are first computed at row level, then aggregated by condition with raw counts reported alongside ratios.
- No denominator may exclude failures unless exclusion rule is written below.

## 1. guardrail_validity_rate

- Numerator:
  count of generated guardrail rows where guardrail executes successfully and satisfies predefined minimum control-validity rule
- Denominator:
  all generated guardrail rows
- Eligible rows:
  every generated guardrail row, including generation failures
- Excluded rows:
  none
- Treatment of execution errors:
  count as invalid in numerator; remain in denominator
- Treatment of unsupported/ambiguous cases:
  if guardrail cannot support required evaluation path, count invalid unless frozen rule marks requirement out of scope before generation
- Aggregation level:
  per generator condition, per formulation family, per requirement category, optional per model, overall
- Macro/micro averaging:
  micro on generated guardrail rows; macro summaries may be secondary if later needed

## 2. precision

- Numerator:
  implementation evaluation rows predicted violating where expected verdict is violating
- Denominator:
  implementation evaluation rows predicted violating
- Eligible rows:
  executed implementation evaluation rows with binary expected verdict in eligible comparison set
- Excluded rows:
  execution-error rows; rows explicitly frozen as unsupported/ambiguous; rows for invalid guardrails if human chooses stage-separated reporting
- Treatment of execution errors:
  excluded from precision denominator but counted separately in `execution_failure_rate`
- Treatment of unsupported/ambiguous cases:
  excluded if frozen as unsupported before analysis; otherwise not eligible
- Aggregation level:
  per guardrail condition; per requirement category; optional per model; overall
- Macro/micro averaging:
  primary micro over eligible rows; macro by requirement may be secondary

## 3. recall

- Numerator:
  implementation evaluation rows expected violating and predicted violating
- Denominator:
  implementation evaluation rows expected violating
- Eligible rows:
  executed rows with expected violating verdict in eligible comparison set
- Excluded rows:
  execution-error rows; frozen unsupported/ambiguous rows; rows removed by explicit pre-frozen exclusion rule only
- Treatment of execution errors:
  excluded from recall denominator but reported separately in `execution_failure_rate`
- Treatment of unsupported/ambiguous cases:
  excluded only if frozen as unsupported/ambiguous before analysis
- Aggregation level:
  per guardrail condition; per requirement category; optional per model; overall
- Macro/micro averaging:
  primary micro

## 4. F1

- Numerator:
  `2 * precision * recall`
- Denominator:
  `precision + recall`
- Eligible rows:
  same eligible rows as precision and recall
- Excluded rows:
  inherits precision/recall exclusions
- Treatment of execution errors:
  reflected through precision/recall exclusions and separately reported failure rates
- Treatment of unsupported/ambiguous cases:
  inherits precision/recall exclusions
- Aggregation level:
  computed from aggregated precision and recall for each reporting slice
- Macro/micro averaging:
  primary micro-derived F1

## 5. semantic_completeness

- Numerator:
  obligation evaluation rows judged correctly enforced
- Denominator:
  obligation evaluation rows required by frozen checklist
- Eligible rows:
  obligations for requirements with frozen checklist and executable evidence path
- Excluded rows:
  checklist items marked `AMBIGUOUS`; obligations lacking any frozen evidence path because requirement was removed before freeze
- Treatment of execution errors:
  if guardrail cannot execute needed obligation evidence path, obligation counts as not correctly enforced unless row is excluded by pre-frozen unsupported rule
- Treatment of unsupported/ambiguous cases:
  `AMBIGUOUS` obligations excluded from denominator; unsupported non-ambiguous obligations remain failures
- Aggregation level:
  per guardrail, per condition, per category, overall
- Macro/micro averaging:
  primary micro over obligations; macro by requirement secondary

## 6. obligation_omission_rate

- Numerator:
  obligation evaluation rows where required obligation is omitted or not meaningfully checked
- Denominator:
  obligation evaluation rows required by frozen checklist
- Eligible rows:
  same as `semantic_completeness`
- Excluded rows:
  same as `semantic_completeness`
- Treatment of execution errors:
  if execution prevents checking obligation, classify as omission only if adjudication shows obligation absent; otherwise handle under execution failure and not omission
- Treatment of unsupported/ambiguous cases:
  ambiguous checklist rows excluded; unsupported but non-ambiguous rows require explicit adjudication
- Aggregation level:
  per guardrail condition, per category, overall
- Macro/micro averaging:
  primary micro

## 7. over_constraint_rate

- Numerator:
  implementation evaluation rows for valid implementations predicted violating
- Denominator:
  implementation evaluation rows for valid implementations
- Eligible rows:
  compliant, valid-alternative, and human-approved valid boundary rows with executed verdicts
- Excluded rows:
  execution-error rows; rows frozen unsupported/ambiguous
- Treatment of execution errors:
  excluded from denominator, tracked separately
- Treatment of unsupported/ambiguous cases:
  excluded only if frozen before analysis; otherwise remain eligible
- Aggregation level:
  per guardrail condition; per variant type; per category; overall
- Macro/micro averaging:
  primary micro

## 8. paraphrase_behavioral_consistency

- Numerator:
  shared implementation evaluation rows where compared equivalent-formulation guardrails produce same verdict and that verdict matches frozen expected semantics
- Denominator:
  shared implementation evaluation rows across compared equivalent formulations
- Eligible rows:
  F0/F1/F2, and any F3 rows explicitly frozen as semantically equivalent; only shared implementation IDs with executed verdicts for both sides
- Excluded rows:
  non-equivalent formulation comparisons; missing-pair rows; execution-error pair rows; frozen unsupported/ambiguous rows
- Treatment of execution errors:
  pair excluded from denominator and counted in execution failure reporting
- Treatment of unsupported/ambiguous cases:
  excluded only if equivalence or expected semantics not frozen
- Aggregation level:
  per requirement family; per condition; optional per model; overall
- Macro/micro averaging:
  primary micro over shared comparisons; macro by requirement family secondary

## 9. guardrail_divergence_rate

- Numerator:
  equivalent requirement families where at least one eligible shared implementation row yields materially different expected-verdict pattern across compared equivalent formulations
- Denominator:
  equivalent requirement families with at least one eligible shared comparison set
- Eligible rows:
  requirement families with frozen equivalence labels and at least one executed shared comparison set
- Excluded rows:
  families lacking executed shared comparisons; frozen unsupported families
- Treatment of execution errors:
  if no eligible pair remains, family excluded; otherwise compute on remaining shared comparisons and report lost pairs separately
- Treatment of unsupported/ambiguous cases:
  families excluded only by pre-frozen rule
- Aggregation level:
  per generator condition; optional per model; overall
- Macro/micro averaging:
  family-level rate, not micro row rate

## 10. attribution_accuracy

- Numerator:
  detected violation rows correctly attributed to originating requirement
- Denominator:
  detected violation rows with attribution field present and expected attribution frozen
- Eligible rows:
  violating implementation evaluations where guardrail emits requirement-linked attribution and expected attribution exists
- Excluded rows:
  rows without attribution field by design; execution-error rows; non-detected rows
- Treatment of execution errors:
  excluded from denominator, reported separately
- Treatment of unsupported/ambiguous cases:
  excluded if expected attribution unavailable by pre-frozen design
- Aggregation level:
  per condition; per category; overall
- Macro/micro averaging:
  primary micro

## 11. validation_yield

- Numerator:
  flawed generated guardrail rows identified by validation pipeline before final acceptance
- Denominator:
  flawed generated guardrail rows in adjudicated sample eligible for validation
- Eligible rows:
  generated guardrails with human-adjudicated flawed/non-flawed label and explicit validation decision
- Excluded rows:
  no adjudication; no validation decision; generation failure rows if validation pipeline never receives artifact and rule excludes them
- Treatment of execution errors:
  execution-error guardrails remain eligible if validation pipeline had artifact and could flag flaw
- Treatment of unsupported/ambiguous cases:
  excluded only by pre-frozen adjudication rule
- Aggregation level:
  per validation condition; per category; optional per model; overall
- Macro/micro averaging:
  primary micro over flawed eligible guardrails

## 12. generation_failure_rate

- Numerator:
  generated guardrail rows where no usable artifact is produced under frozen settings
- Denominator:
  all generation attempts
- Eligible rows:
  every declared generation attempt
- Excluded rows:
  none
- Treatment of execution errors:
  not relevant
- Treatment of unsupported/ambiguous cases:
  not relevant unless failure is due to prompt refusing unsupported task, which still counts as generation failure unless pre-frozen exclusion exists
- Aggregation level:
  per condition; per formulation; optional per model; overall
- Macro/micro averaging:
  micro

## 13. execution_failure_rate

- Numerator:
  implementation evaluation rows ending in execution error or non-verdict outcome
- Denominator:
  all scheduled implementation evaluation rows for generated artifacts that reached execution stage
- Eligible rows:
  every scheduled execution row for artifacts that exist
- Excluded rows:
  generation-failure rows with no artifact; rows canceled by explicit pre-frozen exclusion rule
- Treatment of execution errors:
  counted in numerator
- Treatment of unsupported/ambiguous cases:
  if row is marked unsupported by pre-frozen rule, exclude; if not, non-verdict counts as execution failure
- Aggregation level:
  per condition; per variant type; optional per model; overall
- Macro/micro averaging:
  micro

## Human decisions required for freeze

1. Approved denominator rules for `precision`, `recall`, `F1`, and `over_constraint_rate`:
   - `precision`: executed eligible rows from valid guardrails where predicted verdict is violating.
   - `recall`: executed eligible rows from valid guardrails where expected verdict is violating.
   - `F1`: derived from frozen `precision` and `recall` values for same reporting slice.
   - `over_constraint_rate`: executed eligible rows from valid guardrails on valid implementations only (`compliant`, `valid_alternative`, and human-approved valid `boundary` rows).
2. Approved stage-separated reporting for invalid guardrails:
   - invalid guardrails remain in `guardrail_validity_rate`.
   - invalid guardrails do not remain inside primary detection denominators for `precision`, `recall`, `F1`, or `over_constraint_rate`.
3. Approved treatment of execution-error rows:
   - execution-error rows remain in `execution_failure_rate`.
   - execution-error rows are excluded from primary outcome denominators.
   - all primary outcome tables must report raw execution-error counts beside metric values.
4. Approved exclusion handling for unsupported/ambiguous cases:
   - exclude only if unsupported/ambiguous status was frozen before analysis.
   - `AMBIGUOUS` obligation rows are excluded from obligation-level semantic metrics.
   - unsupported but non-ambiguous rows count as failures unless an explicit pre-frozen exclusion rule marks them out of scope.
   - no post hoc exclusions are allowed.

## Frozen reporting policy summary

- `guardrail_validity_rate` is front-stage metric over all generated guardrail rows.
- `generation_failure_rate` is front-stage metric over all generation attempts.
- `execution_failure_rate` is front-stage metric over all scheduled execution rows for artifacts that reached execution.
- `precision`, `recall`, `F1`, and `over_constraint_rate` are conditional performance metrics computed only on rows that are from valid guardrails, executed to verdict, in frozen eligible comparison set, and not excluded by explicit pre-frozen unsupported/ambiguous rule.
- Every primary outcome table must report attrition counts, at minimum: total generated, valid, invalid, scheduled for execution, execution errors, and eligible executed rows used in denominator.
