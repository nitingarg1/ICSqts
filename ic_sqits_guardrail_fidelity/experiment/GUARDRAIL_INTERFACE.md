            # GUARDRAIL_INTERFACE

            STATUS: ASSUMPTION_BASED_DRAFT
Not protocol-valid final results.
Human-only and unfrozen later-phase decisions were filled under explicit user instruction to assume completion.
Use for package assembly and review only, not as protocol-valid final science.

            ## Contract

            - Study-level entrypoint: `evaluate(case: dict) -> dict`
            - Supported generator conditions: `H`, `L0`, `L1`, `L2`
            - Output contract must follow `experiment/schema/guardrail_result.schema.json`
            - Guardrails must not read hidden expected verdicts during execution.
            - App-local hook adaptation may map `FAIL` verdicts into request-block records, but study interface remains generator-agnostic.
