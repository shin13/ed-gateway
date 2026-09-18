# ED Gateway State

_Last updated: 2026-09-18 — Session: multilingual safety detection_

## Status

Multilingual safety detection is merged into `main` (`453583d`). The stack is running from merged
`main` with `LLM_PROVIDER=openai_compatible` (`gpt-4.1-mini`), all three services healthy. Both
feature branches were merged and deleted; `main` is the only branch. Unit suite green
(73 passed, 1 skipped), ruff and mypy clean.

One test is **knowingly red** — see "Open Decision" below. No code work is in progress.

## NEXT PRIORITY — colleague-testable self-contained web app

Make ED Gateway something a colleague can host on their own machine via Docker, chat with, and give
feedback on. This is the next session's whole job. It is deployment/operability work, not features.

**Blockers, in the order they actually bite.** Each is verified against the current tree, not assumed:

1. **No git remote.** Verified: `git remote -v` is empty, no branch has an upstream. Colleagues
   cannot obtain the code at all, and today it exists on exactly one disk with no backup. This is
   the first thing to fix. Other projects here push to ailab GitLab over HTTPS — reuse that, and
   mind the two documented push failure modes (the `Expect:` header one, and the receive-pack size
   limit).
2. **Both ports bind to localhost only** — `docker-compose.yml:39,59` publish `127.0.0.1:8001` and
   `127.0.0.1:8000`. Nobody else on the network can reach a running instance. Two different shapes
   follow from this, and they need different work: (a) each colleague runs their own stack — needs
   the repo, Docker, an `.env`, and their own LLM credentials; or (b) one shared host — needs the
   binding opened, which must not happen before item 3.
3. **No authentication whatsoever.** Verified: no auth callback anywhere in
   `src/ed_gateway/chainlit_ui/`. Anyone who can reach the port can start an interview. Acceptable
   while bound to localhost; unacceptable the moment the binding opens.
4. **Synthetic-data-only is a notice, not a control.** `CLAUDE.md` requires synthetic data only, and
   the UI shows 「研究展示用途」, but nothing prevents a colleague from typing real patient details
   into a hospital-adjacent tool. Decide deliberately how this is enforced or accepted before
   inviting testers. This is the highest-consequence item, even though it is not the first blocker.
5. **Secret distribution is undefined.** `.env` is correctly gitignored (`.gitignore:1`) and
   `.env.example` is committed, but there is no documented way to hand a colleague a working
   `LLM_API_KEY` / `LLM_BASE_URL`. Also unverified: whether the configured LLM endpoint is even
   reachable from a colleague's machine, or only from inside 院內 network.
6. **The `POSTGRES_PASSWORD` trap will hit every new tester.** Postgres applies that variable only
   when the data directory is first initialised; changing it later leaves the volume on the old
   password and `api` crash-loops with `InvalidPasswordError`. This cost real time on 2026-09-04
   and is currently documented nowhere. It belongs in the setup instructions.
7. **No feedback capture in the product.** Collecting feedback is the stated purpose, yet the only
   mechanism is `docs/live-validation-checklist.md`, a manual template. Decide whether feedback
   goes in-app or stays a form colleagues fill in by hand.
8. **Multi-user behaviour is unevidenced.** Concurrency and idempotency were already outside the
   MVP's evidence, and several colleagues chatting at once is exactly that untested case.
9. **Images are untagged.** `api` and `web` are `build: .` with no `image:` tag, so there is no
   versioned artifact and no rollback target. Worth fixing before anyone else depends on an
   instance.

Suggested first step next session: decide between shape (a) per-colleague local stack and
shape (b) one shared host, because almost everything above branches on that single choice.
Shape (a) is far less work and avoids items 2, 3, and most of 8.

## Open Decision — failing compose smoke test

`tests/smoke/test_compose.py:28` asserts 「胸痛還冒冷汗」 triggers exactly `["WARN-CARDIOVASCULAR"]`.
It now returns `["WARN-CARDIOVASCULAR", "WARN-CIRCULATION"]`. Traced to the layer:

- `safety.cardiovascular` → keyword layer, `{"detail": "胸痛還冒冷汗", "present": true}`
- `safety.circulation` → semantic layer, `{"present": true, "detected_by": "llm_semantic_screen"}`

