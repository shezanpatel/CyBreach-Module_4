CREATE TABLE user_profile (
    user_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
    current_streak INTEGER NOT NULL DEFAULT 0,
    last_completion_time TIMESTAMPTZ,
    verified_activity_time TIMESTAMPTZ,

    CONSTRAINT pk_user_profile
        PRIMARY KEY (user_id, tenant_id)
);