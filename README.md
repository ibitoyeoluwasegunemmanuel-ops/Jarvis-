# JARVIS

A personal AI operating environment for work, technology, and life administration.

JARVIS is designed as a persistent, multimodal, voice-first AI system with a realistic 3D presence, shared visual workspace, project memory, specialist agents, and permissioned computer operation.

## Product principles
1. One coherent system, not disconnected tools.
2. Voice and visual interaction are first-class interfaces.
3. The assistant must inspect, reason, act, verify, and report.
4. User data and computer access are protected by explicit permissions.
5. Important actions are auditable, reversible where possible, and approval-gated.
6. Capabilities expose confidence and limitations.
7. Build for a private first deployment while keeping multi-user architecture possible.

## Documentation
- [Master PRD](docs/MASTER-PRD.md)
- [System architecture](docs/SYSTEM-ARCHITECTURE.md)
- [Data model](docs/DATA-MODEL.md)
- [Security and threat model](docs/SECURITY-THREAT-MODEL.md)
- [Engineering standards](docs/ENGINEERING-STANDARDS.md)
- [Integrated delivery plan](docs/INTEGRATED-DELIVERY-PLAN.md)
- [Desktop runtime](docs/DESKTOP-RUNTIME.md)

## Development

```powershell
pnpm install
.\scripts\build-gateway-sidecar.ps1
pnpm dev:app
```

The sidecar helper requires Python 3.11, Rust stable, and PyInstaller. It creates the target-triple binary under `apps/desktop/src-tauri/binaries`.

## Current status
The repository includes a Tauri 2 Windows desktop shell, a loopback-only packaged FastAPI sidecar, local single-owner authentication, and an owner-only local Projects workspace. Projects support creation and status tracking; each project supports task creation, listing, and status tracking, an immutable audit-history timeline, an append-only decision journal with rationale and source references, and milestone planning with target dates and tracked status. Project, task, and decision changes append audit events. CI run #93 passed desktop typecheck/build, Ruff, 32 gateway tests, the packaged Windows gateway smoke test, the NSIS installer build, and installer artifact upload. The Windows installer is available as the `jarvis-windows-x64-installer` artifact on the [successful CI run](https://github.com/ibitoyeoluwasegunemmanuel-ops/Jarvis-/actions/runs/43577694380). The milestone and decision-journal workspace now passes Ruff and 37 gateway tests; desktop typecheck/build also pass. The latest Windows packaged-sidecar and installer checks are still running. See [Build Status](docs/BUILD-STATUS.md) for the exact validation state. Voice, avatar, project decisions/milestones, persistent memory, specialist execution, and computer-use tools remain in development. No physical-device installer test or signed installer is claimed.

## Safety boundary
JARVIS is an authorized personal productivity and engineering assistant. It must not perform covert recording, unauthorized access, credential theft, malware deployment, evasion, or surveillance of targeted private individuals. Security testing is limited to systems the user owns or is explicitly authorized to assess.
