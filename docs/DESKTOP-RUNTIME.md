# JARVIS Desktop Runtime

## Current implementation

The desktop workspace is a Tauri 2 application using the React/Vite interface.

- Vite serves the interface on fixed loopback development port 1420.
- Tauri uses the compiled apps/desktop/dist assets in packaged builds.
- Native Rust startup creates a fresh per-launch token using two UUIDv4 values.
- The native process starts the packaged Python gateway sidecar with the token in its process environment and fixed loopback arguments (127.0.0.1:8765).
- The native process drains sidecar output without forwarding it to the webview and terminates the process group when the desktop exits.
- The webview never receives the session token.
- The native Tauri command `get_gateway_capabilities` calls only `http://127.0.0.1:8765/v1/system/capabilities`, adds the `X-Jarvis-Session` header in Rust, applies a five-second timeout, and returns the JSON response.
- The React UI invokes this typed command and displays the gateway's reported session state. This is not a general-purpose HTTP proxy and the UI cannot choose URLs, methods, or headers.
- The shell-plugin capability is scoped to one named sidecar and the exact host/port argument sequence; arbitrary shell commands are not permitted.
- The Python gateway refuses to bind to a non-loopback host.
- Windows CI builds the sidecar with PyInstaller, smoke-tests authentication, and produces an NSIS installer.

## Run locally on Windows

Install workspace dependencies and build the gateway sidecar:

```powershell
pnpm install
.\scripts\build-gateway-sidecar.ps1
pnpm dev:app
```

The helper requires Python 3.11 and the Rust stable toolchain. It creates `apps/desktop/src-tauri/binaries/jarvis-gateway-<target-triple>.exe`.

## Security boundary

This is a private desktop shell with a process-level gateway session gate and one typed native read bridge, not yet a complete owner-authenticated agent runtime.

- No arbitrary filesystem, process, or shell command access is exposed to the webview. The only shell-plugin scope is the fixed gateway sidecar and fixed arguments.
- No API token is embedded in the React frontend or returned by native commands.
- The bridge exposes only a fixed, read-only capabilities request. No generic URL fetch, HTTP method selection, or arbitrary headers are accepted from JavaScript.
- The gateway session token is not permanent identity and does not prove workspace membership.
- Owner login, trusted workspace membership, RLS, approval consumption, and audit enforcement are not yet complete.
- Project writes and tool execution are not connected.
- Voice, camera, screen capture, browser control, and general computer-use permissions remain disabled.

## Next engineering gate

1. Confirm the Windows native bridge compile and installer workflow pass.
2. Add owner authentication and trusted workspace membership before any project writes.
3. Add a typed project/memory API after authorization and persistence boundaries are established.
4. Add approval issuance and single-use consumption bound to exact action arguments.
5. Add Windows signing, release metadata, and update strategy.
