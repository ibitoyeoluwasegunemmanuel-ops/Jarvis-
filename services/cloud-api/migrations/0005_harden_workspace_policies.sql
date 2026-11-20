-- Harden the identity helper against search_path shadowing and avoid a
-- broad FOR ALL policy that also duplicates the project's SELECT policy.
CREATE OR REPLACE FUNCTION jarvis.current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
SET search_path = ''
AS $$
    SELECT nullif(pg_catalog.current_setting('jarvis.user_id', true), '')::uuid
$$;

DROP POLICY IF EXISTS project_member_write ON jarvis.projects;

CREATE POLICY project_member_insert ON jarvis.projects
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = projects.workspace_id
              AND wm.user_id = jarvis.current_user_id()
              AND wm.role IN ('owner', 'admin', 'member')
        )
    );

CREATE POLICY project_member_update ON jarvis.projects
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = projects.workspace_id
              AND wm.user_id = jarvis.current_user_id()
              AND wm.role IN ('owner', 'admin', 'member')
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = projects.workspace_id
              AND wm.user_id = jarvis.current_user_id()
              AND wm.role IN ('owner', 'admin', 'member')
        )
    );

CREATE POLICY project_member_delete ON jarvis.projects
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM jarvis.workspace_members wm
            WHERE wm.workspace_id = projects.workspace_id
              AND wm.user_id = jarvis.current_user_id()
              AND wm.role IN ('owner', 'admin', 'member')
        )
    );
