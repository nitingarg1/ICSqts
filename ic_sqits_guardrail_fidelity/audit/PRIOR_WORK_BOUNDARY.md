# PRIOR_WORK_BOUNDARY

Date: 2026-08-27
Status: HUMAN_REVIEW_REQUIRED

## Sources reviewed

- `inputs/GAISS_FINAL.docx`
- `inputs/ETECOM_IEEE_ETECOM_2026_FINAL_MERGED_3AUTHORS_v2.docx`
- `inputs/IC_SQITS_FIRST_DRAFT.md`

## Overlap audit table

| Item | GAISS | ETECOM | IC-SQITS proposed use | Reuse allowed? | Citation required? | Overlap risk | Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Research questions | Specification-driven governance, drift, review effort, delivery mode of specification | FE/PE/NE enforceability, frozen guardrails, detection and boundary to policy/context | Semantic fidelity and robustness of generated guardrails; paraphrase stability; failure taxonomy for guardrail synthesis | No reuse of prior RQ results; only thematic progression | Yes | Medium | Keep IC-SQITS RQ1-RQ4 centered on guardrail semantic fidelity, robustness, detection comparison, and validation yield |
| Contributions | Governance framework, review gate, document-vs-code drift loop, controlled studies on specification delivery | FE/PE/NE taxonomy, requirement-to-guardrail lineage, frozen challenge protocol, traceability and boundary analysis | New contribution must be trustworthiness of guardrail-generation process itself | No direct reuse as new contribution | Yes | High | Explicitly state IC-SQITS starts after requirement selected for executable enforcement |
| Datasets / corpora | Case study plus controlled studies on AI-assisted software engineering tasks | Synthetic 145-requirement benchmark across eight services; 30 frozen challenge requirements; 20 public-source sample | New requirement corpus for guardrail-fidelity study; reused requirements only as labeled seeds if used later | Seed inputs only, not outcomes | Yes | High | Any reused requirement must be marked `REUSED_SEED` with provenance; no prior counts reused |
| Requirement taxonomies | Risk taxonomy for governance gaps and lifecycle control points | FE/PE/NE codebook and executable category structure | Obligation-level semantic-fidelity error taxonomy and metamorphic consistency framing | Conceptual inspiration only | Yes | High | Do not report FE/PE/NE prevalence as IC-SQITS result; freeze new error taxonomy later |
| Benchmark applications | Premium-payment governance case and controlled coding tasks | Requirement-and-evidence evaluation fixtures across multiple services | Compact application for guardrail synthesis evaluation with compliant, violating, valid-alternative, and boundary implementations | New implementation artifacts only | Yes | Medium | New or independently versioned application artifacts required |
| Guardrail generation | Not main unit of analysis; governance of generated code/spec workflow | Deterministic frozen guardrails generated from classified requirements | Main unit of analysis is generated guardrail behavior under H, L0, L1, L2 conditions | No reuse of frozen ETECOM guardrails as IC-SQITS evidence | Yes | High | Generate entirely new IC-SQITS guardrails and preserve raw outputs |
| Mutations / challenges | Not central empirical mechanism | Structurally blinded seeded challenge mutations and valid controls | New implementation-variant matrix with violation diversity, paraphrase families, valid alternatives, and boundary cases | Reuse only as inspiration for protocol design | Yes | High | No reuse of ETECOM 90 challenge outcomes or mutation verdicts |
| Metrics | Quality, drift, effort, delivery-mode effects | Coverage, challenge response, false positives, traceability, applicability sample | Guardrail validity, semantic completeness, over-constraint, paraphrase consistency, divergence rate, attribution accuracy, validation yield | No prior metric values reusable | Yes | High | Keep new dependent variable on semantic fidelity and robustness |
| Human review | Human review gate and human reconciliation central | Human approval of codebook, checklists, verdicts, freezes | Human-authored reference guardrails and adjudication of semantic fidelity | Process pattern only | Yes | Medium | Preserve human-only ground truth checkpoints; do not replace human semantic authority |
| Traceability | Specification as governance artifact and drift accountability | Stable requirement identity across classification, guardrail, mutation, evidence | Requirement attribution correctness for generated guardrails and validation artifacts | Conceptual lineage yes; prior traceability outcomes no | Yes | Medium | Recompute all traceability evidence from new IC-SQITS runs only |
| Enforcement-boundary claims | Not core claim | Deterministic boundary between executable checks and unresolved policy/context semantics | Mention only as prior-work boundary; not new IC-SQITS evidence | No | Yes | High | IC-SQITS must not claim ETECOM boundary findings as new |
| Figures / tables | Governance-loop figures and controlled-study tables | FE/PE/NE architecture, coverage tables, challenge tables, applicability tables | New figures/tables only for guardrail-fidelity experiment | No direct reuse | Yes | High | Redraw only if scientifically necessary and with new content, not reused structure or counts |
| Wording likely to overlap | Phrases around specification as governance artifact, review gate, drift loop | Phrases around frozen guardrails, enforcement boundary, requirement identity | Manuscript must use fresh wording and cite prior work where conceptual lineage exists | Limited paraphrase with citation only | Yes | High | Rewrite all summary language from scratch and avoid sentence-level reuse |

## What IC-SQITS must NOT claim as new

1. GAISS results about specification review gates, specification delivery mode, developer effort, or document-versus-code drift as if newly observed in IC-SQITS.
2. ETECOM results about FE/PE/NE prevalence, frozen guardrail challenge response, valid-control rejection rates, traceability counts, or policy/context enforcement boundaries as if newly observed in IC-SQITS.
3. Any statement that IC-SQITS newly proves requirements are executable in general.
4. Any claim that prior figures, tables, or benchmark counts belong to the IC-SQITS experiment.

## Artifacts that may be reused only as seed inputs

1. Selected prior-study requirements, if later marked `REUSED_SEED` with provenance.
2. Conceptual protocol ideas such as frozen artifacts, human gates, traceability discipline, and reproducibility controls.
3. Prior papers as literature and novelty-boundary sources.

## Artifacts that must be generated entirely new

1. IC-SQITS requirement-selection set and provenance records for this study.
2. Requirement formulation families F0-F5 and equivalence labels.
3. Human reference guardrails for IC-SQITS evaluation.
4. L0, L1, and L2 generated guardrails and all raw outputs.
5. Implementation variants, expected verdict matrix, execution logs, processed metrics, and final verified results.
6. Semantic-fidelity failure labels and validation-yield outcomes.
7. All paper Results narrative and all numbers reported as IC-SQITS evidence.

## Originality boundary

GAISS established specification-driven governance for human review of AI-generated code, and ETECOM established requirement-to-guardrail enforceability with frozen executable controls and explicit enforcement boundaries. IC-SQITS begins one stage later: given a requirement chosen for executable enforcement, can automatically generated guardrails be trusted to preserve requirement meaning, stay behaviorally stable across equivalent wording, detect violations without unsupported restrictions, and expose failure modes before trust is granted? The new dependent variable is guardrail semantic fidelity and robustness. Prior studies may be cited for lineage and may provide labeled seed inputs only, but none of their empirical outcomes may be reused as IC-SQITS results.
