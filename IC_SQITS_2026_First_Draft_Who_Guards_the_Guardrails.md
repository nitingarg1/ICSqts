# Who Guards the Guardrails? Evaluating Semantic Fidelity and Robustness of LLM-Generated Security Controls for AI-Written Software

**Anonymous submission — first research draft**

## AUTHORING NOTE — REMOVE BEFORE SUBMISSION

This is a research-first manuscript draft. No experimental results have been invented. Every bracketed field marked [RESULT TO INSERT], [N], [MODEL], or [REFERENCE TO VERIFY] must be replaced only after the corresponding experiment or literature check is complete.

Novelty boundary: this paper is intentionally designed to be distinct from two prior studies. The GAISS work studies specifications as governance artifacts for human–AI oversight, including specification-anchored versus code-only review and requirement attribution. The ETECOM work studies requirement enforceability, FE/PE/NE classification, frozen executable guardrails, seeded challenges, and the requirement–enforcement boundary. This IC-SQITS paper instead evaluates the trustworthiness of the guardrail-generation process itself: whether automatically generated guardrails preserve requirement meaning, remain behaviorally stable under semantically equivalent wording changes, and detect violations without introducing new false enforcement.

The intended IC-SQITS positioning is Trusted AI & Algorithmic Governance with a strong secondary connection to AI-Driven Cybersecurity & Threat Detection. The paper should remain anonymized for double-blind submission.

## Abstract

AI-assisted development increasingly relies on machine-generated code as well as machine-generated tests, policies, and enforcement logic. This creates a recursive trust problem: if a large language model generates the guardrail used to judge another generated artifact, who verifies that the guardrail itself faithfully represents the governing requirement? A syntactically valid test or policy can silently under-constrain, over-constrain, or misinterpret the requirement it is intended to enforce.

This paper introduces a controlled methodology for evaluating the semantic fidelity and robustness of LLM-generated executable guardrails for security- and reliability-sensitive software requirements. The study compares human-authored guardrails with LLM-generated guardrails under multiple requirement presentations, including canonical wording, semantically equivalent paraphrases, clarified versions, and deliberately underspecified variants. Guardrails are evaluated against compliant implementations, controlled requirement violations, and adversarially chosen boundary cases. In addition to precision and recall, we measure guardrail validity, semantic-fidelity error classes, paraphrase consistency, behavioral equivalence, and requirement-attribution correctness.

Across [N] requirements and [N] generated guardrails, [RESULT TO INSERT]. The intended contribution is not another claim that natural-language requirements are executable. Instead, the study asks whether the automation that creates executable controls is itself trustworthy, and identifies when human validation, differential testing, or explicit semantic escalation remains necessary.

## Keywords

trusted AI; AI-generated code; executable guardrails; semantic fidelity; LLM-generated tests; security assurance; metamorphic testing; algorithmic governance

## 1. Introduction

Generative AI is beginning to automate not only software implementation but also the mechanisms used to validate that implementation. Coding assistants can generate unit tests, static-analysis rules, policy checks, assertions, and runtime monitors from natural-language requirements. This can reduce the cost of converting written intent into executable assurance. It also creates a second-order reliability problem: the enforcement artifact may be wrong even when the implementation being checked is correct.

Consider the requirement: “A caller without the PAYMENT_APPROVER role must not approve a payment, and a rejected attempt must not modify payment state.” An LLM can readily generate an executable test for this sentence. Yet several subtly incorrect tests also look plausible: one may assert only that an HTTP 403 is returned while ignoring state mutation; another may test the wrong role; another may treat any non-200 response as sufficient; and another may accidentally exercise a route that never reaches the approval logic. A passing guardrail can therefore create false confidence if the guardrail does not preserve the semantics of the requirement.

This problem becomes more important as organizations adopt specification-driven and policy-driven workflows for AI-assisted development. Prior work has shown the value of explicit specifications for governance and traceability, while executable-guardrail research has explored which parts of a requirement can be mapped to deterministic evidence. Those results leave a separate question unresolved: if guardrails are synthesized automatically, how reliable is the synthesis step itself?

The distinction matters for trusted AI. A trustworthy development pipeline cannot assume that a model-generated verifier is correct merely because it compiles or because it detects one seeded defect. The verifier should be challenged independently, including with compliant alternatives, multiple violation forms, semantically equivalent requirement wording, and cases near the boundary of the stated requirement.

