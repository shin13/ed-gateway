# Privacy and Production Gaps

ED Gateway is restricted to local research demonstrations with synthetic data. Host ports bind to localhost, PostgreSQL is not exposed, secrets are passed only to the API, and raw answers are not written to container stdout.

Production use requires, at minimum:

- hospital SSO, role-based authorization, session ownership, and audit review;
- TLS in transit, managed encryption keys, encrypted storage, and backup controls;
- a retention schedule, deletion workflow, legal basis, consent language, and privacy impact assessment;
- security threat modeling, dependency and container scanning, secret rotation, and incident response;
- institutional clinical approval, prospective safety evaluation, bias and accessibility evaluation, monitoring, and change control;
- an approved EHR interface with human confirmation before final-record submission;
- production observability that excludes protected health information while preserving operational evidence.

The Compose stack, mock-provider tests, and local readiness checks are not production-readiness evidence.
