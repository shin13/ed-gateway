# Synthetic Live Validation Checklist

Use this checklist to validate the running research MVP before the next revision session. Use synthetic demonstration data only. Do not enter real patient information, credentials, API keys, national IDs, addresses, financial data, or insurance data.

## Record the validation mode

- [ ] Record the date, local time, browser, and current Git commit.
- [ ] Record `LLM_PROVIDER=mock` for the current offline stack, or explicitly record an approved `openai_compatible` test configuration.
- [ ] If using a live provider, use approved synthetic inputs and never copy the API key into feedback, screenshots, or logs.

## Core scenarios

- [ ] Normal complete interview: patient, age 34, no warning signs, dizziness beginning this morning, spinning sensation, mild nausea, no trauma, independent walking, no known history/medication/allergy, no exposure, vitals not measured.
- [ ] Caregiver interview: verify subsequent observations show `CAREGIVER_STATEMENT` provenance.
- [ ] Early completion: finish before answering and verify all missing fields, including 12 safety categories, are listed.
- [ ] Immediate warning: report current chest pain/tightness or sudden one-sided weakness and verify ordinary questions stop, immediate nurse assistance is prominent, the triggering wording is preserved, and no diagnosis or TTAS level appears.
- [ ] Safety ambiguity: give an unclear warning answer twice and verify one direct clarification occurs before conservative escalation.
- [ ] Contradiction: confirm and then deny the same non-terminal field; verify the system asks once for clarification and preserves the conflict in the draft.
- [ ] Draft review: verify every required section, UTC update time, verbatim chief complaint, normalized data, source labels, missing data, contradictions, fixed nurse-only triage-level text, JSON side view, and final disclaimer.
- [ ] New session: use 「開始新的合成展示」 and verify the previous draft does not leak into the new browser session.

## Feedback template

Copy one block per issue into the next session:

```text
Validation mode: mock / openai_compatible
Date and approximate time:
Scenario:
Synthetic answer sequence:
Expected behavior:
Actual behavior:
Safety impact: none / possible / immediate
Screenshot or response excerpt (no real patient data or secrets):
Can reproduce: always / sometimes / once
```

If behavior could suppress or delay a configured warning, stop that scenario and flag it as an immediate safety-impact issue rather than continuing ordinary validation.
