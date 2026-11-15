# JARVIS — Ambient Presence, Conversation and Demonstration Modes

Status: Product/UX specification. This is the intended interaction contract; do not represent it as implemented until the UI, voice runtime, avatar and demo engine pass end-to-end acceptance tests.

## Core principle

JARVIS should feel like a calm, intelligent presence in the owner's private virtual office—not a dashboard that permanently covers the screen with cards. The default state is ambient, spacious and avatar-led. Information surfaces appear contextually when requested, when a task needs review, or when an important event requires attention.

## 1. Ambient Presence Mode (default)

- Full-screen or large central virtual office with the owner-representative avatar seated naturally.
- Warm executive-office environment with a subtle global globe/map visual in the background.
- JARVIS branding, a small connection indicator and a discreet voice-state indicator.
- Minimal bottom conversation affordance, such as "Hey JARVIS…" and a subtle waveform when the active session is listening or speaking.
- Hide navigation rails, agenda cards, agent lists, metrics and project widgets by default. Reveal controls on hover, keyboard shortcut, gesture or explicit request.
- No fabricated clock, weather, agenda, learning percentages, connected tool counts or live intelligence headlines. Display only values returned by real services, with timestamps and disconnected/unknown states.
- Respect reduced-motion, accessibility, privacy mode and compact layout.

## 2. Natural Conversation Mode

The owner can say "Hey JARVIS" and talk naturally without pressing a record button. Wake-word detection should be local where practical, with explicit microphone permission, a clear visible listening indicator, mute/pause and session-end controls. Ambient audio must not be continuously uploaded or retained before activation.

Conversation supports:
- Full-duplex turn-taking, interruptions/barge-in and resume.
- Streaming speech recognition and speech synthesis.
- Short spoken responses with optional visual details.
- Context from the current project/workspace only when authorised.
- Spoken clarification when the request is ambiguous.
- A text transcript that can be hidden or opened on demand.
- A quiet mode where JARVIS replies only visually or by text.

The avatar's mouth, gaze, posture and expressions follow actual voice/session events. The system must never fake listening, thinking, progress or task completion.

## 3. Contextual Workspace Mode

When the owner asks "show me my agenda", "open WorldScope", "compare these options", or "show the research", relevant panels slide in without replacing the office. Use progressive disclosure:
- One concise result first.
- Expand details only when requested.
- Use left/right panels or a floating translucent workspace for documents, maps, charts, browser pages, code, project boards and approvals.
- Allow pinning a useful panel, resizing, closing and returning to ambient presence.
- Keep the avatar visible as a conversational companion unless the owner chooses full-workspace mode.

Examples:
- "What's my agenda today?" opens a clean agenda panel populated from connected calendar/tasks.
- "Show my investor research" opens the relevant CRM/research results with sources and next actions.
- "Open the WorldScope newsroom" opens its workspace and editorial queue.
- "Compare these API providers" opens a side-by-side comparison with evidence, pricing date and caveats.

## 4. Demonstration / Presentation Mode

JARVIS can move beyond speech and demonstrate a concept:
- The avatar may transition from seated to standing, turn toward a virtual display, point, gesture, draw or walk through a staged explanation.
- A virtual presentation area can show diagrams, maps, timelines, product mockups, code diffs, workflows, charts, 3D objects or step-by-step instructions.
- JARVIS can narrate while highlighting the exact element being discussed.
- The owner can interrupt, ask "why?", request another angle, zoom in, or say "continue".
- Demo mode can be invoked by "show me", "demonstrate", "walk me through", "present this" or an explicit button.
- A demo can use a simulated example when labelled as a simulation; live actions must be separately authorised and visibly distinguished.
- Do not imply a real phone call, message, API action, website change or deployment occurred when only a demonstration was shown.

## 5. Action and approval interaction

The owner may say "call this person", "send this email", "publish this article" or "deploy this change". JARVIS should:
1. Clarify target/account/content if necessary.
2. Prepare the exact action and show a preview.
3. Explain consequences and risks.
4. Request explicit approval for sensitive actions.
5. Execute through the approved connector only after policy re-check.
6. Report the actual result, evidence and any failure.

A demonstration of a call or workflow is not a real call/action. Real phone calls, external messages, payments, publishing, destructive changes and production deployment require action-bound approval. Voice approval for high-impact actions should be confirmed in a secure UI.

## 6. Avatar performance and animation states

- Seated idle: relaxed posture, natural blink and subtle breathing.
- Listening: eyes/gaze attentive, small acknowledgement, microphone waveform.
- Speaking: accurate visemes/lip-sync, restrained hand gestures.
- Thinking: brief natural pause and thoughtful gaze; no fake "processing" loop.
- Explaining: seated gestures or optional standing presentation pose.
- Demonstrating: turns to display, points to actual highlighted content.
- Waiting for approval: calm neutral pose with explicit approval panel.
- Completed/failed: reflect the real verified tool outcome, not an animation guess.

The owner can select seated-only, expressive, standing presentation, minimal avatar or no-avatar mode. The avatar should be a user-approved likeness based on the supplied reference and must not be replaced with a generic person.

## 7. Founder work and personal workflows

Add contextual workspaces for:
- CEO Global Founder Office: agenda, priorities, investor pipeline, partnerships, contacts, meeting briefs, follow-ups and portfolio health.
- WorldScope News: newsroom planning, current research, source verification, article drafts, editorial review, media assets and publishing approvals.
- HANDLY: product roadmap, worker/customer journey QA, marketplace operations, support, developer tasks and investor materials.
- CareLink Africa: parent/expert waitlists, specialist recruitment, partnerships, content calendar and traction reporting.
- SENDLY: product development, payment provider research, compliance, risk, release readiness and partner tracking.
- Drive Secure: fleet hardware/vendors, device provisioning, GPS/video telematics, alerts, evidence, fleet analytics and customer operations.
- Creative Studio: brand assets, video scripts, thumbnails, image/video production and campaign planning.
- General Research & Intelligence: multi-source research, people/organisation discovery, public information verification, API discovery and technology comparisons.

Each workspace must use actual project data or clearly show that a connector is not yet connected. Keep project data isolated by default.

## 8. Visual and interaction rules

- The ambient home screen is intentionally uncluttered; it is not a permanent dashboard.
- Panels are contextual and dismissible.
- Use smooth, restrained transitions; avoid constant motion and excessive neon effects.
- Voice and keyboard/touch controls are both first-class.
- All actions have visible status: proposed, awaiting approval, running, succeeded, failed or simulated.
- Show source provenance and last-updated time for information that can become stale.
- Never show a live map, camera feed, news ticker, connected-service count, or learning count unless backed by a real connected source.

## 9. Acceptance tests

1. On launch, owner sees the seated owner-representative avatar in the uncluttered virtual office.
2. The default greeting is time-aware and says "CEO Global", never first name by default.
3. "Hey JARVIS" starts a session without a record-button press; microphone state is always visible.
4. Owner can interrupt speech and JARVIS resumes naturally.
5. Asking for agenda opens only the agenda panel and uses real connected data.
6. Asking to explain a concept invokes a demonstrative presentation with the avatar and supporting visual.
7. The avatar can switch seated/standing presentation poses with matching lip-sync and gestures.
8. A simulated call is clearly labelled simulated; a real call needs an approved telephony integration and explicit action approval.
9. Owner can dismiss all panels and return to ambient office mode immediately.
10. No fabricated data or unverified success states appear anywhere.
