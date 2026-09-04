# ED Gateway Source Authority

This record defines how conflicts among supplied clinical and engineering materials are handled. It does not approve any clinical rule for production.

## Authority order

1. `GOAL.md` defines the product, safety, and engineering scope.
2. `1_INSTRUCTIONS_貼入指令欄_v2.1.md` is the candidate source for dialogue order and safety boundaries.
3. `2_KNOWLEDGE_急診前哨_警訊與範例.md` supplies detailed wording and examples.
4. `胸痛.docx`, `頭暈.docx`, `發燒.docx`, and `下背痛.docx` are nursing examples, synthetic fixture sources, and acceptance material. They do not define four separate flows.
5. `reference/arxiv-2506.04032.pdf` supplies modular-architecture and simulation-evaluation ideas only. Its diagnosis, care-recommendation, multi-agent, and EHR-retrieval design is outside this MVP.
6. TTAS and workflow PDFs are reference material only. They do not authorize formal TTAS scoring or patient-facing thresholds.

All supplied materials remain read-only in the research-material directory. The only implementation repository is `/Users/shin/Projects/ed-gateway`; the research directory contains a symbolic link to it.

## Resolved source conflict

The older intervention workflow displays a neurological escalation branch containing a 4.5-hour window. The newer v2.1 instructions explicitly remove that threshold. ED Gateway records onset or last-known-normal time but routes configured current neurological warning signs for nurse review regardless of elapsed time.

## Binding output boundary

ED Gateway may collect, clarify, normalize, identify configured warning-sign observations, stop ordinary questioning, and create a nurse-review draft. It must not diagnose, infer a disease, recommend treatment or medication, promise safe waiting, estimate missing measurements, assign a formal triage level, or automatically submit a hospital record.
