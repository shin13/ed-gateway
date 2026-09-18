# ED Gateway State

_Last updated: 2026-09-18 — Session: colleague-testable local deployment_

## Status

`main` is at `d6beb50` and in sync with `origin/main` on private GitHub. The stack runs from `main`
with `LLM_PROVIDER=openai_compatible` (`gpt-4.1-mini`), all three services healthy on image
`ed-gateway:0.1.0`. Unit suite green (84 passed, 1 skipped), ruff and mypy clean.

One test is **knowingly red** — see "Open Decision" below. No code work is in progress.

## Decided: per-colleague local stack (shape a)

Each colleague clones the repository and runs their own Docker stack with their own LLM credentials.
Nothing is hosted on a shared machine. This closes the localhost-binding, authentication and
concurrency questions by avoiding them rather than solving them; reopen all three before any shared
host is considered.

### Delivered this session

- **`DEPLOYMENT.md`** — the colleague-facing setup guide: offline demo, full mode with their own key,
  how to send feedback, and the traps below.
- **Versioned images** — `api` and `web` build one `ed-gateway:0.1.0` image, overridable with
  `ED_GATEWAY_VERSION`. Verified: both containers report the same image id.
- **Offline-mode notice** — the chat asks the API which provider is live and says on its first screen
  when answers are only keyword-matched, so mock-mode feedback is not mistaken for full-mode feedback.
- **Session export** — `GET /api/v1/interview-sessions/{id}/export` and a 「匯出本次對話」 button
  produce one Markdown file: session id, provider and model, rule version, transcript with each
  statement's source, triggered warnings, and the draft.
- **README correction** — the offline demo needs no `.env`; the README said to create one first.

### Blockers, updated

1. ~~No git remote.~~ **Resolved.** `origin` is `https://github.com/shin13/ed-gateway.git`, a
   **private** repository. Pre-push audit found no secrets in the full history, no tracked `.env`,
   and no 院內 hostnames or IPs.

   **Boundary this creates.** This repo is hosted outside 院內, unlike the other projects here. Real
   patient data, 院內 endpoints and internal hostnames must never enter it. The first push was safe
   only because `GOAL.md` keeps all research material in `~/Downloads/` behind a symlink, so no
   source document has ever been committed. Keep it that way.
2. **Ports bind to localhost only** — `docker-compose.yml` publishes `127.0.0.1:8001` and
   `127.0.0.1:8000`. Under shape (a) this is the intended design, not a defect.
3. **No authentication.** Acceptable while bound to localhost. Blocking for any shared host.
4. **Synthetic-data-only is still a notice, not a control.** `DEPLOYMENT.md` and the UI both say it
   in the strongest wording available, but nothing prevents a colleague from typing real patient
   details into a hospital-adjacent tool. **Highest-consequence open item.** Decide deliberately
   whether this is enforced or accepted before inviting testers.
5. **Secret distribution — decided, partly unverified.** Each colleague uses their own key; nothing
   is shared through the repository, and `DEPLOYMENT.md` says so. Verified: `beta-test.tsgh-dmc.com`
   resolves to public addresses (`54.54.14.188`, `43.213.251.33`, `43.213.236.253`), so it is not an
   院內-only name. **Unverified: whether an IP allowlist or similar control blocks a colleague's
   machine, and where a colleague applies for a key.** `DEPLOYMENT.md` currently tells them to ask
   the project owner.
6. ~~The `POSTGRES_PASSWORD` trap is undocumented.~~ **Resolved** — documented in `DEPLOYMENT.md`
   with the symptom and both ways out.
7. ~~No feedback capture in the product.~~ **Resolved** by the export button above.
8. **Multi-user behaviour is unevidenced.** Moot under shape (a), since each colleague runs alone.
   Reopen for any shared host.
9. ~~Images are untagged.~~ **Resolved** — `ed-gateway:0.1.0`.

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
that exactly one rule fires? **(2) clinical** — should 冒冷汗 flag circulation at all? Not an
engineering call; belongs with `docs/open-clinical-decisions.md`.

## Verified Evidence — this session

- Clean `git clone` from GitHub into an empty directory, with **no `.env`**, reached three healthy
  services, `/health/ready` reporting `llm: mock`, Chainlit HTTP 200, and a three-turn interview
  advancing `RESPONDENT → AGE → SAFETY_SCREEN`.
- Both containers report image id `6b70b2cf5881` under tag `ed-gateway:0.1.0` — one image, not two.
- Export exercised against the real PostgreSQL and the live provider; the rendered file carried the
  session id, `openai_compatible / gpt-4.1-mini`, `clinical-review-draft-v1`, the transcript with
  `CAREGIVER_STATEMENT` provenance, and 「本次會談未產生草稿。」 where no draft existed.
- Export button exercised in a browser end to end: the action returned a downloadable
  `ed-gateway-<session>.md` file element.
- Inside the `web` container, `/health/ready` is reachable and `offline_notice` returns `None` for
  the live provider and the banner for `mock`.
- Data survived the image cleanup and rebuild: 36 sessions, 21 drafts.
- Gates on the final tree: 84 passed, 1 skipped; ruff clean; mypy clean over 27 source files.

## Known Issues / Residual Scope

- The failing smoke test above.
- **The clean-clone acceptance run has not been repeated since the export and notice landed.** The
  clone test above ran before those commits, so the offline banner and the current transcript layout
  have not been seen the way a colleague will see them.
- English `detection_concepts_en` wording has **no clinical or bilingual review** — item 10 in
  `docs/open-clinical-decisions.md`.
- **No per-language evaluation was run.** Only English and Traditional Chinese were exercised.
- Chinese phrase lists remain hardcoded in `extractor.py` rather than versioned in `config/`, still
  contradicting the architecture note in `CLAUDE.md`.
- `DEPLOYMENT.md` is English, following the repo convention. If the people who actually run Docker
  are clinical staff rather than developers, it needs a Traditional Chinese quick start.
- Non-safety fields other than `respondent.type` still accept any shape a provider proposes.

## Context for Next Session

Start from `d6beb50` on `main`. Re-check `git status`, `docker compose ps`, `/health/ready` and the
configured `LLM_PROVIDER` before trusting any runtime state above — Docker Desktop does not survive a
reboot, and `docker compose` fails with `failed to connect to the docker API` until it is started.

First job: the clean-clone acceptance run listed under Known Issues. It needs the local stack stopped,
because both use ports 8000 and 8001.
