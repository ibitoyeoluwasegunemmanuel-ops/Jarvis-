# JARVIS Intelligence and Presence Vision

Status: Product direction for the cross-device foundation
Date: 2026-11-20

## Product definition

JARVIS is a personal AI operating system and executive companion. The avatar is its visible, conversational presence; it is not the product by itself. The product combines natural voice conversation, persistent personal context, visual understanding, a live application workspace, secure tool execution, and proactive cloud operations.

The system must preserve the existing Windows desktop, Flutter mobile client, FastAPI cloud API, Supabase identity/workspace model, local gateway, and project-sync foundation. New capabilities are additive and introduced through versioned migrations and backward-compatible APIs.

## Core interaction model

The user should be able to speak naturally while JARVIS speaks back. Voice and workspace interaction are concurrent:

1. The user asks for an answer or action.
2. JARVIS acknowledges and responds in natural speech.
3. If relevant, the workspace opens a live panel for the requested application, document, search, dashboard, or task.
4. JARVIS narrates what it is doing and streams useful results into the panel.
5. The user can interrupt, clarify, switch topics, or approve an action without losing context.
6. The avatar remains present while panels change.

Example: "JARVIS, open GitHub and show me the latest HANDLY changes." JARVIS speaks, opens the authenticated GitHub panel, retrieves the relevant repository activity through an authorised integration, and summarises the result. It must not claim to have accessed GitHub if the connector is not connected or the request failed.

## Avatar and presence

Support two interchangeable presentation identities:
- A consented, user-provided likeness animated for the user's own assistant.
- A designed female AI persona associated with the JARVIS identity.

The avatar layer is replaceable and must not own memory, authentication, tools, or business logic. It should support low-latency speech output, speech-aligned lip movement, gaze, listening/speaking/idle states, subtle expressions, and interruption handling. The assistant voice and visual identity should remain consistent across Windows and mobile, subject to device capabilities.

## Intelligence capabilities

### Conversational runtime
- Streaming speech recognition and speech synthesis.
- Turn-taking, barge-in, interruption, cancellation, and fast acknowledgement.
- Tool selection and multi-step reasoning with visible task progress.
- Context carryover across devices and sessions.
- Graceful fallback to text when audio/network services are unavailable.

### Personal memory and context
- Separate durable facts, preferences, project context, decisions, commitments, and short-lived conversation context.
- Store provenance, timestamps, confidence, and user controls for sensitive or uncertain inferences.
- Allow the user to inspect, correct, export, and delete supported memory records.
- Never infer or store a sensitive trait as fact merely from voice, face, or behaviour.
- Distinguish "the user said", "a connected source reports", and "the assistant inferred".

### Emotional and social intelligence
- Respond empathetically to explicit statements and conversational cues.
- Treat emotion recognition as uncertain, optional and user-controlled; ask rather than assume.
- Do not claim to feel human emotions or make clinical diagnoses.
- Adapt tone and pacing without manipulating the user or creating dependency.

### Visual awareness
- Accept explicit camera sessions, screenshots, images, and user-selected screen shares where supported.
- Explain what visual inputs are active and provide a visible camera/microphone state.
- Do not continuously record or monitor without clear user activation and persistent indicators.
- Provide a pause/stop control and avoid retaining raw media unless the user explicitly chooses a supported storage action.

### Live workspace and application orchestration
- Dockable panels for connected apps, browser pages, files, project boards, calendars, search results, and task progress.
- Keep the avatar and conversation visible while a panel opens or changes.
- Support deep links and embedded experiences where permitted; otherwise open a secure browser panel or external app.
- Clearly label which account and workspace are active.
- Avoid exposing access tokens to the frontend or avatar provider.

### Agents and execution
- Read-only actions can run within granted scopes.
- Writes, external messages, purchases, account changes, deployments, and destructive operations require explicit confirmation unless the user has configured a narrowly scoped policy.
- Show the intended action, target, data to be sent, and result.
- Use idempotency keys, audit logs, retries with limits, and cancellation for long-running work.
- Never pretend an action succeeded before receiving a verified result.

### Proactive cloud operations
- Cloud workers continue approved monitoring when the Windows PC is off.
- Scheduled and event-driven checks for project status, deadlines, approvals, deliveries, and awaited responses.
- Deliver notifications to connected devices with user-configurable quiet hours and priority.
- Cloud workers use scoped credentials, encrypted secrets, least privilege, and auditable access.

## Cross-device experience

Windows is the full control room with avatar, voice, and multi-panel workspace. Android is the mobile companion for voice, alerts, quick approvals, workspace summaries, and remote commands. Both use the same authenticated cloud identity and workspace. Conversations, tasks, and permitted context should synchronize through the cloud rather than peer-to-peer exposure of the local gateway.

The local FastAPI gateway remains bound to loopback. Mobile clients must never connect directly to the Windows local gateway over the public internet.

## Proposed implementation sequence

1. Stabilise current mobile and Windows builds; retain the existing security and data foundations.
2. Deploy the cloud API safely with dedicated runtime credentials and verify end-to-end authentication.
3. Implement the conversational runtime abstraction: streaming input/output, session state, interruption, and provider-independent interfaces.
4. Build the live workspace shell with dockable panels and a persistent avatar/conversation region.
5. Add one verified integration at a time, beginning with GitHub read-only repository and pull-request views.
6. Add memory service with provenance, consent controls, retention and correction/deletion paths.
7. Add cloud monitoring workers and push notifications.
8. Add visual awareness with explicit activation and visible controls.
9. Add tightly scoped agent execution and confirmation policies.
10. Introduce avatar choices and speech-synchronised animation; benchmark latency and accessibility across devices.

## Acceptance criteria for the experience

- User can speak, hear a spoken response, and interrupt naturally.
- JARVIS can open a workspace panel while continuing the conversation.
- A GitHub request opens the correct authorised repository and reports actual retrieved information.
- The same workspace and conversation context are available on Windows and Android after sign-in.
- Approved cloud monitoring continues while Windows is offline.
- Every external write action has an understandable confirmation and an audit record.
- Camera/microphone use is explicit, visible, and stoppable.
- Avatar identity can change without losing memory, tools, or account context.

## Known current gaps

The current foundation has Supabase authentication, workspaces, device registration, project metadata sync, and cloud API database policies. It does not yet provide a deployed public cloud API, streaming voice conversation, avatar rendering, dockable live workspace panels, long-term personal memory service, push notifications, background cloud monitoring workers, camera understanding, or broad two-way sync. These are future implementation milestones, not existing features.
