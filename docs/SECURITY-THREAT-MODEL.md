# JARVIS — Security, Privacy, and Threat Model

## 1. Objectives
Protect identity, files, projects, credentials, communications, devices, and connected accounts. Prevent unauthorised actions, cross-workspace leakage, hidden capture, unsafe tool execution, and misleading completion claims.

## 2. Assets
OAuth tokens and API keys; signing keys; source code and proprietary documents; datasets and financial records; email/calendar/contacts; screen/camera/microphone media and transcripts; memory and audit records; local operator, browser profiles, and developer workspaces.

## 3. Trust boundaries
1. User to desktop renderer.
2. Renderer to local gateway.
3. Gateway to model/voice providers.
4. Gateway to local operator.
5. Gateway to external integrations.
6. Workspace/tenant to workspace/tenant.
7. Untrusted external content to agent instructions/tools.

Web pages, emails, files, repository content, model output, and tool output are untrusted data. They never become system instructions or permission grants.

## 4. Threats and required controls

| Threat | Control |
|---|---|
| Prompt injection in pages/files | Treat retrieved content as data; independent tool policy; approvals for side effects |
| Secret leakage | OS-backed secure storage/encrypted vault; redaction; no secrets in prompts/logs/client bundle |
| Arbitrary command execution | Allowlisted commands, isolated workspace, scoped filesystem, explicit elevation |
| Malicious browser workflow | Domain allowlists, isolated browser context, download quarantine, visible session |
| Cross-tenant leakage | RLS, tenant-bound queries, scoped grants, negative tests |
| Approval replay/tampering | Short-lived approval bound to exact action hash and nonce |
| Covert recording | Explicit consent, persistent indicators, stop controls, no background capture |
| Data exfiltration | Egress policy, least privilege, outbound payload review and approval |
| Supply-chain compromise | Lockfiles, dependency scanning, signed releases, update verification |
| Unsafe agent autonomy | Risk tiers, budgets, timeouts, cancellation, human approval |
| False completion claim | Independent verification, evidence, explicit partial/failed/unverified states |
| Data loss/ransomware | Backups, restore drills, restricted deletion, version history |

## 5. Risk tiers
### Tier 0 — Read-only, low impact
Examples: explain supplied code, inspect explicitly shared screenshot, read permitted repository file. Allow within granted scope and log access.

### Tier 1 — Reversible local changes
Examples: create draft file in approved workspace, generate chart, prepare patch. Restrict to scoped workspace and retain diff/undo.

### Tier 2 — External or consequential changes
Examples: send email, publish content, create issue, change cloud setting, modify shared data. Require approval of exact action and target.

### Tier 3 — High impact or destructive
Examples: production deployment, database migration, deletion, permission change, financial transaction. Require step-up confirmation, impact summary, recovery plan, and independent verification. Some actions may remain disabled in initial release.

## 6. Secure execution protocol
1. Model proposes structured tool call.
2. Schema validates arguments.
3. Policy evaluates user, workspace, scope, target, risk, and environment.
4. Approval UI shows exact action, data sent, target, impact, and expiry.
5. User approves; server issues one-time action-bound approval.
6. Executor revalidates policy and action hash immediately before execution.
7. Executor performs operation with timeout and idempotency.
8. Verification checks resulting state independently.
9. Audit stores redacted request, approval, result, and evidence.
10. User receives truthful status: verified, partial, failed, or unverified.

## 7. Secure development
Threat model every privileged tool and integration. CI includes static analysis, dependency audit, secret scanning, and licence checks. Validate inputs and encode outputs. Address CSRF, SSRF, path traversal, injection, and unsafe deserialisation where relevant. Rate-limit and budget providers. Establish secure update/code-signing. Review IPC, local networking, permissions, and auto-start. Never commit production secrets or real user data.

## 8. Privacy controls
Capture is opt-in and visible. Raw audio/video/screen is transient by default. Retention is disclosed and configurable. Export/deletion includes derived memory and embeddings. Sensitive data excluded from analytics unless necessary. No training use of private data without informed consent. Review compliance against applicable law, including Nigeria Data Protection Act 2023, before launch.

## 9. Incident response
Emergency stop halts active runs, browser sessions, and operator jobs. Revoke tokens and device sessions. Preserve minimal security evidence without copying unnecessary sensitive payloads. Notify owner with scope/timeline/assets, contain, rotate credentials, patch, retest, and document lessons. Restore only from verified backups.

## 10. Release blockers
Critical/high unresolved vulnerabilities, exposed credentials, unbounded OS access, bypassable approvals, broken tenant isolation, silent capture, and unverified high-impact operations block release.
