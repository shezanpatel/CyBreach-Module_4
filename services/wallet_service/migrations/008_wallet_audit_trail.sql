-- ============================================================
-- Migration 008
-- Wallet Audit Trail
-- Week 9 - Pod Alpha
-- ============================================================

-- ------------------------------------------------------------
-- 1. Add module source to transaction headers
-- ------------------------------------------------------------

ALTER TABLE wallet_ledger
ADD COLUMN IF NOT EXISTS module_source VARCHAR(20);


-- Existing transactions predate module-source tracking.
-- Keep NULL valid so historical records remain intact.


-- ------------------------------------------------------------
-- 2. Add module source to accounting entries
-- ------------------------------------------------------------

ALTER TABLE wallet_ledger_entries
ADD COLUMN IF NOT EXISTS module_source VARCHAR(20);


-- ------------------------------------------------------------
-- 3. Backfill accounting entries from transaction headers
-- ------------------------------------------------------------

UPDATE wallet_ledger_entries AS entry
SET module_source = ledger.module_source
FROM wallet_ledger AS ledger
WHERE entry.transaction_id = ledger.id
  AND entry.module_source IS NULL
  AND ledger.module_source IS NOT NULL;


-- ------------------------------------------------------------
-- 4. Audit-query indexes
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_created_at
    ON wallet_ledger (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_transaction_type
    ON wallet_ledger (user_id, transaction_type);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_module_source
    ON wallet_ledger (user_id, module_source);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entries_user_created_at
    ON wallet_ledger_entries (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entries_user_entry_type
    ON wallet_ledger_entries (user_id, entry_type);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entries_user_module_source
    ON wallet_ledger_entries (user_id, module_source);


-- ------------------------------------------------------------
-- 5. Append-only protection
--
-- Ledger records may be inserted but never modified or deleted.
-- Corrections must be represented by new offset transactions.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION prevent_wallet_ledger_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Wallet ledger is append-only: % operations are not permitted on %',
        TG_OP,
        TG_TABLE_NAME;
END;
$$;


DROP TRIGGER IF EXISTS wallet_ledger_append_only_trigger
ON wallet_ledger;

CREATE TRIGGER wallet_ledger_append_only_trigger
BEFORE UPDATE OR DELETE
ON wallet_ledger
FOR EACH ROW
EXECUTE FUNCTION prevent_wallet_ledger_mutation();


DROP TRIGGER IF EXISTS wallet_ledger_entries_append_only_trigger
ON wallet_ledger_entries;

CREATE TRIGGER wallet_ledger_entries_append_only_trigger
BEFORE UPDATE OR DELETE
ON wallet_ledger_entries
FOR EACH ROW
EXECUTE FUNCTION prevent_wallet_ledger_mutation();


-- ============================================================
-- Migration complete
-- ============================================================