We therefore study guardrail generation as a system under test. The central research question is not whether requirements can be executable, but whether automatically generated enforcement preserves the intended semantics consistently enough to be trusted.

We make four intended contributions. First, we define a semantic-fidelity evaluation model for executable guardrails that separates syntactic validity from behavioral correctness. Second, we introduce a paraphrase-based metamorphic test for guardrail synthesis: semantically equivalent requirements should produce behaviorally equivalent enforcement even when generated code differs. Third, we compare human-authored and LLM-generated guardrails against compliant, violating, and boundary implementations. Fourth, we characterize guardrail-generation failure modes such as under-constraint, over-constraint, wrong-observable selection, exception loss, and state-effect omission.

## 2. Relationship to Prior Work and Novelty Boundary

This paper is deliberately positioned after, rather than as a rewrite of, two earlier studies.

Prior Study A examined specifications as governance artifacts for AI-generated software. Its primary concern was human–AI collaboration: whether an approved specification changes drift review, attribution, confidence, accountability, and review effort. The specification served as a shared review baseline. The current study does not repeat that human-review experiment and does not claim a new result about specification-anchored review.

Prior Study B moved from review artifacts toward executable enforcement. It classified requirements by enforceability, generated frozen guardrails, exercised controlled challenge variants, preserved requirement identity, and characterized the boundary between deterministic evidence and unresolved policy or human judgment. The current study does not re-estimate FE/PE/NE prevalence, does not reuse the prior challenge outcomes as new evidence, and does not treat the requirement–enforcement boundary as its primary contribution.

The current paper begins one step later in the pipeline. It assumes that a requirement has already been selected as suitable for executable enforcement and asks whether the automatically generated enforcement is semantically faithful. Its unit of analysis is therefore the generated guardrail and its behavior across requirement formulations and implementation variants, rather than the requirement classification itself.

This separation is essential for originality. The new experiment will use new generation runs, a new evaluation matrix, new dependent variables, and a new failure taxonomy. Reused requirements, if any, will be explicitly labeled and will serve only as seed inputs; none of the earlier experimental outcomes will be reused as results.

## 3. Research Questions

RQ1 — Guardrail validity and semantic fidelity: When a guardrail is generated automatically from an enforceable software requirement, how often does it correctly encode all machine-checkable obligations in that requirement?

RQ2 — Robustness to equivalent wording: How stable is guardrail behavior when the same requirement is expressed using semantically equivalent paraphrases, reordered clauses, or clarified wording?

RQ3 — Detection effectiveness: How do LLM-generated guardrails compare with human-authored guardrails and conventional developer tests when evaluated against compliant implementations, controlled violations, and boundary cases?

RQ4 — Failure modes and validation: Which guardrail-generation errors occur most frequently, and how effectively can differential or metamorphic validation identify them before the guardrail is trusted?

## 4. Conceptual Model

A requirement-to-guardrail pipeline contains at least two independently fallible transformations: interpretation and implementation. The model must first infer what evidence is relevant to the requirement and then encode a decision procedure over that evidence. Errors at either step may remain invisible if evaluation checks only whether the generated artifact compiles.

We therefore distinguish four levels of guardrail quality. (1) Syntactic validity: the artifact parses, compiles, or executes. (2) Control validity: it passes a known compliant case and rejects at least one known violating case. (3) Semantic fidelity: it evaluates every machine-checkable obligation in the requirement without adding unsupported restrictions. (4) Robustness: equivalent requirement formulations lead to materially equivalent enforcement behavior.

The proposed trust model treats levels (3) and (4) as the main research targets. A guardrail that merely compiles is not trustworthy, and a guardrail that detects one seeded violation may still be incomplete or over-constrained.

## 4.1 Semantic-Fidelity Error Taxonomy

The study will use a frozen error taxonomy before final execution. Candidate categories are: OBLIGATION_OMISSION, where one required clause is not checked; WRONG_OBSERVABLE, where the guardrail inspects evidence that does not establish the requirement; OVER_CONSTRAINT, where valid behavior is incorrectly rejected; EXCEPTION_LOSS, where a documented exception is ignored; STATE_EFFECT_OMISSION, where response behavior is checked but resulting state is not; ACTOR_OR_SCOPE_CONFUSION, where the wrong role, resource, endpoint, or operation is tested; WEAK_PROXY, where a superficial proxy is treated as evidence of compliance; and NON_EXECUTABLE_OR_BROKEN, where the generated control cannot run.

