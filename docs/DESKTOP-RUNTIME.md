# JARVIS Desktop Runtime

## Current implementation

The desktop workspace is a Tauri 2 application using the React/Vite interface.

- Vite serves the interface on fixed loopback development port 1420.
- Tauri uses the compiled apps/desktop/dist assets in packaged builds.
- Native Rust startup creates a fresh per-launch process token using two UUIDv4 values.
- The native process starts the packaged Python gateway sidecar with the token in its process environment and fixed loopback arguments (127.0.0.1:8765).
- The native process owns the sidecar handle and terminates its process group when JARVIS exits.
- A single local owner account is created on first run and authenticated on later launches. Password hashing and session storage happen in the Python gateway's local SQLite database.
- Owner session tokens remain in native Rust-managed state. Native commands implement setup, login, status, logout, gateway capabilities, project list, and project create.
- Owner-session token copies are zeroized in native memory after requests and on logout/runtime drop.
- The webview never receives either the gateway process token or the owner session token.
- The typed project commands call only fixed `/v1/projects` routes and attach both authentication headers natively. JavaScript does not choose the URL, HTTP method, or headers.
- The Projects view lists the local owner's projects and creates new projects. The gateway determines ownership and appends an immutable creation audit event.
- The shell-plugin capability is scoped to one named sidecar and fixed host/port arguments. Arbitrary shell commands are not allowed.
- The packaged Python gateway refuses to bind to a non-loopback host.

## Run locally on Windows

```powershell
pnpm install
.\scripts\build-gateway-sidecar.ps1
pnpm dev:app
```

The helper requires Python 3.11 and the Rust stable toolchain. It creates `apps/desktop/src-tauri/binaries/jarvis-gateway-<target-triple>.exe`.

## Security boundary

This is a private single-owner desktop workspace with local project persistence. It is not yet a cloud multi-user or autonomous agent runtime.

- No arbitrary filesystem, process, or shell command access is exposed to the webview. The only shell-plugin scope is the fixed gateway sidecar and its fixed arguments.
- The gateway process token and owner session token are not embedded in the React frontend or returned by native commands.
- Native API methods are typed and fixed; no generic URL fetch, HTTP method selection, or arbitrary headers are accepted from JavaScript.
- Owner password setup/login is local to this device. It is not a cloud identity provider or multi-user identity system.
- Project reads/writes require a valid owner session. Project owner identity is assigned within the gateway, not submitted by the client.
- Project audit events are append-only in the local SQLite store.
- Cloud workspace membership, PostgreSQL RLS, approval issuance/consumption, and append-only cloud audit enforcement are not complete.
- Voice, camera, screen capture, browser control, and general computer-use permissions remain disabled.

## Next engineering gate

1. Confirm the Windows project bridge compile and packaged owner/project smoke test.
2. Add project update/status and task APIs, with matching audit events.
3. Implement trusted workspace identity and secure cloud persistence before multi-user support.
4. Add approval issuance and single-use consumption bound to exact action arguments.
5. Add Windows signing, release metadata, and update strategy.
