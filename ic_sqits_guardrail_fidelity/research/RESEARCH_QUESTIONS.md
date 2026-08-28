# RESEARCH_QUESTIONS

Date: 2026-08-27
Status: FROZEN

Human approval recorded: 2026-08-27

This file defines exact RQ wording for Step 3.
Novelty boundary source: `audit/PRIOR_WORK_BOUNDARY.md`

## RQ1

- Exact wording:
  When a guardrail is generated automatically from a selected machine-checkable software requirement, how often does it correctly encode all requirement-grounded machine-checkable obligations without omitting required checks or adding unsupported restrictions?
- Experimental unit:
  requirement x formulation x generator condition x generated guardrail
- Independent variables:
  requirement category; requirement formulation family; generator condition (`H`, `L0`, `L1`, `L2`); optional model identity if more than one model is frozen later
- Dependent variables:
  guardrail validity; semantic completeness; obligation omission count; over-constraint indicators; execution status
- Required raw data:
  canonical requirement text; formulation variant; frozen obligation checklist; raw guardrail output; compile/execute logs; per-obligation evaluation rows; expected verdict matrix links
- Planned metric(s):
  `guardrail_validity_rate`; `semantic_completeness`; `obligation_omission_rate`; `generation_failure_rate`; `execution_failure_rate`
- Required controls:
  human-authored reference guardrail; compliant implementation(s); controlled violating implementation(s); selected valid alternative(s); frozen obligation checklist approved by human
- Failure condition that would make RQ unanswerable:
  missing or unfrozen obligation checklist; no executable evaluation path for large share of rows; inability to map verdicts back to obligation-level evidence
- Overlap check against GAISS:
  Distinct. Does not study specification review gate, drift review, or developer-effort outcomes.
- Overlap check against ETECOM:
  Distinct. Does not ask what fraction of requirements are FE/PE/NE or where deterministic enforcement stops; asks whether generated guardrails faithfully encode already selected enforceable requirements.
- Same-prompt multi-model note:
  If multiple models are included, the same frozen prompt template, same requirement formulation, and same evaluation artifacts must be used across models. Model identity is a secondary factor, not a new primary research question.

## RQ2

- Exact wording:
  How stable is generated guardrail behavior when the same requirement is expressed through semantically equivalent paraphrases, clause-order permutations, and clarified wording that should preserve the same machine-checkable obligations?
- Experimental unit:
  requirement family x equivalent formulation pair/set x generator condition x shared implementation variant corpus
- Independent variables:
  formulation family (`F0`, `F1`, `F2`, `F3` where equivalence is frozen); generator condition; requirement category
- Dependent variables:
  paraphrase behavioral consistency; guardrail divergence; verdict-pattern differences across equivalent formulations
- Required raw data:
  frozen formulation corpus; human-approved equivalence labels; raw guardrails per formulation; implementation-level verdict rows; shared implementation IDs
- Planned metric(s):
  `paraphrase_behavioral_consistency`; `guardrail_divergence_rate`; per-family agreement counts
- Required controls:
  frozen F0/F1/F2 equivalence labels; shared implementation corpus across compared formulations; same execution harness and expected semantics
- Failure condition that would make RQ unanswerable:
  equivalence labels not frozen by human; compared formulations do not share common implementation corpus; execution failures dominate compared rows
- Overlap check against GAISS:
  Distinct. GAISS studied specification delivery and governance review, not paraphrase robustness of generated guardrails.
- Overlap check against ETECOM:
  Distinct. ETECOM used frozen requirement text for executable enforcement evaluation, not metamorphic wording stability of generated guardrails.
- Same-prompt multi-model note:
  Cross-model robustness may be analyzed only under identical frozen prompt templates and formulation sets. Any observed differences are generator-sensitivity findings, not standalone model ranking claims.

## RQ3

- Exact wording:
  How do LLM-generated guardrails compare with human-authored reference guardrails, and optionally conventional developer tests where available, in detecting controlled violations while avoiding false enforcement on compliant, valid-alternative, and boundary implementations?
- Experimental unit:
  requirement x generator/baseline condition x implementation variant evaluation
- Independent variables:
  guardrail condition (`H`, `L0`, `L1`, `L2`, optional developer-test baseline); implementation variant type (compliant, violating, valid alternative, boundary); requirement category
- Dependent variables:
  precision; recall; F1; over-constraint rate; attribution accuracy; validity status
- Required raw data:
  guardrail artifact; implementation variant ID and type; expected verdict; actual verdict; execution error rows; attribution fields if present
- Planned metric(s):
  `precision`; `recall`; `F1`; `over_constraint_rate`; `attribution_accuracy`; `guardrail_validity_rate`
- Required controls:
  human-authored reference guardrail for each requirement; compliant implementations; diverse violating variants; valid alternatives; selected boundary variants; frozen expected verdict matrix
- Failure condition that would make RQ unanswerable:
  no frozen expected verdict matrix; missing valid controls; insufficient violating diversity; invalid guardrails dominate baseline or comparison condition without separate reporting
- Overlap check against GAISS:
  Distinct. Does not compare document-vs-code governance workflow outcomes.
- Overlap check against ETECOM:
  Distinct but adjacent. Uses new comparative detection and false-enforcement design rather than ETECOM seeded challenge-response or enforcement-boundary counts.
- Same-prompt multi-model note:
  If model identity is included, comparisons must hold prompt version, formulation, expected verdict matrix, and execution harness constant across models. Report as conditional comparison, not universal superiority.

## RQ4

- Exact wording:
  Which semantic-fidelity failure modes occur most often in generated guardrails, and how effectively can structured extraction plus differential/metamorphic validation identify flawed guardrails before they are trusted?
- Experimental unit:
  flawed generated guardrail x frozen error label set x validation pipeline outcome
- Independent variables:
  generator condition; requirement category; formulation family; failure label category
- Dependent variables:
  failure-label frequency; validation yield; residual flawed guardrails that escape validation
- Required raw data:
  raw generated guardrails; frozen semantic-fidelity error taxonomy; human adjudication labels; validation decisions; per-guardrail acceptance/rejection outcome; evidence excerpts supporting labels
- Planned metric(s):
  `validation_yield`; failure-label frequency table; residual error counts by category
- Required controls:
  frozen error taxonomy; human-adjudicated flawed/non-flawed labels on eligible sample; preserved raw L0/L1 outputs; explicit validation decision log for L2
- Failure condition that would make RQ unanswerable:
  no frozen error taxonomy; no adjudicated flawed-guardrail labels; validation pipeline not preserved as explicit decision records
- Overlap check against GAISS:
  Distinct. GAISS did not analyze guardrail-generation semantic-failure taxonomy or validation yield.
- Overlap check against ETECOM:
  Distinct. ETECOM focused on executable requirement boundary and frozen challenge behavior, not generator failure taxonomy or pre-trust validation effectiveness.
- Same-prompt multi-model note:
  Failure-label distributions may be stratified by model only if the same frozen prompts and validation pipeline are used across models.

## Scope checks

- Requirement-enforceability coverage is not a primary RQ.
- FE/PE/NE prevalence is not a primary RQ.
- Enforcement-boundary claims remain prior-work context, not new dependent variables.
- All four RQs are intended to be answerable from frozen artifacts, execution logs, and human-approved checklists rather than model self-judgment.
- Same prompt across different models is allowed as a secondary independent variable under frozen settings.
- The study must not turn that secondary factor into a universal model-ranking claim unless design and sample size later justify it.
