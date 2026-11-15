-- Stable mapping from each local desktop project to one cloud workspace row.
ALTER TABLE jarvis.projects
    ADD COLUMN source_local_id text;

UPDATE jarvis.projects
SET source_local_id = 'legacy-' || id::text
WHERE source_local_id IS NULL;

ALTER TABLE jarvis.projects
    ALTER COLUMN source_local_id SET NOT NULL;

ALTER TABLE jarvis.projects
    ADD CONSTRAINT projects_workspace_source_local_unique
    UNIQUE (workspace_id, source_local_id);

-- Only workspace owners, admins and members can write project metadata.
-- Viewers retain read-only access through the SELECT policy in 0001.
CREATE POLICY project_member_write ON jarvis.projects
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = workspace_id
              AND wm.user_id = jarvis.current_user_id()
              AND wm.role IN ('owner', 'admin', 'member')
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = workspace_id
              AND wm.user_id = jarvis.current_user_id()
              AND wm.role IN ('owner', 'admin', 'member')
        )
    );

GRANT INSERT, UPDATE ON jarvis.projects TO jarvis_api;
