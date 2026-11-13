# JARVIS — Engineering and Quality Standards

## 1. Repository conventions
- Document product, architecture, security, and implementation decisions.
- Prefer cohesive packages and explicit interfaces.
- TypeScript strict mode; Python type checking.
- Formatting, linting, dependency lockfiles, reproducible builds.
- Never commit secrets, user datasets, raw recordings, or machine-specific config.

## 2. Proposed monorepo layout
```text
apps/
  desktop/                 # Tauri + React desktop application
  workspace-web/           # optional hosted workspace client
services/
  gateway/                 # FastAPI API, auth, orchestration
  operator/                # restricted local computer operator
packages/
  contracts/               # shared API/tool schemas
  ui/                       # shared UI components
  agent-runtime/            # planner, specialists, tool router
  memory/                   # project context and retrieval
  policy/                   # permissions and approvals
  providers/                # model, voice, avatar, OCR adapters
  integrations/             # GitHub, Google, Supabase adapters
infra/
  migrations/
  deployment/
  observability/
tests/
  security/
  integration/
  e2e/
docs/
```

This is the target structure, not a claim that application code already exists.

## 3. API and tool contracts
Version public routes. Validate requests and responses. Tool manifests define permissions, risk tier, timeout, idempotency, verification. Use correlation IDs. Never pass arbitrary model-generated code to privileged execution. Errors use stable codes and actionable summaries.

## 4. Testing pyramid
Unit tests for business logic, policy, schemas, transformations. Integration tests for database/providers/connectors. Contract tests for adapters/tools. End-to-end tests for critical journeys. Security tests for denied actions, path traversal, injection, prompt injection, replay, and tenant isolation. Performance tests for voice streaming, avatar rendering, retrieval, and long-running jobs.

## 5. Required end-to-end journeys
1. Start app, grant microphone permission, hold-to-talk, interrupt assistant, review transcript.
2. Share screenshot, ask about visible error, receive evidence-linked explanation.
3. Create project, add decision/task, retrieve context in later session.
4. Inspect repository, propose patch, run tests in isolated workspace, show diff.
5. Attempt unapproved external action and verify it is blocked.
6. Approve one exact external action and verify result.
7. Revoke integration and prove subsequent calls fail closed.
8. Import dataset, report quality issues, analyse, chart, export.
9. Trigger emergency stop during operator task.
10. Export and delete user data, including embeddings and assets.

## 6. Definition of done
Requirements and edge cases documented; implementation reviewed and typed; tests cover success, failure, cancellation, and permissions; security/privacy assessed; observability and user status present; docs and migrations updated; no success claim without verifiable evidence.
