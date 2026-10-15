-- ============================================================
-- Migration 005: Subscription Lifecycle
-- Pod Alpha - Wallet Service
-- ============================================================

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id VARCHAR(255) NOT NULL,

    tier VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',

    credits_per_period NUMERIC(20, 8) NOT NULL,

    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,

    cancelled_at TIMESTAMPTZ NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT subscriptions_tier_check
        CHECK (tier IN ('FREE', 'STARTER', 'PROFESSIONAL', 'ENTERPRISE')),

    CONSTRAINT subscriptions_status_check
        CHECK (status IN ('ACTIVE', 'CANCELLED', 'EXPIRED')),

    CONSTRAINT subscriptions_credits_positive_check
        CHECK (credits_per_period >= 0),

    CONSTRAINT subscriptions_period_check
        CHECK (current_period_end > current_period_start)
);

-- A user can have only one active subscription.
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_subscriptions_active_user
ON subscriptions (user_id)
WHERE status = 'ACTIVE';

-- Fast lookup by user.
CREATE INDEX IF NOT EXISTS
    idx_subscriptions_user_id
ON subscriptions (user_id);

-- Fast lookup for renewal processing.
CREATE INDEX IF NOT EXISTS
    idx_subscriptions_period_end
ON subscriptions (current_period_end);

-- Fast lookup of active subscriptions.
CREATE INDEX IF NOT EXISTS
    idx_subscriptions_status
ON subscriptions (status);

-- Automatically maintain updated_at.
CREATE OR REPLACE FUNCTION update_subscription_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_subscriptions_updated_at
ON subscriptions;

CREATE TRIGGER trg_subscriptions_updated_at
BEFORE UPDATE ON subscriptions
FOR EACH ROW
EXECUTE FUNCTION update_subscription_updated_at();