The taxonomy will be frozen before the final generation campaign. Post-hoc categories may be added only as separately labeled exploratory findings.

## 4.2 Metamorphic Consistency

For a semantically equivalent set of requirement formulations R = {r1, r2, ..., rk}, the generated guardrails need not be textually identical. They should, however, produce the same verdict over a shared implementation corpus whenever the formulations preserve the same obligations.

We define behavioral consistency between two guardrails gi and gj over implementation set I as the proportion of implementations for which both produce the same semantically valid verdict. Text similarity is not used as the primary measure because independently written tests may be behaviorally equivalent despite different code structure.

A large drop in behavioral consistency across equivalent paraphrases indicates sensitivity to wording rather than requirement semantics. This is treated as a trustworthiness failure even if each individual guardrail appears plausible in isolation.

## 5. Experimental Method

The experiment is designed as a controlled guardrail-synthesis study. The primary experimental unit is requirement × formulation × generator × guardrail × implementation variant.

The final protocol will be frozen before collecting reported results. Generation prompts, model identifiers, decoding parameters, requirement formulations, implementation variants, human reference guardrails, and evaluation scripts will be versioned and preserved.

## 5.1 Requirement Corpus

Target corpus: approximately 40–60 requirements, with emphasis on security, authorization, data protection, reliability, observability, and state-transition properties. Requirements should be drawn from three sources: publicly grounded security/engineering guidance; newly created benchmark requirements for the controlled application; and a small, explicitly labeled subset of prior-study requirements where reuse is scientifically useful.

The new corpus should not simply reproduce the ETECOM FE/PE/NE benchmark. Inclusion criteria for this study are narrower: each selected requirement must have at least one machine-checkable core so that guardrail fidelity can be evaluated. Requirements whose primary purpose is to measure the enforceability boundary are not the focus here.

## 5.2 Requirement Formulations

Each canonical requirement will be transformed into a controlled family of formulations. Proposed variants are: F0 canonical wording; F1 semantically equivalent paraphrase; F2 clause-order permutation; F3 clarified wording with explicit actor/action/effect; F4 mildly underspecified wording; and, for selected requirements, F5 exception-bearing or negation-sensitive wording.

F1 and F2 are metamorphic-equivalence variants: their correct enforcement behavior should remain equivalent to F0. F3 tests whether explicitness improves guardrail quality. F4 and F5 test sensitivity to missing or difficult semantics and should be analyzed separately rather than folded into equivalence consistency.

## 5.3 Benchmark Application and Implementation Variants

A compact service-oriented application will provide observable behaviors for the selected requirements. A payment/approval workflow remains a useful domain because it naturally exposes authorization, idempotency, audit, logging, validation, and state-transition requirements, but the implementation and experiment corpus for this paper must be newly generated or independently versioned rather than treated as the prior ETECOM benchmark.

For each requirement, the evaluation set should contain: at least one compliant reference implementation; multiple controlled violating variants targeting different parts of the requirement; at least one valid alternative implementation where practical; and selected boundary variants designed to reveal over-constraint or weak-proxy behavior.

The key methodological improvement over a single-mutation test is violation diversity. A guardrail that detects only the exact defect shape used during its creation is not necessarily semantically faithful.

## 5.4 Guardrail Generators and Baselines

We propose four comparison conditions. H — human-authored reference guardrail, created from the canonical requirement before LLM outputs are inspected. L0 — direct LLM synthesis from the natural-language requirement. L1 — structured synthesis in which the model first extracts actor, action, condition, expected outcome, state effects, evidence, and exceptions before generating enforcement. L2 — L1 plus differential/metamorphic validation across multiple requirement formulations.

A conventional developer-test baseline may be included for a subset of requirements to distinguish requirement-faithful guardrails from ordinary tests written only from implementation intuition.

If multiple models are used, model identity becomes a factor rather than a claim of universal model superiority. The study should avoid ranking models unless the experimental design and sample size support that inference.

## 5.5 Human Reference and Adjudication

Human-authored guardrails serve as a reference implementation of the intended machine-checkable requirement, not as unquestionable ground truth. Before final execution, each human guardrail must pass predefined compliant and violating controls.

