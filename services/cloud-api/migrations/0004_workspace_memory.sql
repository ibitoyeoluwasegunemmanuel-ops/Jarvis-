-- Workspace-scoped memory shared by authenticated JARVIS clients.
CREATE TABLE jarvis.memory_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES jarvis.workspaces(id) ON DELETE CASCADE,
    created_by uuid NOT NULL,
    category text NOT NULL CHECK (
        category IN ('preference', 'fact', 'decision', 'note', 'reference')
    ),
    content text NOT NULL CHECK (length(content) BETWEEN 1 AND 4000),
    source_ref text NOT NULL DEFAULT '' CHECK (length(source_ref) <= 1000),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX memory_entries_workspace_created
    ON jarvis.memory_entries(workspace_id, created_at DESC);

ALTER TABLE jarvis.memory_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY memory_member_read ON jarvis.memory_entries
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = memory_entries.workspace_id
              AND wm.user_id = jarvis.current_user_id()
        )
    );

CREATE POLICY memory_member_insert ON jarvis.memory_entries
    FOR INSERT WITH CHECK (
        created_by = jarvis.current_user_id()
        AND EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = memory_entries.workspace_id
              AND wm.user_id = jarvis.current_user_id()
              AND wm.role IN ('owner', 'admin', 'member')
        )
    );

GRANT SELECT, INSERT ON jarvis.memory_entries TO jarvis_api;
