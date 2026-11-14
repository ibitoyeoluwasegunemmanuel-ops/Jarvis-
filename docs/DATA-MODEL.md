# JARVIS — Data Model

Status: The cloud/multi-user schema below is the logical target model. The first local Windows build currently implements a smaller SQLite subset for owner authentication, projects, tasks, and audit events; it does not yet implement cloud identity, workspace membership, or production RLS.

## 1. Modelling rules
- Tenant/workspace scope on every tenant-owned record.
- Explicit project association where relevant.
- UUID primary keys and UTC timestamps.
- Money stored as integer minor units plus ISO currency code.
- Secrets live outside ordinary application tables in a secrets manager or encrypted vault.
- Vector search filters tenant, workspace, project, and sensitivity before ranking.

## 2. Identity and tenancy
### users
id, email, display_name, status, created_at, updated_at

### workspaces
id, name, owner_user_id, workspace_type, timezone, locale, created_at, updated_at

### workspace_members
id, workspace_id, user_id, role, status, created_at

### devices
id, workspace_id, user_id, device_name, platform, os_version, app_version, last_seen_at, revoked_at

### user_preferences
id, user_id, workspace_id, preference_key, preference_value_json, updated_at

## 3. Project brain
### projects
id, workspace_id, name, slug, description, status, priority, owner_user_id, repository_url, environment_json, last_verified_at, created_at, updated_at

### project_members
id, project_id, user_id, role

### project_tasks
id, workspace_id, project_id, title, description, status, priority, due_at, assignee_user_id, source_conversation_id, created_at, updated_at, completed_at

### project_milestones
id, project_id, title, description, target_at, status, completed_at

### project_decisions
id, project_id, title, decision, rationale, alternatives_json, decided_by, decided_at, review_at, source_ref

### project_risks
id, project_id, title, description, likelihood, impact, mitigation, status, owner_user_id, reviewed_at

### project_updates
id, project_id, summary, status_snapshot_json, evidence_json, confidence, observed_at, created_by

## 4. Conversations and memory
### conversations
id, workspace_id, user_id, project_id, title, mode, started_at, ended_at, retention_policy

### messages
id, conversation_id, role, content_text, content_json, input_modality, created_at, redaction_state

### memory_items
id, workspace_id, project_id, memory_type, content, sensitivity, confidence, source_type, source_id, valid_from, valid_until, last_verified_at, created_by, created_at, updated_at

### memory_embeddings
id, memory_item_id, embedding_model, embedding vector, created_at

### memory_feedback
id, memory_item_id, user_id, feedback_type, corrected_content, created_at

Memory supports provenance, confidence, freshness, correction, export, and deletion.

## 5. Documents and media
### assets
id, workspace_id, project_id, asset_type, object_key, mime_type, size_bytes, checksum, sensitivity, retention_until, created_by, created_at

### asset_extractions
id, asset_id, extractor, extracted_text, metadata_json, status, created_at

### capture_sessions
id, workspace_id, user_id, source_type, consented_at, started_at, ended_at, retention_policy, status

Raw camera/screen/audio is not stored by default. Save only on user request or when a disclosed feature requires short-lived processing.

## 6. Agents and execution
### agent_runs
id, workspace_id, project_id, conversation_id, parent_run_id, agent_role, objective, plan_json, status, started_at, finished_at, model_provider, model_name, usage_json

### tool_definitions
id, name, version, input_schema_json, output_schema_json, risk_tier, required_scopes_json, enabled, verification_method

### tool_runs
id, workspace_id, agent_run_id, tool_definition_id, input_redacted_json, output_redacted_json, status, idempotency_key, started_at, finished_at, verification_json

### approvals
id, workspace_id, user_id, tool_run_id, action_hash, action_summary, target, parameters_redacted_json, risk_tier, status, requested_at, expires_at, decided_at, decision_reason

### audit_events
id, workspace_id, actor_type, actor_id, event_type, resource_type, resource_id, action_hash, policy_result, metadata_redacted_json, occurred_at, correlation_id

### scheduled_jobs
id, workspace_id, created_by, job_type, schedule_json, scope_json, enabled, next_run_at, last_run_at, last_result_json

## 7. Integrations and permissions
### integrations
id, workspace_id, provider, display_name, connection_status, granted_scopes_json, connected_by, connected_at, last_used_at, revoked_at

### integration_secret_refs
id, integration_id, secret_manager_ref, key_version, rotated_at

The secret reference points to encrypted secret storage. No plaintext tokens here.

### permission_grants
id, workspace_id, principal_type, principal_id, resource_type, resource_id, scopes_json, granted_by, granted_at, expires_at, revoked_at

### policy_rules
id, workspace_id, subject_selector_json, resource_selector_json, action_selector_json, effect, conditions_json, priority, enabled

## 8. Analytics and usage
### usage_events
id, workspace_id, user_id, provider, model, input_units, output_units, estimated_cost_minor, currency, event_at, metadata_redacted_json

### analytics_jobs
id, workspace_id, project_id, source_asset_id, analysis_type, parameters_json, status, result_asset_id, created_at, completed_at

### data_quality_findings
id, analytics_job_id, column_name, finding_type, severity, details_json, created_at

## 9. Constraints and relationships
- Workspace ownership and membership are explicit; projects belong to one workspace.
- Project artefacts cannot cross workspace/project permission scope.
- Tool runs belong to an agent run and workspace.
- Approval references one exact tool run/action hash.
- Integrations belong to one workspace and have revocable scoped grants.
- Embeddings cascade-delete with memory items.
- Asset deletion removes object storage and derived extractions in one workflow.
- Idempotency keys unique within workspace and tool definition.

## 10. Indexing
B-tree indexes for workspace/project/status/due dates/timestamps. Unique indexes for workspace slugs and scoped idempotency. GIN only for JSONB query patterns that justify it. pgvector HNSW/IVFFlat selected after measuring corpus size and latency. Full-text search always applies access filters before exposure.

## 11. Row-level security
Enable RLS on every tenant-owned table. Policies derive identity and workspace membership from trusted claims/database functions. Never trust client-supplied workspace_id as proof of access. Test allowed and denied access for every table and RPC. Service-role keys stay server-side.

## 12. Migration and deletion
Version migrations; review destructive changes and take verified backups; test against anonymised data. Export user data in interoperable formats. Deletion covers relational rows, embeddings, object storage, caches, and scheduled jobs. Retain minimal security records only where legally required and disclose retention.
