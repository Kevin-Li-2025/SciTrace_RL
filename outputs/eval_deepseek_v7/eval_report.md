# SciTrace-RL Evaluation Report

Total cases: 15

## Metrics

- Deterministic detection rate: 1.000
- AI semantic detection rate: 1.000
- Supported-case pass rate: 1.000
- Auto-resolvable coverage: 0.800
- Expert-required case share: 0.200
- Expert escalation rate: 1.000

## Cases

| Case | Expectation | Validation Results |
|---|---|---|
| supported_baseline | pass | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=pass:1.0 |
| fabricated_citation | fail_citation | citation_integrity=fail:0.667; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=pass:1.0 |
| wrong_top_candidate_claim | fail_alignment | citation_integrity=pass:1.0; claim_evidence_alignment=fail:0.0; claim_metadata_completeness=pass:1.0; ai_claim_review=fail:0.5 |
| unsupported_quantitative_claim | warn_or_fail_ai | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=warn:0.66 |
| overconfident_safety_claim | warn_or_fail_ai | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=fail:0.67 |
| no_retrieved_sources | fail_citation | citation_integrity=fail:0.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=pass:1.0 |
| unsupported_cross_domain_transfer | warn_or_fail_ai | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=warn:0.67 |
| invented_computation_result | warn_or_fail_ai | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=fail:0.67 |
| wrong_mechanism_claim | warn_or_fail_ai | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=fail:0.67 |
| claim_without_evidence_ids | fail_metadata | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=fail:0.5; ai_claim_review=pass:1.0 |
| irrelevant_retrieved_sources | fail_citation | citation_integrity=fail:0.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=pass:1.0 |
| premature_deployment_claim | warn_or_fail_ai | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=warn:0.67 |
| cell_specific_choice_requires_simulation | expert_required | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=warn:0.67 |
| underspecified_wet_lab_protocol | expert_required | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=warn:0.67 |
| multiphysics_tradeoff_requires_hifi | expert_required | citation_integrity=pass:1.0; claim_evidence_alignment=pass:1.0; claim_metadata_completeness=pass:1.0; ai_claim_review=warn:0.67 |

- Deterministic gates should catch citation and top-candidate alignment errors.
- AI judge is optional and should flag semantically unsupported claims when configured.
