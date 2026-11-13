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

## Proposed technical direction
- Desktop: Tauri 2 + React + TypeScript
- Local gateway/operator: Python + FastAPI
- Persistence: PostgreSQL + pgvector
- Browser automation: Playwright with explicit session and action permissions
- Avatar: Three.js with commercially licensed rigged GLB/GLTF assets
- Voice and model providers behind replaceable adapters

These are proposed defaults, not irreversible vendor commitments. Provider and hardware decisions require evidence-based evaluation.

## Development

Install workspace dependencies:

```bash
pnpm install
```

Run the desktop interface in a browser:

```bash
pnpm dev:desktop
```

Run the native Tauri desktop shell:

```bash
pnpm dev:app
```

Build the desktop interface:

```bash
pnpm build:desktop
```

The Windows CI workflow packages the Python gateway as a sidecar and builds an NSIS installer. Local native development also needs the target-specific gateway sidecar under apps/desktop/src-tauri/binaries.

## Current status
The repository contains the product and security specifications, a React desktop workspace, a FastAPI gateway, gateway session-token checks, and a Tauri 2 native shell that starts the gateway sidecar with a fresh process token. The interface monitors gateway health. The Windows sidecar smoke test and NSIS installer are being validated in CI. Voice, persistent project memory, specialist execution, and computer-use tools are not yet implemented.

## Safety boundary
JARVIS is an authorized personal productivity and engineering assistant. It must not perform covert recording, unauthorized access, credential theft, malware deployment, evasion, or surveillance of targeted private individuals. Security testing is limited to systems the user owns or is explicitly authorized to assess.
