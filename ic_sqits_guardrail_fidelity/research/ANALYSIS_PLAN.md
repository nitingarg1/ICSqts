# ANALYSIS_PLAN

Date: 2026-08-27
Status: FROZEN

Human approval recorded: 2026-08-27

This file freezes statistical and descriptive reporting rules before final generation.
It must remain aligned with:
- `research/RESEARCH_QUESTIONS.md`
- `research/METRICS_SPEC.md`

## 1. Reporting principles

- Primary reporting is descriptive first.
- Every reported ratio must be accompanied by raw numerator and denominator counts.
- Every reported ratio must be traceable to frozen raw artifacts and processed row IDs.
- No analysis choice may depend on whether a result appears favorable or statistically significant.
- Invalid guardrails and execution failures must be reported explicitly and not hidden inside primary detection metrics.
- Category-level and condition-level breakdowns are required wherever denominator size is non-trivial.
- If a denominator is too small for stable interpretation, report counts and caveat rather than over-interpret.

## 2. Primary reporting units

- Generated-guardrail row for validity and generation outcomes.
- Implementation evaluation row for detection and over-constraint outcomes.
- Obligation evaluation row for semantic completeness and omission outcomes.
- Equivalent-formulation shared comparison row for paraphrase consistency.
- Requirement family for family-level divergence reporting.
- Validation decision row for validation-yield reporting.

## 3. Descriptive statistics to report

For each applicable metric, report:
- numerator
- denominator
- proportion or rate
- reporting slice: overall, by guardrail condition, by requirement category, and optional by frozen model identity

Required descriptive outputs:
- `guardrail_validity_rate`
- `generation_failure_rate`
- `execution_failure_rate`
- `semantic_completeness`
- `obligation_omission_rate`
- `precision`
- `recall`
- `F1`
- `over_constraint_rate`
- `paraphrase_behavioral_consistency`
- `guardrail_divergence_rate`
- `attribution_accuracy`
- `validation_yield`

Required count tables:
- total generation attempts by condition
- valid vs invalid generated guardrails by condition
- scheduled execution rows, executed verdict rows, and execution-error rows by condition
- eligible denominator counts for each primary metric by condition
- requirement counts by category
- formulation family counts (`F0`, `F1`, `F2`, frozen-equivalent `F3` if used)
- implementation variant counts by type (`compliant`, `violating`, `valid_alternative`, `boundary`)
- failure-label counts for RQ4 taxonomy

## 4. Confidence intervals

- For proportions/rates, report 95% confidence intervals where denominator is meaningful and interval computation is stable.
- Default interval for binomial proportions: Wilson score interval.
- For rates based on very small denominators, raw counts remain primary and intervals are optional secondary annotations.
- Do not report confidence intervals for derived quantities when denominator is too small to support meaningful interpretation.
- `F1` may be reported without a confidence interval if no pre-frozen resampling method is implemented; if interval is later added, it must be added by deterministic pre-frozen script and applied uniformly across compared conditions.

## 5. Paired comparison logic for F0/F1/F2

- Pairing unit is frozen shared implementation evaluation row under same requirement family, same implementation ID, same guardrail condition, and same execution harness.
- `paraphrase_behavioral_consistency` is computed on shared eligible executed rows only, as frozen in `METRICS_SPEC.md`.
- `guardrail_divergence_rate` is computed at requirement-family level: a family is divergent if at least one eligible shared comparison yields materially different expected-verdict behavior across equivalent formulations.
- Report for each family:
  - number of eligible shared comparisons
  - number of agreement rows
  - number of disagreement rows
  - whether family is marked divergent
- Missing pairs and execution-error pairs are not silently imputed; they are reported as lost comparisons.

## 6. Human-vs-LLM comparison logic

- Main comparison conditions are frozen in the experiment design, expected to include `H`, `L0`, `L1`, and `L2`; optional developer-test baseline may be included only if frozen before generation.
- Human-authored reference guardrails are treated as comparison baseline, not infallible semantic oracle outside frozen checklists and expected verdict matrices.
- Compare conditions using the same frozen requirement set, implementation corpus, expected verdict matrix, and metric denominators.
- Primary comparison outputs are side-by-side descriptive metrics and raw counts, not narrative superiority claims.
- If model identity is included as secondary factor, it must be reported as conditional under same frozen prompt and execution settings.

## 7. Hypothesis tests

- Primary study claims are descriptive, not inferential.
- No hypothesis test is required for the main paper claims if the final corpus remains a controlled, finite, non-probability benchmark.
- Hypothesis tests may be reported only as explicitly labeled exploratory analyses if all of the following hold:
  - paired structure is valid for the comparison,
  - denominator size is adequate,
  - test choice is justified by data structure rather than result direction,
  - multiple-comparison handling is pre-declared and applied uniformly.
- If exploratory paired binary-comparison testing is later used, the default pre-declared choice is McNemar's test for matched verdict outcomes on the same eligible rows.
- If these conditions are not met, report descriptive differences and confidence intervals only.

## 8. Multiple-comparison handling

- No multiple-comparison correction is needed for primary descriptive reporting.
- If exploratory hypothesis tests are run across multiple conditions, categories, or metric families, control false discoveries with Holm correction within each declared test family.
- The declared family must be fixed before running tests and may not be redefined after seeing outcomes.

## 9. Category-level reporting

- Report all major primary metrics by requirement category:
  - authorization/security
  - data protection/logging
  - validation/input constraints
  - state transitions/business invariants
  - reliability/idempotency
  - observability/audit
- Category tables must include raw counts before ratios.
- If a category has too few eligible rows for a stable ratio, report counts and mark the estimate as low-sample.

## 10. Minimum sample-size caveats

- No universal minimum denominator will be invented after the fact.
- If denominator is less than 10 for a reported slice, treat the ratio as unstable and foreground counts.
- If denominator is less than 5 for a reported slice, ratio may still be shown for completeness but should not support comparative claims.
- If too few eligible pairs remain for paraphrase or paired comparison slices, report only counts and representative failure evidence.
- If too few adjudicated flawed guardrails exist for a validation-yield slice, report raw counts and avoid strong comparative conclusions.

## 11. Required tables and figure families

- Attrition table from generation to eligible evaluation rows.
- RQ1 table: validity, generation failure, execution failure, semantic completeness, omission rate.
- RQ2 table: shared pair counts, paraphrase consistency, divergence rate, lost-pair counts.
- RQ3 table: precision, recall, F1, over-constraint, attribution accuracy, with denominators and failure counts.
- RQ4 table: failure-label frequencies, validation yield, residual flawed guardrails escaping validation.
- Category-level appendix tables with same metric definitions.

## 12. Reporting restrictions

- Do not claim population prevalence beyond frozen benchmark.
- Do not claim universal model superiority from conditional comparisons.
- Do not claim statistical significance unless a pre-declared exploratory test is actually run and assumptions are met.
- Do not suppress rows, categories, or failed conditions because denominators are inconvenient.
- Do not convert execution failures or unsupported cases into favorable outcomes.

## Human gate checklist

- Approve descriptive-first reporting as primary analysis mode.
- Approve Wilson 95% confidence intervals for eligible proportion metrics where appropriate.
- Approve paired shared-row logic for F0/F1/F2 comparisons.
- Approve side-by-side human-vs-LLM descriptive comparison without automatic superiority claims.
- Approve that hypothesis tests are optional exploratory analyses only, with McNemar + Holm as pre-declared default if later justified.
- Approve low-sample caveats for denominators below 10 and stronger caution below 5.
