-- Owner bootstrap policies. The workspace SELECT policy in 0001 allows an
-- authenticated owner to read their own workspace before membership exists.
CREATE POLICY workspace_owner_insert ON jarvis.workspaces
    FOR INSERT WITH CHECK (owner_user_id = jarvis.current_user_id());

CREATE POLICY workspace_owner_membership_insert ON jarvis.workspace_members
    FOR INSERT WITH CHECK (
        user_id = jarvis.current_user_id()
        AND role = 'owner'
        AND EXISTS (
            SELECT 1 FROM jarvis.workspaces w
            WHERE w.id = workspace_id
              AND w.owner_user_id = jarvis.current_user_id()
        )
    );

GRANT INSERT ON jarvis.workspaces, jarvis.workspace_members TO jarvis_api;
