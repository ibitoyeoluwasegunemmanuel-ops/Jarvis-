# JARVIS Desktop Runtime

## Current implementation

The desktop workspace is now structured as a Tauri 2 application using the existing React/Vite interface.

- Vite serves the interface on the fixed loopback development port `1420`.
- Tauri embeds the compiled `apps/desktop/dist` assets in packaged builds.
- The native Rust entry point starts a Tauri window and registers no application commands or privileged plugins.
- The default capability grants only Tauri core defaults to the `main` window.
- Bundling is intentionally disabled until the Windows installer identity, icon set, signing approach, and release process are ready.

## Run locally

From the repository root:

```bash
pnpm install
pnpm dev:app
```

For a frontend-only development session:

```bash
pnpm dev:desktop
```

## Security boundary

This is a native application shell, not yet a secure local agent runtime.

- No filesystem, shell, process, microphone, camera, screen-capture, or browser-automation permissions are exposed to the webview.
- No Tauri commands are registered.
- No API credentials are embedded in the frontend.
- The FastAPI gateway is still a separate process; automatic startup, health supervision, owner authentication, and shutdown handling are not implemented.
- The current gateway CORS policy and health endpoint do not authenticate callers. Do not treat loopback binding or CORS as authentication.
- The app must not be used to run sensitive tasks until the local session boundary and approval enforcement are implemented.

## Next engineering gate

1. Build and test this native shell on a Windows runner.
2. Implement a supervised local gateway lifecycle with an owner-only session token.
3. Bind all mutating actions to authenticated identity, workspace, exact arguments, expiry, and one-time approval.
4. Add only the narrowly scoped Tauri capabilities required by each reviewed feature.
5. Add Windows installer assets and signing/release configuration.
