# F5 Corpus Design

## Goal

Create a 14-requirement F5 corpus that tests difficult syntax and subtle semantic
changes while preserving human control over requirement selection and final answer
key validation.

## Source Of Truth

- Use `ic_sqits_guardrail_fidelity/requirements/requirements_v1.yaml` as the only
  semantic source of truth.
- Use F1-F4 formulations only as optional style references.
- Never resolve a conflict in favor of F1-F4 over F0.

## Selection Workflow

1. Build an 18-20 ID candidate shortlist from the 48 frozen requirements.
2. Favor negation, exceptions, compound conditions, `unless`/`only if`, and temporal
   ordering.
3. Show category, exact F0 wording, difficult-syntax tags, and selection rationale.
4. Recommend exactly 14 IDs, with at least two IDs from each category. Assign the
   remaining two positions to the strongest syntax cases.
5. Require human approval or replacement of the exact IDs before drafting F5.
6. Record the approved IDs in the Step 16 report draft.

## Variant Allocation

- Split approved IDs into seven semantics-preserving variants and seven near-miss
  variants.
- Keep allocation hidden from public F5 filenames and rows.
- Preserve variants may reorder clauses, front conditions, change voice, use an
  equivalent negative form, or embed an exception without changing meaning.
- Near-miss variants should introduce one realistic semantic shift, such as changed
  exception scope, weaker negation, altered Boolean grouping, moved temporal scope,
  or changed clause applicability.

## Files

Create only category files needed by selected rows under:

`ic_sqits_guardrail_fidelity/requirements/formulations/F5/`

Use existing neutral category filenames:

- `authorization_security.yaml`
- `data_protection_logging.yaml`
- `validation_input_constraints.yaml`
- `state_transitions_business_invariants.yaml`
- `reliability_idempotency.yaml`
- `observability_audit.yaml`

Each public row contains only:

- `requirement_id`
- `f0_text`
- `f5_text`

Create hidden answer key at:

`ic_sqits_guardrail_fidelity/requirements/formulations/F5/F5_ANSWER_KEY.md`

For every selected ID, record category, `preserve_semantics` or `near_miss`, syntax
focus, exact semantic change when applicable, and human review note.

Create report at:

`ic_sqits_guardrail_fidelity/reports/STEP_16_REPORT.md`

Report includes status, selected IDs, files created/modified, commands run, syntax
coverage, allocation counts, answer-key path, and human gate. Status remains
`PENDING_HUMAN_VALIDATION` until human validates answer key.

## Validation

- Selected count equals 14 and every ID exists in F0.
- Every selected ID appears in exactly one F5 row; no extra rows exist.
- Embedded F0 text exactly matches canonical F0.
- All F5 files parse as YAML.
- Answer key covers every F5 row exactly once.
- Public filenames and rows do not reveal allocation.
- Preserve and near-miss counts equal seven each.
- `git diff --check` passes.

## Human Gates

1. Human approves exact 14 IDs after reviewing shortlist.
2. Human validates hidden answer key after F5 drafting.
3. Step 16 becomes complete only after second gate.