Semantic-fidelity adjudication should be performed using a requirement-level checklist derived before generation. For example, an authorization requirement may require checking actor role, operation, response, and state mutation. A generated guardrail is incomplete if it omits any mandatory observable that is necessary to establish the requirement.

Where possible, a second reviewer should independently assess a stratified sample of guardrails and disagreements should be resolved using the frozen requirement checklist. Inter-rater agreement should be reported if the sample size permits.

## 5.6 Execution Protocol

For every requirement formulation and generator condition: (1) generate the guardrail once under frozen settings or according to a predeclared number of replicates; (2) preserve the raw output; (3) record compilation/execution failures without silently repairing them; (4) execute the guardrail against the full implementation-variant set; (5) record pass/fail/error and requirement attribution; and (6) compare behavioral outcomes with the predefined expected verdict matrix.

No generated guardrail may be modified after observing final evaluation outcomes. If a repair experiment is desired, it must be run as a separate, explicitly labeled condition.

## 6. Metrics

Guardrail validity rate = valid executable guardrails / generated guardrails. A valid guardrail must at minimum execute successfully and satisfy predefined positive and negative controls.

Violation-detection precision, recall, and F1 will be computed over implementation variants with predefined ground truth. Counts will always accompany ratios.

Semantic completeness = correctly enforced machine-checkable obligations / required machine-checkable obligations for a requirement. This metric requires the frozen obligation checklist.

Over-constraint rate = valid implementations incorrectly rejected / valid implementation evaluations.

Paraphrase behavioral consistency = agreement of semantically equivalent guardrails over the shared implementation corpus, conditioned on the expected semantics being equivalent.

Guardrail divergence rate = proportion of equivalent requirement families for which at least one generated guardrail produces a materially different expected-verdict pattern.

Attribution accuracy = detected violations correctly associated with the originating requirement / detected violations, if requirement-linked evidence is part of the generated artifact.

Validation yield = proportion of flawed generated guardrails identified by the proposed differential/metamorphic validation procedure before final acceptance.

## 7. Planned Results Structure

This section must remain empty of empirical claims until the experiment is executed.

7.1 RQ1 — Guardrail validity and semantic fidelity. Report [N] generated artifacts, compile/execute success, control validity, obligation-completeness distribution, and error categories.

7.2 RQ2 — Paraphrase robustness. Report behavioral consistency across F0/F1/F2, the number of requirement families with divergent enforcement, and representative semantic-sensitive failures.

7.3 RQ3 — Detection effectiveness. Compare H, L0, L1, and L2 on precision, recall, F1, over-constraint, and boundary cases. Avoid superiority language unless justified by the design.

7.4 RQ4 — Failure modes and validation. Report frequencies of obligation omission, over-constraint, wrong observable, exception loss, state-effect omission, and other frozen categories. Quantify how many flawed guardrails are caught by metamorphic/differential checks.

Placeholder summary sentence for later replacement: Across [N] requirements, [N] formulations, and [N] generated guardrails, [RESULT TO INSERT].

## 8. Discussion

The central interpretation should focus on recursive trust. Automatically generated enforcement is attractive because it reduces the cost of turning requirements into checks, but the enforcement artifact becomes another AI-produced component that requires assurance.

If the experiment finds high fidelity under explicit formulations but instability under paraphrase or underspecification, the practical recommendation should be to validate the semantic transformation, not merely the generated code. A structured intermediate checklist or multi-formulation differential test may then function as a guardrail on the guardrail generator.

If human-authored controls also exhibit disagreement or incompleteness, the result should not be hidden. That would indicate that the limiting factor is requirement interpretation rather than LLM generation alone.

The paper should avoid claiming that a high guardrail-detection score proves production security. Controlled mutations establish experimental ground truth, not operational defect prevalence. Likewise, robustness to paraphrase does not establish correctness for requirements whose meaning is genuinely ambiguous.

## 8.1 Security and Trusted-AI Implications

The study is directly relevant to trusted AI because it treats model-produced assurance artifacts as outputs requiring independent validation. A secure AI-assisted development pipeline should separate the generator from the authority that establishes correctness, preserve the originating requirement, and expose uncertainty when enforcement semantics are unstable.

