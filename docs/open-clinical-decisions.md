# Open Clinical Decisions

The following items require institutional clinical governance before any production use. The MVP does not silently resolve them.

1. The 12-category rule set is labeled `clinical-review-draft-v1`; clinical owners must approve exact concepts, wording, age-specific behavior, sensitivity, and escalation handling.
2. Age-unknown interviews currently retain the general 12-category screen and mark age as unresolved. A clinically approved combined adult and pediatric wording set remains open.
3. The current source treats present chest pain or chest tightness as an immediate nurse-review trigger. This limits ordinary follow-up in synthetic chest-discomfort conversations and requires explicit clinical confirmation.
4. The source mentions numeric thresholds for pain, trauma mechanisms, temperature, and blood pressure. Patient-facing threshold wording and device-data validation require clinical and usability review.
5. Pregnancy, self-harm, violence, substance use, domestic violence, and sexual-history questions need a private-channel and on-site response policy.
6. Pediatric routing by weight is an institution-specific specialty rule, not a triage rule, and is not implemented.
7. Language access, inability to communicate, respondent changes, and accessibility fallbacks need approved operational procedures.
8. Measurement provenance and freshness rules need integration contracts for actual devices and clinician-entered values.
9. The acceptable number of unanswered warning categories before mandatory human takeover needs prospective evaluation.
10. The English `detection_concepts_en` wording in `config/safety-rules.yaml` is a working translation of the Chinese phrase lists, used to let the language model recognise the 12 categories in any language. It has had no clinical or bilingual review, carries the same `clinical-review-draft-v1` status as the Chinese lists, and no per-language detection evaluation has been run.
