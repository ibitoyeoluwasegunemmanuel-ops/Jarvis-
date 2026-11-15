# JARVIS — Extensible Skills, Knowledge and Provider Architecture

Status: Architecture direction approved for implementation; individual integrations remain unimplemented until their adapters, credentials, tests and permissions are delivered.

## Product requirement

JARVIS is an expandable personal AI operating environment. It must be able to acquire new knowledge, install or connect new skills, switch model/search providers, and operate across desktop, mobile and web interfaces without replacing its central identity, memory, policy or audit system.

The Skill & Knowledge Centre is a first-class product area, not a developer-only configuration file.

## 1. Four independent extension types

1. **Model providers** — reasoning, coding, vision, audio and embedding models. Provider adapters expose a common internal contract while preserving model-specific capabilities and limitations.
2. **Search and research providers** — web/metasearch, news, academic papers, public datasets, maps/geospatial, finance, flight, vessel, weather and public-camera indexes.
3. **App/API integrations** — authenticated actions and events in external services such as email, calendar, files, GitHub, CRM, messaging and business tools.
4. **Skills and specialist agents** — versioned workflows that combine instructions, knowledge sources, tools, evaluations and permission scopes.

A model provider is not an app connector; a search engine is not a source of truth; and a learned website is not automatically an authorised integration.

## 2. Candidate ecosystem to evaluate

These are candidate adapters, not claims that they have already been connected.

| Need | Candidate | Intended role | Cost / caveat |
|---|---|---|---|
| Multi-model gateway | OpenRouter | One API for multiple model vendors, including free model variants | Free variants are rate-limited and availability changes; route/fallback must be tested |
| App integrations | Composio | Discover, authenticate and execute actions across a large app toolkit catalogue | Requires account/API key for hosted service; inspect current plan, permissions and data terms |
| API authentication/integration | Nango | OAuth, token refresh and API connection management | Open source/self-hostable with feature/plan distinctions; not every hosted feature is free |
| Self-hosted metasearch | SearXNG | Query multiple configured search engines through one local search API | Self-hosted; individual upstream engines can throttle/block; configure JSON output and respect terms |
| Search API | Brave Search | Independent web index and structured search/context | Has monthly free credits, then usage pricing; not a permanent unlimited free API |
| Public API discovery | public-apis/public-apis and APIs.guru | Discover APIs and OpenAPI specifications for new skills | Catalogues are discovery aids, not guarantees of uptime, free use, safety or quality |
| Agent tool protocol | MCP | Standardised tool discovery and invocation across compatible servers | Every server still needs trust review, scopes, isolation and policy enforcement |

Primary references:
- OpenRouter: https://openrouter.ai/docs and https://openrouter.ai/collections/free-models/
- Composio: https://github.com/ComposioHQ/composio and https://docs.composio.dev/
- Nango: https://github.com/NangoHQ/nango
- SearXNG: https://github.com/searxng/searxng and https://docs.searxng.org/dev/search_api.html
- Brave Search API: https://brave.com/search/api/
- Public APIs: https://github.com/public-apis/public-apis
- APIs.guru: https://github.com/APIs-guru/openapi-directory
- MCP: https://modelcontextprotocol.io/

## 2A. Additional low-cost provider candidates (verified Nov 15, 2026)

| Need | Candidate | Current free allowance / role | Integration decision |
|---|---|---|---|
| Unified LLM adapter and self-hosted gateway | LiteLLM | Open-source interface for 100+ model providers; retries, fallbacks and an OpenAI-compatible proxy. LiteLLM itself does not make upstream inference free. | Use as a provider abstraction candidate; keep JARVIS policy, approvals and secrets outside the proxy. |
| Free hosted model trials | OpenRouter | Free model variants are available, but are rate-limited. Current free-variant limit shown in its docs: 20 requests/minute and 50/day until the account has purchased qualifying credits. | Add as optional provider, with per-model allowlist, daily budget and fallback to local models. |
| Multi-provider inference | Hugging Face Inference Providers | Free accounts currently receive $0.10 monthly inference credits (subject to change); paid usage is available. | Useful for testing multiple model vendors through one token; do not treat as unlimited free inference. |
| AI-focused web search | Tavily | Current Researcher free tier lists 1,000 API credits/month with no credit card required. | Add as an independent search adapter alongside SearXNG; enforce monthly quota. |
| Search API | Brave Search | Current Search plan includes $5 monthly credits; published price is $5 per 1,000 requests. It is not an unlimited free plan. | Optional independent index for corroboration and structured web/news results. |

