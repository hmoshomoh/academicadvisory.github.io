# Academic Support & Complaints System - MVP Build Spec

Sep 27, 2026 - @Ifeakachukwu Owoh

## Goal for the build agent

Build the Academic Support & Complaints Management System described below as an MVP: a Django app with an academic-advisory module (GPA/CGPA + auto recommendations) and an anonymity-preserving complaints module, for a college project — not a production SaaS.

Definition of done:

- Every item in `EXPECTATIONS.md` (section "Pre-development gate") is checked off, each backed by a passing test or a verified manual walkthrough — never checked because the code merely runs.
- The build order in "Pre-development gate" is followed phase by phase; a phase isn't started until the prior phase's items are all checked.
- Nothing is added beyond what this spec and the original brief describe — if a requirement can't be met as scoped, it stays unchecked with a one-line blocker note, not silently dropped or reinterpreted.

## What changed from the original brief

The brief's stack (Django, Postgres, Bootstrap templates) is already fairly simple — the complexity crept in around deployment, an optional API layer, and how finely RBAC was specified. Nothing about the two modules themselves, or the anonymity rule, is cut.

| Area | Original brief | Simplified for MVP | Why |
| --- | --- | --- | --- |
| Deployment | Gunicorn + Nginx on a self-managed Ubuntu VPS | A managed PaaS with a Postgres add-on (Render, Railway, or Fly.io); Gunicorn still runs, platform handles the reverse proxy and TLS | No VPS/Nginx/SSL setup to hand-configure or grade |
| Frontend/API | Stack allows substituting DRF + a JS framework | No REST API layer, no SPA — plain Django views + templates + Bootstrap | Avoids a second auth surface (session vs token), a separate frontend build, and CORS handling for no real benefit at this scale |
| RBAC | Implied fine-grained, per-feature permission checks | Django's built-in auth Groups (Student, Adviser, Admin) + view-level decorators; adviser scoping done with one FK filter | Keeps the three-role separation and adviser-only-sees-assigned-students behavior, drops a bespoke permission engine |
| Testing tooling | Postman for API testing | Django's built-in test client only | There's no separate API to test against |
| Non-functional targets | <3s response, \~99% uptime target, ISO 10002-aligned audit language | Audit trail kept (it's a functional requirement); the SLA/compliance framing dropped | Those are production SLAs — nothing to instrument or prove for a college MVP |

## Final tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3 + Django, server-rendered (no DRF, no separate API) |
| Database | PostgreSQL |
| Frontend | Django templates + Bootstrap 5 + vanilla JS |
| Auth / RBAC | Django's built-in auth + Groups: Student, Adviser, Admin |
| Deployment | A managed PaaS with a Postgres add-on (Render, Railway, or Fly.io) — Gunicorn via a Procfile, no manual Nginx/VPS config |
| Testing | Django's built-in test framework (unit + integration) + manual click-through checks |
| Tooling | Git/GitHub, VS Code |

This is a deliberate substitution of the brief's own stack section (Python/Django, PostgreSQL, Bootstrap, Gunicorn+Nginx+Ubuntu, Postman) — same backend and database, simpler frontend and deployment path.

## Data model

&#91;embedded content: entity & role hierarchy · anonymity gate\]

Every record traces back to a Student; advisers and admins each reach only the branch their role needs, and an anonymous complaint's identity never rejoins the tree — no exceptions in queries, joins, or exports.

Entities: `User` (base) → `Student` / `Adviser` / `Admin`; `Student` 1–N `AcademicRecord` → N `Recommendation`; `Student` 1–N `Complaint`; `Complaint` N–1 `ComplaintCategory`; `Complaint` 1–N `ComplaintStatusLog`; a status change → N `Notification`.

## In-scope features and roles

| Role | Can do |
| --- | --- |
| Student | Register/log in; view GPA/CGPA and auto-generated recommendations; submit a complaint (named or anonymous) with an attachment; track status via a reference code |
| Adviser | View only their assigned students' academic records; respond to advisory requests |
| Admin | Categorize, resolve, or escalate any complaint; view the analytics dashboard (volume, categories, resolution time, exportable reports) |

Core features:

- Auth against Django's own user model (no external institutional-credential integration)
- GPA/CGPA computation and rule-based recommendation generation (course advice, warning, probation alert) from performance thresholds
- Complaint submission form with a named/anonymous toggle and file/image attachment
- On submit: a unique tracking reference the student uses to check status without re-authenticating or exposing identity
- Admin workflow: categorize → resolve directly, or escalate
- Append-only `ComplaintStatusLog` (who did what, when) on every complaint
- Notifications on status change
- RBAC via Django Groups (Student/Adviser/Admin), enforced with `@login_required` / `@user_passes_test` and a queryset filter scoping advisers to their assigned students

Hard constraint, unchanged from the brief: anonymity must survive the full lifecycle. If a complaint is anonymous, identity must never be exposed to admins, advisers, or in logs/exports — the tracking reference is the only link back to the student, and it must not be reversible without proper authorization. Don't just nullable-out a student FK; decide whether identity is stored at all for an anonymous complaint, and make sure joins/reports can't leak it.

## Non-functional requirements, trimmed for MVP

- Security: Django's defaults are enough — CSRF protection, session auth, hashed passwords; HTTPS is inherited from the PaaS, not something to configure by hand
- Confidentiality: the anonymity constraint above holds; nothing further to design for it
- Auditability: the append-only `ComplaintStatusLog` is a functional requirement, not optional — every admin action on a complaint is logged with who/what/when
- Performance and reliability: no formal SLA to instrument or load-test; pages should feel responsive on a normal dev/small hosting tier, that's it
- Compatibility: responsive via Bootstrap, works on desktop and mobile browsers, no native app

## Pre-development gate: EXPECTATIONS.md

Before writing any application code, write `EXPECTATIONS.md` at the repo root. Turn every functional and non-functional requirement in this spec into an individual, checkable line item (`- [ ]`), grouped by the phases below. This file is the gate for the whole build, not a status log:

- Never check an item (`- [x]`) because the code runs without erroring — only because a test passes or you personally verified it by walking through the feature.
- Don't start phase *N+1* until every item in phase *N* is checked.
- If a requirement can't be met as scoped, leave it unchecked and add a one-line note underneath explaining the blocker — never drop the line or quietly reinterpret the requirement.

Build order (same phases as the original brief):

1. Auth + roles (Student/Adviser/Admin via Django Groups) + base schema
2. Academic records + GPA/CGPA computation + recommendation logic
3. Complaint submission, including the anonymous path + tracking reference
4. Admin review: categorize/resolve/escalate + status log
5. Notifications
6. Admin analytics dashboard + export
7. Testing pass + manual click-through checks

## Testing requirements

- Manual checks: click through each role (Student, Adviser, Admin) at least once per feature area — informal, no separate UAT logistics needed for a college project

An `EXPECTATIONS.md` item tied to the features gets checked once its test passes or the walkthrough is actually done — not when the surrounding code looks finished. If you have to use unit test make them very few and minimal, and only run them after large code pushes
