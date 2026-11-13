# JARVIS — Integrated Delivery and Validation Plan

This plan is organised around complete user journeys and shared infrastructure, not disconnected mini-products. Architecture, permission model, data contracts, observability, and design system are established once and reused.

## Workstream A — System foundation
Deliver desktop shell, local gateway, authentication/session model, typed contracts, secure IPC, policy engine, audit trail, configuration, provider adapters, error handling, and emergency stop as one deployable foundation.

Exit evidence: signed-in session; secure local communication; permission allow/deny tests; audit event for every tool call; emergency-stop test.

## Workstream B — Presence and multimodal interaction
Integrate virtual office, avatar state machine, voice streaming, interruption, captions, image/document ingestion, and visible screen/camera sharing.

Exit evidence: latency benchmarks; interruption tests; Nigerian English evaluation; avatar fallback; capture indicator and stop tests.

## Workstream C — Project brain and workspace
Deliver relational project records, source-linked memory, task/decision tracking, search, shared workspace panels, and project briefings.

Exit evidence: create/update/retrieve context across sessions; stale-memory warning; provenance; export/delete tests.

## Workstream D — Orchestration and specialist agents
Deliver central planning and specialist routing for engineering, defensive security, analytics, technology research, design, and operations. Shared tools, budgets, policy, and evaluation apply to all agents.

Exit evidence: multi-step tasks with plan, progress, cancellation, evidence, partial-failure handling, and truthful final status.

## Workstream E — Computer operation and integrations
Deliver restricted browser, file, and developer workers; GitHub and selected Google integrations; connector permissions; approval-bound side effects.

Exit evidence: authorised end-to-end workflow; blocked unauthorised workflow; exact approval binding; revocation; independent verification.

## Workstream F — Production quality
Deliver automated CI, dependency and secret scanning, signed builds, privacy-aware crash reporting, backup/restore, usage budgets, documentation, and update mechanism.

Exit evidence: reproducible build; security review; restore drill; cost report; release checklist passed.

## Integrated user journeys
### Build and secure a product
Inspect repository, understand requirements, propose architecture, implement scoped change, run tests, perform defensive security review, show diff and risks, prepare pull request. Production deployment remains approval-gated.

### Analyse a business dataset
Profile schema, flag missing/duplicate/outlier data, clarify ambiguous business definitions, perform reproducible analysis, build charts, and export assumptions with report.

### Research a technology decision
Compare current vendor documentation, licensing, pricing, compatibility, and security posture; provide dated citations, decision matrix, recommendation, and ADR draft.

### Operate an approved workflow
Show plan, open visible isolated browser session, request approval at consequential boundaries, verify completion, and provide evidence.

### Maintain project awareness
Read only configured sources, update status from verifiable events, detect blockers, and issue scheduled briefings. Offline/disconnected sources are marked clearly.

## Monitoring scope
Monitor only connected and explicitly configured resources: app health, provider availability, job failures, selected repositories, approved deployments, and user-defined project signals. Monitoring is visible, revocable, and reports last successful check. No promise of background monitoring while device/service is offline.

## Release gates
Owner acceptance for complete journeys; security review and threat-model update; automated and exploratory tests; accessibility/performance review; cost/rate-limit review; backup/restore and incident drill. No release with unresolved blocking vulnerabilities or misleading status.