Official references:
- LiteLLM: https://docs.litellm.ai/docs/
- OpenRouter free models and limits: https://openrouter.ai/collections/free-models/ and https://openrouter.ai/docs/api-reference/limits
- Hugging Face pricing: https://huggingface.co/docs/inference-providers/pricing
- Tavily pricing: https://www.tavily.com/pricing
- Brave Search API: https://brave.com/search/api/
- SearXNG: https://docs.searxng.org/

**Recommended JARVIS combination:** LiteLLM as an optional model-routing layer; OpenRouter and Hugging Face as hosted model sources; Ollama/local models for private offline-capable inference; SearXNG for self-hosted metasearch; Tavily and Brave as separately configurable research sources. JARVIS must query multiple search providers when appropriate, compare results, retain citations and disclose which sources were actually queried. Never send private project data to external providers unless the owner has enabled that provider for that data class.

## 3. Provider routing

Implement a provider registry and capability-aware router.

- Store provider metadata: provider ID, endpoint, supported modalities, context window, tool-call support, structured output support, streaming, region, pricing, rate limits, retention/data policy and health.
- Select a provider based on task requirements, quality, latency, availability, privacy and user-configured budget.
- Support explicit preferred provider, automatic routing, and safe fallback.
- Never silently send private project files or secrets to a new provider. Require explicit provider/data-sharing configuration.
- Record provider/model/version and relevant usage metadata with each run.
- Free model endpoints are best-effort: quotas, model availability, terms and data policies can change. Do not advertise free as unlimited or production guaranteed.
- Keep embeddings, reranking, OCR, ASR, TTS and vision as separate capability adapters; not every chat model supports them.

## 4. Search and research federation

Search adapters should expose a common result shape: title, URL, snippet/content, source/provider, published/updated time when available, retrieval time, language, licence/usage metadata, and confidence signals.

Research workflow:
1. Classify the question and select suitable source categories.
2. Query more than one configured source when the question warrants it.
3. Deduplicate canonical URLs and cluster related claims.
4. Open primary sources and corroborate consequential claims.
5. Keep quotations short and retain provenance.
6. Mark disagreement, missing evidence, freshness and confidence.
7. Store a source-linked research record in the knowledge library when the user asks or an approved learning rule applies.

SearXNG can be the self-hosted broad metasearch adapter; Brave or specialist providers can be optional independent sources. Never claim that every search engine is queried unless the selected instance's actual configuration confirms it.

## 5. Skill manifest and lifecycle

Every installable skill must declare:
- Stable ID, display name, version, publisher/owner, description and category.
- Entry point and runtime type (built-in, MCP server, HTTP API, local worker or workflow).
- Input/output JSON schemas and examples.
- Required permissions/scopes, domains, data classes and risk tier.
- Network, filesystem, process and account requirements.
- Secret references (never literal secret values).
- Dependencies, licence, update source, integrity/hash and compatibility.
- Test/evaluation suite, health check, timeout, retry and rollback strategy.

Lifecycle: Discover → inspect publisher/source and licence → review permissions → sandbox/test → owner approves installation → enable → monitor → update with diff → rollback/disable/uninstall.

A skill cannot grant itself new permissions, change policy, read unrelated secrets, or silently install dependencies. Remote MCP servers and API descriptions are untrusted input until reviewed.

## 6. Knowledge learning and personalisation

