-- ============================================================
-- Migration 006: Multi-Currency Conversion Rates
-- Pod Alpha - Wallet Service
-- ============================================================
--
-- Purpose:
--   Store configured currency conversion rates used only by
--   the display/conversion layer.
--
-- IMPORTANT:
--   Wallet balances and the financial ledger remain the
--   authoritative internal credit amounts.
--
--   This table must never be used to rewrite historical
--   wallet balances or ledger transactions.
-- ============================================================


CREATE TABLE IF NOT EXISTS currency_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    base_currency VARCHAR(3) NOT NULL,
    target_currency VARCHAR(3) NOT NULL,

    rate NUMERIC(20, 8) NOT NULL,

    effective_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT currency_rates_base_currency_check
        CHECK (char_length(base_currency) = 3),

    CONSTRAINT currency_rates_target_currency_check
        CHECK (char_length(target_currency) = 3),

    CONSTRAINT currency_rates_rate_positive_check
        CHECK (rate > 0),

    CONSTRAINT currency_rates_different_currency_check
        CHECK (base_currency <> target_currency),

    CONSTRAINT currency_rates_unique_effective_rate
        UNIQUE (
            base_currency,
            target_currency,
            effective_at
        )
);


-- ------------------------------------------------------------
-- Fast lookup for the latest applicable conversion rate.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS
    idx_currency_rates_lookup
ON currency_rates (
    base_currency,
    target_currency,
    effective_at DESC
);


-- ------------------------------------------------------------
-- Automatically maintain updated_at.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_currency_rate_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS
    trg_currency_rates_updated_at
ON currency_rates;


CREATE TRIGGER
    trg_currency_rates_updated_at
BEFORE UPDATE ON currency_rates
FOR EACH ROW
EXECUTE FUNCTION update_currency_rate_updated_at();