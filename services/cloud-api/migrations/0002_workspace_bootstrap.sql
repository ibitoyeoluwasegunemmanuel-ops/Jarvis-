-- Workspace self-service bootstrap. Run after 0001 with a migration owner.
CREATE OR REPLACE FUNCTION jarvis.can_bootstrap_workspace(target_workspace uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, jarvis
AS $$
    SELECT EXISTS (
        SELECT 1 FROM jarvis.workspaces w
        WHERE w.id = target_workspace
          AND w.owner_user_id = jarvis.current_user_id()
    )
$$;

REVOKE ALL ON FUNCTION jarvis.can_bootstrap_workspace(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION jarvis.can_bootstrap_workspace(uuid) TO jarvis_api;

CREATE POLICY workspace_owner_insert ON jarvis.workspaces
    FOR INSERT WITH CHECK (owner_user_id = jarvis.current_user_id());
CREATE POLICY workspace_owner_membership_insert ON jarvis.workspace_members
    FOR INSERT WITH CHECK (
        user_id = jarvis.current_user_id()
        AND role = 'owner'
        AND jarvis.can_bootstrap_workspace(workspace_id)
    );

GRANT INSERT ON jarvis.workspaces, jarvis.workspace_members TO jarvis_api;