Build a source-ingestion pipeline:
- Inputs: user-provided URL, uploaded documents, explicitly connected drives/repos, approved browser sessions, selected emails/calendar records and user feedback.
- Fetch only permitted public or authorised content. Respect robots/access controls, copyright, terms and rate limits; do not bypass login, paywalls or technical restrictions.
- Extract text and metadata; preserve canonical URL, title, author/publisher, publication date, fetched date, content hash and page/section references.
- Chunk and index with lexical + vector retrieval; keep original source and derived summaries linked.
- Separate facts, preferences, decisions, procedures, hypotheses and transient observations.
- Record confidence, source quality, sensitivity, expiry/freshness and review status.
- Detect duplicates and contradictions; ask the owner before treating disputed or sensitive inferred preferences as durable profile facts.
- Support correction, source deletion, retention controls, export and re-indexing.
- Never claim the base model was retrained. Learning means retrieval/indexing and approved profile/workflow updates unless a separately evaluated fine-tuning pipeline is deliberately added.

Learning policies:
- **Learn now:** ingest the specific source and report what was saved.
- **Suggest learning:** propose useful new knowledge or skill, ask before persistent storage/install.
- **Approved auto-learning:** only pre-authorised low-risk source categories and retention rules.
- Never learn passwords, authentication secrets, payment credentials or highly sensitive personal data into semantic memory.

## 7. Personal operating profile

Maintain an owner-controlled profile of explicit preferences, recurring workflows, active projects, preferred communication style, approved tools and decision history. Distinguish explicit user statements from inferred patterns. Show why an item was learned and from which source. Provide review, correction, expiry and deletion controls.

## 8. Tool execution and approvals

All connectors and skills call the shared policy engine. Tool calls are typed, schema-validated, scoped and audited. Read-only lookup may be low risk; sending, publishing, contacting people, changing records, payments, deleting data, installing code and production deployment require action-specific approval. Approval binds the exact tool, account, target, arguments and expiry. Re-check policy immediately before execution. Use idempotency and verify outcomes.

Credentials live in an encrypted secret vault or connector-managed auth store. Never place API keys in prompts, renderer state, source control, logs or knowledge embeddings. Provide disconnect/revoke and token rotation.

## 9. Cross-device product

The desktop, mobile and web clients use the same authenticated JARVIS service and owner-controlled memory/skill registry. Mobile should support chat, voice, camera/document sharing, notifications and action approvals; desktop adds the supervised local computer operator; web provides remote workspace access. Keep local-only permissions on the local desktop and do not expose them through cloud APIs.

Voice calls to the owner are an optional telephony adapter. They must be opt-in, identify JARVIS clearly, disclose the purpose, provide a secure approval interaction and never treat a spoken ambiguous response as approval for high-impact actions.

## 10. Avatar and virtual office

The avatar is a replaceable presentation layer, not the model or orchestrator. Use a licensed GLB/GLTF character with facial blend shapes/visemes, idle/listening/thinking/speaking/action-complete states, gaze and expression controls. Provide male/female/other selectable characters and accessible compact/no-avatar modes. Voice and avatar state must reflect actual session state; do not fake tool progress or claim an action succeeded based on animation.

## 11. Delivery sequence and exit criteria

1. Provider registry + OpenRouter adapter + local model option; demonstrate model selection, fallback, capability and privacy controls.
2. Search federation with SearXNG adapter and independent search adapter; demonstrate source deduplication, citations and outage handling.
3. Skill & Knowledge Centre UI; add/inspect/approve/enable/disable skill and display permissions.
4. URL/document learning pipeline; demonstrate provenance, freshness, deduplication, contradiction flags and deletion.
5. One app-integration adapter (GitHub first) behind scoped auth and approval; then evaluate Composio/Nango as integration backends.
6. Specialist orchestration using shared tools and policy; no agent identity or permission supplied by model output.
7. Avatar prototype and voice; evaluate Nigerian English, interruption, latency and asset licence.
8. Shared mobile/web client and optional owner-call workflow.

Each stage requires tests, threat-model review, cost/rate-limit review and a working end-to-end demonstration. No feature is considered implemented merely because it appears in this architecture document.
