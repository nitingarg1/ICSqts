# REPRODUCIBILITY

STATUS: ASSUMPTION_BASED_DRAFT
Not protocol-valid final results.
Human-only and unfrozen later-phase decisions were filled under explicit user instruction to assume completion.
Use for package assembly and review only, not as protocol-valid final science.

This package assembles deterministic artifact counts and scaffold documentation only. It does not claim empirical guardrail-generation or execution results.

## Deterministic package regeneration

Run from repo root:

```bash
python3 -c "from experiment.assumption_package import write_assumption_artifacts; write_assumption_artifacts()"
```

Then verify tests and artifact counts with the commands used in this session.
