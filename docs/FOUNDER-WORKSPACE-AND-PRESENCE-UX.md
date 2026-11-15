# JARVIS — Founder Workspace and Presence UX Decisions

Status: Product direction approved; this document describes intended UX, not completed UI/runtime functionality.

## Identity and greeting
- Product name is always JARVIS. Do not rename the assistant "CEO Global AI".
- Owner-facing greeting uses the preferred title "CEO Global" and local time: Good morning, CEO Global; Good afternoon, CEO Global; Good evening, CEO Global. Use the owner's configured timezone and a neutral fallback if time is unavailable.
- Do not greet the owner by first name by default.
- Owner identity shown in account/profile settings may use the verified full name; the conversational greeting remains CEO Global.

## Avatar direction
- The primary avatar represents the owner as a digital presence, based on the user's supplied reference photo, rather than a generic male assistant.
- Preserve recognisable visible characteristics from the reference (dark skin, short tightly curled hair, shaped beard and moustache, rectangular glasses) without inventing a different person.
- Avatar is seated in a virtual office/command environment, with selectable outfit, lighting, office background and optional alternate avatar modes.
- It must remain clearly the JARVIS interface: JARVIS branding and identity belong to the system, not to the avatar as a separate assistant character.
- Avatar asset must be user-approved and locally/licence controlled. Offer a non-avatar compact mode and privacy mode.
- Use facial blend shapes/visemes for speech, natural blink/gaze, listening/thinking/speaking states and interruptible speech. The avatar is a presentation layer; it must not imply unverified task progress.

## Voice and wake-word interaction
- Primary hands-free interaction: configurable wake phrase, default candidate "Hey JARVIS", followed by natural two-way conversation and barge-in.
- Push-to-talk remains available as a fallback, not the only interaction.
- Wake-word detection should run locally where feasible. Show a persistent, obvious microphone/listening indicator and a one-tap pause/disable control.
- Do not continuously upload ambient audio. Before wake phrase, local detection should discard audio frames; after activation, capture only the active session according to the user's settings.
- Provide explicit microphone permission, mute, session end, audio retention and transcript controls. Never covertly record.
- Optional proactive voice calls to the owner are opt-in, with caller identity, purpose and approval details shown; high-impact approvals require secure confirmation rather than ambiguous speech alone.
- Voice options should include a natural, calm, confident, professional voice; compare licensed voices and Nigerian-English pronunciation before selecting. Do not imitate a real person's voice without permission.

## Screen composition
- Desktop default: persistent navigation rail; central owner-avatar/workspace area; right-side agent/system/learning panels; bottom voice/text command bar.
- The main workspace must be responsive and modular. Users can collapse panels, move widgets, change density, switch to compact mode and choose light/dark theme.
- The screen should prioritise actual work state and active projects over decorative metrics. No fake percentages, fabricated learned-item counts, dummy connected integrations, or simulated live news in production UI.
- Show provider health, last successful sync, current microphone state, active jobs, approvals waiting, learning queue and source freshness using real backend data.
- Mobile interface is a companion layout, not a squeezed desktop screen: voice-first home, project cards, notifications, knowledge capture, and approval inbox.

## Founder workbench modules
Provide dedicated workspaces and skill packs for the owner's recurring work:
- WorldScope News: newsroom research, source verification, article drafting, editorial calendar, story assets and publishing approvals.
- HANDLY: product engineering, worker/customer journey QA, marketplace operations, investor materials and support workflows.
- CareLink Africa: expert/parent recruitment, partnerships, content, waitlist metrics and product operations.
- Sendly: fintech product planning, compliance research, integration/vendor evaluation and release checklists.
- Drive Secure: fleet telematics, device/vendor research, GPS/video event workflows and fleet operations.
- Founder office: investor discovery, outreach drafts, contact/CRM tracking, meeting preparation, business analysis and portfolio-wide priorities.
- Creative studio: thumbnails, brand assets, video scripts, voiceovers and campaign content.
- General operations: email/calendar, documents, spreadsheets, research, browser workflows and approved automation.

Each workspace uses shared identity, provider routing, memory, skill registry, approvals and audit; projects remain logically isolated and the user chooses what context is shared.

## Skills and learning UX
- A visible "Skills & Tools" area supports discover, inspect, install, configure, update, disable and uninstall.
- A visible "Knowledge Hub" supports URL capture, document import, approved source connectors, search, source citations, freshness, contradictions, correction and deletion.
- Each learning result shows what was captured, what was not accessible, source URL/date, confidence and whether it is merely indexed knowledge or a newly installed executable skill.
- Adding knowledge never silently grants website/account access or installs code.
- Include a learning review queue and user-controlled auto-learning rules for low-risk approved sources.

## Acceptance criteria
1. Correct JARVIS name and CEO Global time-aware greeting on desktop and mobile.
2. Avatar resembles the approved owner reference; user can reject/reselect avatar assets.
3. Wake phrase works hands-free with clear microphone state, local detection/privacy controls, barge-in and push-to-talk fallback.
4. No fabricated integration, news, learning, system-health or progress data.
5. Founder workspaces load real connected project data or clearly show disconnected/empty states.
6. Skill install and website learning have distinct, reviewable flows.
7. All sensitive actions remain protected by shared policy, exact-argument approval and audit logging.
