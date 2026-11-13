# JARVIS Desktop Runtime

## Current implementation

The desktop workspace is a Tauri 2 application using the React/Vite interface.

- Vite serves the interface on the fixed loopback development port 1420.
- Tauri uses the compiled apps/desktop/dist assets for packaged builds.
- The native Rust startup generates a fresh per-launch session token using two UUIDv4 values.
- The native process starts the packaged Python gateway sidecar with the token in its process environment and fixed loopback arguments (127.0.0.1:8765).
- The native process drains sidecar output without forwarding it to the webview and terminates the process group when the desktop exits.
- The webview never receives the session token. Its gateway status widget polls only the public liveness endpoint.
- The shell-plugin capability is scoped to one named sidecar and the exact host/port argument sequence; arbitrary shell commands are not permitted.
- The Python gateway refuses to bind to a non-loopback host.
- The Windows CI workflow builds the sidecar with PyInstaller and is configured to create an NSIS installer.

## Run locally

From the repository root:

```bash
pnpm install
pnpm dev:app
```

The native gateway sidecar must first exist at apps/desktop/src-tauri/binaries/jarvis-gateway-<target-triple>.exe. The Windows CI workflow stages this automatically. A local Windows developer must build the PyInstaller sidecar and copy it to that target-specific filename before launching Tauri.

For a frontend-only development session:

```bash
pnpm dev:desktop
```

## Security boundary

This is a private desktop shell with a process-level gateway session gate, not yet a complete owner-authenticated agent runtime.

- No arbitrary filesystem, process, or shell command access is exposed to the webview. The only shell-plugin scope is the fixed gateway sidecar and fixed arguments.
- No API token is embedded in the React frontend.
- The webview currently calls only GET /health; a native authenticated request bridge for protected gateway APIs is not implemented.
- The gateway session token is not permanent identity and does not prove workspace membership.
- The public liveness endpoint and CORS are not authentication mechanisms.
- Owner login, trusted workspace membership, RLS, approval consumption, and audit enforcement are not yet complete.
- Voice, camera, screen capture, browser control, and general computer-use permissions remain disabled.

## Next engineering gate

1. Verify the PyInstaller sidecar smoke test and NSIS installer in Windows CI.
2. Add a narrowly scoped native request bridge for protected APIs without returning the token to JavaScript.
3. Add owner authentication and trusted workspace membership before any project writes.
4. Add approval issuance and single-use consumption bound to exact action arguments.
5. Add Windows signing, release metadata, and update strategy.
