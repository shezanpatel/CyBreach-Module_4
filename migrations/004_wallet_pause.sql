-- ============================================================
-- Migration 004: Wallet Reconciliation Pause
-- ============================================================
--
-- Purpose:
--   Persist a wallet safety state so that reconciliation
--   mismatches can immediately freeze financial operations.
--
-- A wallet is normally:
--   is_paused = FALSE
--
-- A reconciliation mismatch changes it to:
--   is_paused = TRUE
--
-- The pause remains persistent until explicitly cleared by
-- an authorized operational process.
-- ============================================================


ALTER TABLE wallet_balance
ADD COLUMN IF NOT EXISTS is_paused BOOLEAN
NOT NULL
DEFAULT FALSE;


ALTER TABLE wallet_balance
ADD COLUMN IF NOT EXISTS pause_reason VARCHAR(255);


ALTER TABLE wallet_balance
ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP WITH TIME ZONE;


CREATE INDEX IF NOT EXISTS
idx_wallet_balance_paused
ON wallet_balance (
    is_paused
);


CREATE INDEX IF NOT EXISTS
idx_wallet_balance_paused_at
ON wallet_balance (
    paused_at
);