The model mapped 冒冷汗 to the circulation category's `cold clammy skin` concept. The Chinese
keyword list for circulation has 皮膚冰冷、臉色蒼白、快昏倒、眼前發黑、心悸又無力 but not 冒冷汗, so
the keyword layer never caught it. Escalation behaviour is unchanged — still `ESCALATED`, ordinary
questioning still stops. The nurse just sees two categories instead of one.

Two unresolved questions: **(1) engineering** — should the assertion become containment
(`"WARN-CARDIOVASCULAR" in triggered`), since the test's job is proving the escalation path, not
that exactly one rule fires? Left unchanged deliberately, because the trigger for changing it was a
behaviour change introduced in the same work. **(2) clinical** — should 冒冷汗 flag circulation at
all? Not an engineering call; belongs with `docs/open-clinical-decisions.md`.

Related discovery: the feature is **not only multilingual**. It also catches Chinese phrasings the
hardcoded keyword list misses — wider than the approved scope, arguably beneficial, still undecided.

## What Was Done This Session

- Diagnosed the reported "stiff dialogue / doesn't understand English" complaint to root cause:
  `mock` provider does no interpretation at all, and `extractor.py`'s detection is pure Traditional
  Chinese keyword matching.
- Fixed a live-provider crash (`respondent.type` enum coercion) with dual-layer validation, TDD.
- Designed, planned, implemented, and live-verified multilingual safety detection across 6 TDD
  tasks. Design: `docs/multilingual-safety-detection-design.md`. Plan:
  `docs/multilingual-safety-detection-plan.md`.
- Closed a pre-existing defect found along the way: the extractor call in `orchestrator.py` had no
  exception handling, so any provider timeout or connection failure crashed the turn with a 500.

## Decisions Made

- **LLM detects, deterministic rules decide.** The 12 categories and all escalation policy stay in
  versioned config and `SafetyGate`; the provider only proposes detections.
- **Add-only asymmetric trust.** A proposal may flag a category the keyword sweep missed, never
  clear or downgrade one it found. A wrong model costs a redundant flag, never a suppressed warning.
- **One LLM call per turn**, extending the existing call rather than adding a second one.
- **Provider failure degrades quietly** (option B1): keyword-only screening for that turn plus a
  nurse-review note in the draft — not the urgent banner, because a network fault carries no
  clinical signal and a false urgent screen has its own on-site cost.
- **English concept wording lives in `config/safety-rules.yaml`**, not hardcoded, so clinical
  reviewers can change it without a code change.
- Merged to `main` with one knowingly-red smoke test rather than weakening the assertion to force
  green.

## Verified Evidence

- Merge `00c199d` (`--no-ff`), state record `453583d`. Feature commits `1ada9bd`…`32823d9`.
- Unit suite on the merged result: 73 passed, 1 skipped. Ruff clean. Mypy clean, 26 source files.
- English warning during an unrelated question → `ESCALATED`, `WARN-NEUROLOGICAL`, observation
  carries `detected_by: llm_semantic_screen` with the English verbatim text and
  `requires_human_confirmation: true`.
- Chinese baseline unchanged; `"I am 34 years old"` and `"我34歲"` do not falsely escalate.
- Degraded path exercised live, not only in tests: a one-off API container pointed at
  `LLM_BASE_URL=http://127.0.0.1:9/v1` against the real database returned `200`, advanced the
  interview, and listed both unscreened answers in 【護理師覆核重點】.
- Data survived the down/rebuild cycle: 29 sessions, 19 drafts.
- `api` logs contain no tracebacks and none of the interview text used in these runs.

## Known Issues / Residual Scope

- The failing smoke test above.
- English `detection_concepts_en` wording has **no clinical or bilingual review** — item 10 in
  `docs/open-clinical-decisions.md`.
- **No per-language evaluation was run.** Only English and Traditional Chinese were exercised.
- Chinese phrase lists remain hardcoded in `extractor.py` rather than versioned in `config/`, still
  contradicting the architecture note in `CLAUDE.md`.
- Non-safety fields other than `respondent.type` still accept any shape a provider proposes. No
  crash known; consumers guard with `isinstance`; not exhaustively tested live.

## Context for Next Session

Start from `453583d` on `main`. Re-check `git status`, `docker compose ps`, `/health/ready`, and the
configured `LLM_PROVIDER` before trusting any of the runtime state above — the stack was left
running but Docker Desktop does not survive a reboot, and `docker compose` fails with
`failed to connect to the docker API` until it is started.
