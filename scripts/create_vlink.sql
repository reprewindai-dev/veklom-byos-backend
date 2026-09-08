CREATE TABLE IF NOT EXISTS vlink_bindings (
    id VARCHAR(36) PRIMARY KEY,
    vlink_id VARCHAR(128) NOT NULL,
    api_key_id VARCHAR(36) NOT NULL,
    workspace_id VARCHAR(36) NOT NULL,
    connection_ref VARCHAR(128) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    CONSTRAINT vlink_bindings_api_key_id_fkey FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    CONSTRAINT vlink_bindings_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT vlink_vlink_id_key UNIQUE (vlink_id),
    CONSTRAINT vlink_conn_ref_key UNIQUE (connection_ref)
);
