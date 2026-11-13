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

The native Windows shell is compiled in GitHub Actions, and a standalone Windows x64 executable is published as a build artifact. A signed installer is not available yet.

## Current status
The repository contains the product and security specifications, a React desktop workspace, a FastAPI gateway foundation, automated tests, and a Tauri 2 native shell. A Windows x64 executable has been built in CI. The gateway now enforces a local session-token header on protected routes, but the desktop does not yet provision that token or launch the gateway. No production agent execution, voice, persistent memory, or computer-use tools are claimed yet.

## Safety boundary
JARVIS is an authorized personal productivity and engineering assistant. It must not perform covert recording, unauthorized access, credential theft, malware deployment, evasion, or surveillance of targeted private individuals. Security testing is limited to systems the user owns or is explicitly authorized to assess.