The proposed metamorphic check offers one practical mechanism: equivalent descriptions of the same security invariant should not produce materially conflicting enforcement. When they do, the pipeline can route the guardrail for human review instead of silently treating it as trusted.

This architecture supports a broader principle for algorithmic governance: machine-generated controls should carry evidence of how they were validated, not only evidence that they executed.

## 9. Threats to Validity

Construct validity: semantic fidelity is difficult to measure because a requirement may permit multiple correct enforcement strategies. We mitigate this using obligation-level checklists and behavioral evaluation over diverse implementation variants rather than code-text comparison.

Internal validity: human-authored reference guardrails may encode author assumptions, and implementation mutations may accidentally violate more than one requirement. The protocol should validate each mutation independently and freeze both the expected verdict matrix and guardrail-generation prompts before final execution.

External validity: the study uses a finite requirement set, a controlled application, selected model(s), and selected programming languages/tooling. Results should not be generalized to all requirements or all LLMs.

Conclusion validity: if the corpus is synthetic or convenience-sampled, inferential claims about real-world prevalence should be avoided. Report raw counts, per-category outcomes, confidence intervals where meaningful, and exact denominators.

Prior-work contamination: because this study follows earlier work by the same research group, all reused requirements, tooling concepts, or benchmark components must be disclosed. Earlier experimental outcomes must not enter the new results section as if newly observed.

## 10. Reproducibility Plan

The artifact should preserve canonical requirements, all formulation variants, generation prompts, model identifiers, raw guardrail outputs, human reference guardrails, implementation variants, expected-verdict matrices, raw execution logs, analysis scripts, error labels, and environment versions.

A single reproducible runner should regenerate processed metrics from frozen raw artifacts without asking an LLM to grade final outcomes. Any human semantic annotations should be stored as versioned data with adjudication notes.

For double-blind review, author-identifying repository metadata and links must be anonymized or withheld according to conference rules.

## 11. Conclusion

AI-assisted software engineering is moving toward a pipeline in which models can generate both implementation and enforcement. That pipeline is trustworthy only if the enforcement artifact is not treated as correct by construction.

This paper proposes an empirical evaluation of LLM-generated executable guardrails as first-class assurance artifacts. The study measures whether generated controls preserve requirement obligations, remain behaviorally stable under semantically equivalent wording, distinguish compliant from violating implementations, and avoid unsupported restrictions.

The intended contribution is a shift from asking only “Can this requirement be made executable?” to asking “Can we trust the system that makes it executable?” The answer should be grounded in independent behavioral evidence, explicit failure modes, and reproducible validation rather than in the plausibility of generated test or policy code.

## References — Initial Draft / Verify Before Submission

[1] Prior Study A: “Specifications as Governance Artifacts: Human–AI Collaboration and Oversight for AI-Generated Code,” GAISS 2026. Use the appropriate anonymized/self-citation treatment required by double-blind review.

[2] Prior Study B: “From Governance Artifact to Executable Guardrail: Characterizing Requirement-Enforcement Boundaries with Frozen Guardrails,” ETECOM 2026 submission. Cite only if publication/submission policy permits and handle anonymization correctly.

[3] B. Meyer, “Applying ‘Design by Contract’,” Computer, vol. 25, no. 10, pp. 40–51, 1992.

[4] F. Chen and G. Roşu, “MOP: An Efficient and Generic Runtime Verification Framework,” OOPSLA, 2007.

[5] H. Pearce et al., “Asleep at the Keyboard? Assessing the Security of GitHub Copilot’s Code Contributions,” IEEE Symposium on Security and Privacy, 2022.

[6] Y. Fu et al., “Security Weaknesses of Copilot-Generated Code in GitHub Projects: An Empirical Study,” ACM Transactions on Software Engineering and Methodology, 2025.

[7] NIST, Secure Software Development Framework (SSDF), SP 800-218.

[8] NIST, Artificial Intelligence Risk Management Framework and Generative AI Profile.

[9] [REFERENCE TO VERIFY] Research on metamorphic testing for machine-learning or software systems.

[10] [REFERENCE TO VERIFY] Research on LLM-generated tests and test-oracle quality.

[11] [REFERENCE TO VERIFY] Research on semantic consistency / prompt paraphrase sensitivity in LLMs.

[12] [REFERENCE TO VERIFY] Additional trusted-AI / algorithmic-governance literature relevant to AI-generated assurance artifacts.
