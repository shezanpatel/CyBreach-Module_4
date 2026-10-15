-- ============================================================
-- Migration 007: Budget Alerts
-- Pod Alpha - Wallet Service
-- ============================================================
--
-- Purpose:
--   Store configurable wallet budget thresholds.
--
--   When a wallet balance drops below the configured threshold,
--   the wallet service can publish a notification event.
--
-- IMPORTANT:
--   This table does not modify wallet balances or ledger records.
-- ============================================================

CREATE TABLE IF NOT EXISTS budget_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id VARCHAR(100) NOT NULL,
    currency VARCHAR(3) NOT NULL,

    threshold NUMERIC(18, 2) NOT NULL,

    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    last_triggered_at TIMESTAMPTZ NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT budget_alerts_threshold_non_negative
        CHECK (threshold >= 0),

    CONSTRAINT budget_alerts_currency_length
        CHECK (char_length(currency) = 3),

    CONSTRAINT budget_alerts_unique_wallet
        UNIQUE (user_id, currency)
);

CREATE INDEX IF NOT EXISTS
    idx_budget_alerts_user_currency
ON budget_alerts (
    user_id,
    currency
);

CREATE INDEX IF NOT EXISTS
    idx_budget_alerts_enabled
ON budget_alerts (
    is_enabled
);

CREATE OR REPLACE FUNCTION update_budget_alert_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS
    trg_budget_alerts_updated_at
ON budget_alerts;

CREATE TRIGGER
    trg_budget_alerts_updated_at
BEFORE UPDATE ON budget_alerts
FOR EACH ROW
EXECUTE FUNCTION update_budget_alert_updated_at();
