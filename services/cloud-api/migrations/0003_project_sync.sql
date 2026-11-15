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

CREATE OR REPLACE FUNCTION jarvis.can_write_workspace(target_workspace uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, jarvis
AS $$
    SELECT EXISTS (
        SELECT 1 FROM jarvis.workspace_members wm
        WHERE wm.workspace_id = target_workspace
          AND wm.user_id = jarvis.current_user_id()
          AND wm.role IN ('owner', 'admin', 'member')
    )
$$;

REVOKE ALL ON FUNCTION jarvis.can_write_workspace(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION jarvis.can_write_workspace(uuid) TO jarvis_api;

CREATE POLICY project_member_write ON jarvis.projects
    FOR ALL
    USING (jarvis.can_write_workspace(workspace_id))
    WITH CHECK (jarvis.can_write_workspace(workspace_id));

GRANT INSERT, UPDATE ON jarvis.projects TO jarvis_api;
