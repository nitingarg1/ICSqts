# Next-Experiment Design: From Deterministic Reference-Oracle Fidelity to Generated-Guardrail Fidelity

**Status:** DESIGN (runnable plan for a follow-up study)
**Companion to:** `final_results/PAPER_SUBMISSION.md` (the completed benchmark)
**Track relevance:** Trusted AI & Algorithmic Governance

---

## 1. Why a new experiment (not "more results" on the current one)

The current benchmark is at ceiling. Measured on the frozen 204-variant corpus:

- Precision 1.0000, Recall 0.9896, F1 0.9948, over-constraint 0.0000, execution-error 0.0000.
- Only 1 of 96 violating variants is missed (R013_M02), and that miss is **runtime-unobservable** (the primary sanitization layer still redacts the secret, so no behavior-only oracle can catch it without misfiring on the compliant reference).

Consequences:

- We cannot honestly "increase" recall on this corpus by tuning oracles: the one remaining miss has no observable runtime signature. Chasing it would break the zero-false-positive result.
- Perfect precision + zero over-constraint means there is no headroom on specificity either.

Therefore the honest path forward is a **new experiment that expands scope**, reusing the current frozen ground truth as a fixed, trusted measuring instrument. Three tracks below; they are independent and can run in any order.

---

## 2. Track A — Larger and deeper corpus

**Goal:** stress the measurement beyond the current 2-mutations-per-requirement, single-reference design.

**Changes:**
- Expand from 48 to a larger requirement set (target 80-120), keeping the six-category balance.
- Increase to 3-4 mutations per requirement, targeting a wider obligation set (current corpus: 96 mutations / 81 distinct obligations).
- Add a second, independently-authored reference implementation of the same requirements so a compliant behavior has *two* legitimate realizations, strengthening the over-constraint (specificity) measurement.

**Metrics:** unchanged formulas (precision, recall, F1, over-constraint, execution-error), plus per-obligation recall to expose which obligation classes are hardest.

**Harness reuse:** the existing `experiment/harness.py` classification and `experiment/metrics.py` recomputation stages are corpus-size-agnostic; only the variant generator and expected-verdict table grow.

**Success criteria:** stable precision/recall trends as corpus scales; identification of obligation classes where recall degrades; over-constraint remains measurable across two reference implementations.

---

## 3. Track B — Generated-guardrail fidelity (the RQ2/RQ4 study)

**Goal:** the current paper's guardrails are deterministic hand-authored oracles; RQ2 (paraphrase robustness) is NOT_EXERCISED and RQ4 (validation yield) is NOT_APPLICABLE. This track measures **generated** guardrails against the *same frozen ground truth*, turning the benchmark into a measuring instrument for a generation method.

**Conditions to compare (each generates a guardrail per requirement):**
- **H** — human-authored (baseline; the current oracles serve as one H reference).
- **L0** — direct generation from the requirement text.
- **L1** — generation via a structured obligation extraction step.
- **L2** — L1 plus an automated pre-acceptance validation stage.

**Method:** for each condition and requirement, produce a guardrail artifact, then run it through the *unchanged* harness against the 204 (or expanded) variants. Because ground truth is frozen and integrity-checked, every condition is scored on identical footing.

**Metrics (now answerable):**
- Generation fidelity: precision, recall, F1, over-constraint per condition.
- **Validation yield (RQ4):** fraction of flawed generated guardrails caught by the L2 stage before acceptance, and the L2 false-alarm rate on valid guardrails.
- **Paraphrase robustness (RQ2):** hold the requirement fixed, vary its wording across N equivalent formulations, and measure behavioral-agreement / divergence-rate across the paraphrases for the same condition.
- Generation-failure and execution-error rates per condition.

**Honesty constraints:** all generated artifacts and their raw request/response records must be preserved append-only; every reported number must recompute from raw with no model in the loop at scoring time; conditions frozen before generation; the human baseline frozen before inspecting generated errors.

**Success criteria:** a fair, reproducible comparison of H vs L0/L1/L2 fidelity, a real validation-yield number, and a real paraphrase-divergence number — none of which the current benchmark can claim.

---

## 4. Track C — Hybrid static + dynamic oracle

**Goal:** catch runtime-unobservable defects like R013_M02 (removed redundant secondary redaction whose absence never surfaces at runtime).

**Method:** augment each behavior-only oracle with a lightweight static/structural check for obligations whose enforcement is a defense-in-depth or code-structure property rather than an observable output. Re-run the full corpus and report the delta in recall attributable to the static layer, while confirming the static layer does not introduce false positives on the compliant reference(s).

**Metrics:** recall with/without the static layer; any new false positives; per-obligation attribution of which obligations *require* static checking.

**Success criteria:** recovery of the R013_M02-class miss with FP still 0; a principled delineation of which obligations are behavior-observable vs structure-only.

---

## 5. Shared infrastructure and guarantees

- **Frozen ground truth as instrument:** all tracks reuse the integrity-checked expected-verdict table; obligation references validated before any scoring.
- **Determinism:** fixed logical clock, seeded fixtures, no network, no model at scoring time — every number recomputes from the append-only raw log.
- **Provenance:** obligation -> mutation/variant -> expected verdict -> raw record -> reported number, end to end.
- **Verification:** extend the existing 15-test suite to cover new generators/corpus/integrity before any results are reported.

## 6. What this would let the follow-up paper claim (that this one cannot)

- Real generation-method fidelity comparison (H vs L0/L1/L2).
- A measured validation yield (RQ4) and paraphrase-robustness result (RQ2).
- Recall on runtime-unobservable obligations via a hybrid oracle.
- Scaling behavior of the fidelity measurement on a larger, multi-reference corpus.

All while preserving the current paper's honesty guarantees: benchmark-scoped, no population-level generalization, no fabricated numbers, and full raw-to-number reproducibility.
