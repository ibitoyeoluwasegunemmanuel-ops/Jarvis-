-- Apply with a migration/owner role. Runtime DATABASE_URL must use a
-- separate role with NOBYPASSRLS and no ownership of these tables.
CREATE SCHEMA IF NOT EXISTS jarvis;

CREATE TABLE IF NOT EXISTS jarvis.workspaces (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    owner_user_id uuid NOT NULL,
    timezone text NOT NULL DEFAULT 'Africa/Lagos',
    locale text NOT NULL DEFAULT 'en-NG',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jarvis.workspace_members (
    workspace_id uuid NOT NULL REFERENCES jarvis.workspaces(id) ON DELETE CASCADE,
    user_id uuid NOT NULL,
    role text NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS jarvis.devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES jarvis.workspaces(id) ON DELETE CASCADE,
    user_id uuid NOT NULL,
    device_name text NOT NULL CHECK (length(device_name) BETWEEN 1 AND 100),
    platform text NOT NULL CHECK (platform IN ('windows', 'android', 'ios', 'web')),
    os_version text NOT NULL DEFAULT '',
    app_version text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz
);

CREATE TABLE IF NOT EXISTS jarvis.projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES jarvis.workspaces(id) ON DELETE CASCADE,
    name text NOT NULL,
    slug text NOT NULL,
    description text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'active',
    priority text NOT NULL DEFAULT 'normal',
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, slug)
);

CREATE TABLE IF NOT EXISTS jarvis.monitoring_alerts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES jarvis.workspaces(id) ON DELETE CASCADE,
    severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    title text NOT NULL,
    summary text NOT NULL,
    source_ref text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'open'
      CHECK (status IN ('open', 'acknowledged', 'resolved')),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    acknowledged_at timestamptz
);

CREATE INDEX IF NOT EXISTS devices_workspace_last_seen
    ON jarvis.devices(workspace_id, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS projects_workspace_updated
    ON jarvis.projects(workspace_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS alerts_workspace_status_last_seen
    ON jarvis.monitoring_alerts(workspace_id, status, last_seen_at DESC);

CREATE OR REPLACE FUNCTION jarvis.current_user_id()
RETURNS uuid LANGUAGE sql STABLE AS $$
    SELECT nullif(current_setting('jarvis.user_id', true), '')::uuid
$$;

ALTER TABLE jarvis.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE jarvis.workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE jarvis.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE jarvis.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE jarvis.monitoring_alerts ENABLE ROW LEVEL SECURITY;

-- A workspace owner can read their own newly-created workspace before their
-- first membership row is inserted. Other access is membership-scoped.
CREATE POLICY workspace_member_read ON jarvis.workspaces
    FOR SELECT USING (
        owner_user_id = jarvis.current_user_id()
        OR EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = id
              AND wm.user_id = jarvis.current_user_id()
        )
    );

CREATE POLICY workspace_member_read_self ON jarvis.workspace_members
    FOR SELECT USING (user_id = jarvis.current_user_id());

CREATE POLICY device_owner_all ON jarvis.devices
    FOR ALL USING (
        user_id = jarvis.current_user_id()
        AND EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = devices.workspace_id
              AND wm.user_id = jarvis.current_user_id()
        )
    )
    WITH CHECK (
        user_id = jarvis.current_user_id()
        AND EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = monitoring_alerts.workspace_id
              AND wm.user_id = jarvis.current_user_id()
        )
    );

CREATE POLICY project_member_read ON jarvis.projects
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = workspace_id
              AND wm.user_id = jarvis.current_user_id()
        )
    );

CREATE POLICY alert_member_read ON jarvis.monitoring_alerts
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = workspace_id
              AND wm.user_id = jarvis.current_user_id()
        )
    );

GRANT USAGE ON SCHEMA jarvis TO jarvis_api;
GRANT SELECT ON jarvis.workspaces, jarvis.workspace_members,
    jarvis.projects, jarvis.monitoring_alerts TO jarvis_api;
GRANT SELECT, INSERT, UPDATE ON jarvis.devices TO jarvis_api;
