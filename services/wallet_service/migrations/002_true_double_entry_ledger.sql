-- ============================================================
-- Migration 002
-- True Double-Entry Wallet Ledger
-- ============================================================

-- ------------------------------------------------------------
-- 1. Accounting entries table
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS wallet_ledger_entries (
    id UUID PRIMARY KEY,

    transaction_id UUID NOT NULL
        REFERENCES wallet_ledger(id)
        ON DELETE RESTRICT,

    user_id VARCHAR(100) NOT NULL,

    transaction_type VARCHAR(20) NOT NULL,

    currency VARCHAR(3) NOT NULL,

    entry_type VARCHAR(6) NOT NULL,

    account_code VARCHAR(50) NOT NULL,

    amount NUMERIC(18, 2) NOT NULL,

    reference_id VARCHAR(100) NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL,

    CONSTRAINT ck_wallet_ledger_entry_type
        CHECK (entry_type IN ('DEBIT', 'CREDIT')),

    CONSTRAINT ck_wallet_ledger_entry_amount_positive
        CHECK (amount > 0),

    CONSTRAINT uq_wallet_ledger_entry_transaction_type
        UNIQUE (transaction_id, entry_type)
);


-- ------------------------------------------------------------
-- 2. Indexes
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entries_transaction_id
    ON wallet_ledger_entries (transaction_id);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entries_user_id
    ON wallet_ledger_entries (user_id);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entries_account_code
    ON wallet_ledger_entries (account_code);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entries_created_at
    ON wallet_ledger_entries (created_at);


-- ------------------------------------------------------------
-- 3. Validate that every transaction is balanced
--
-- Every transaction must have:
--
--     exactly 2 entries
--     exactly 1 DEBIT
--     exactly 1 CREDIT
--     equal debit/credit amounts
--     same currency
--
-- This is a deferred constraint, so the database checks
-- the transaction at COMMIT time rather than after the
-- first individual INSERT.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_wallet_ledger_transaction()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id UUID;
    v_entry_count INTEGER;
    v_debit_count INTEGER;
    v_credit_count INTEGER;
    v_debit_amount NUMERIC(18, 2);
    v_credit_amount NUMERIC(18, 2);
    v_currency_count INTEGER;
BEGIN
    v_transaction_id := COALESCE(NEW.transaction_id, OLD.transaction_id);

    SELECT
        COUNT(*),
        COUNT(*) FILTER (
            WHERE entry_type = 'DEBIT'
        ),
        COUNT(*) FILTER (
            WHERE entry_type = 'CREDIT'
        ),
        COALESCE(
            SUM(
                CASE
                    WHEN entry_type = 'DEBIT'
                    THEN amount
                    ELSE 0
                END
            ),
            0
        ),
        COALESCE(
            SUM(
                CASE
                    WHEN entry_type = 'CREDIT'
                    THEN amount
                    ELSE 0
                END
            ),
            0
        ),
        COUNT(DISTINCT currency)
    INTO
        v_entry_count,
        v_debit_count,
        v_credit_count,
        v_debit_amount,
        v_credit_amount,
        v_currency_count
    FROM wallet_ledger_entries
    WHERE transaction_id = v_transaction_id;

    IF v_entry_count <> 2
       OR v_debit_count <> 1
       OR v_credit_count <> 1
       OR v_debit_amount <> v_credit_amount
       OR v_currency_count <> 1
    THEN
        RAISE EXCEPTION
            'Wallet ledger transaction % is not balanced: entries=%, debits=%, credits=%, debit_amount=%, credit_amount=%, currencies=%',
            v_transaction_id,
            v_entry_count,
            v_debit_count,
            v_credit_count,
            v_debit_amount,
            v_credit_amount,
            v_currency_count;
    END IF;

    RETURN NULL;
END;
$$;


-- ------------------------------------------------------------
-- 4. Deferred balancing constraint
-- ------------------------------------------------------------

DROP TRIGGER IF EXISTS wallet_ledger_entries_balanced_trigger
ON wallet_ledger_entries;

CREATE CONSTRAINT TRIGGER wallet_ledger_entries_balanced_trigger
AFTER INSERT OR UPDATE OR DELETE
ON wallet_ledger_entries
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_wallet_ledger_transaction();


-- ------------------------------------------------------------
-- 5. Backfill existing wallet_ledger transactions
--
-- This protects an environment that already contains
-- transactions from before Migration 002.
--
-- Existing transaction types:
--
-- DEPOSIT:
--     DEBIT  CASH
--     CREDIT WALLET
--
-- WITHDRAW:
--     DEBIT  WALLET
--     CREDIT CASH
--
-- CREDIT:
--     DEBIT  CREDIT_SOURCE
--     CREDIT WALLET
--
-- REFUND:
--     DEBIT  REFUND_EXPENSE
--     CREDIT WALLET
--
-- CREDIT_EXPIRY:
--     DEBIT  WALLET
--     CREDIT CREDIT_EXPIRY_REVENUE
-- ------------------------------------------------------------

INSERT INTO wallet_ledger_entries (
    id,
    transaction_id,
    user_id,
    transaction_type,
    currency,
    entry_type,
    account_code,
    amount,
    reference_id,
    created_at
)
SELECT
    gen_random_uuid(),
    wl.id,
    wl.user_id,
    wl.transaction_type,
    wl.currency,
    mapping.entry_type,
    mapping.account_code,
    wl.amount,
    wl.reference_id,
    wl.created_at
FROM wallet_ledger wl
CROSS JOIN LATERAL (
    VALUES
        (
            'DEBIT',
            CASE wl.transaction_type
                WHEN 'DEPOSIT' THEN 'CASH'
                WHEN 'WITHDRAW' THEN 'WALLET'
                WHEN 'CREDIT' THEN 'CREDIT_SOURCE'
                WHEN 'REFUND' THEN 'REFUND_EXPENSE'
                WHEN 'CREDIT_EXPIRY' THEN 'WALLET'
            END
        ),
        (
            'CREDIT',
            CASE wl.transaction_type
                WHEN 'DEPOSIT' THEN 'WALLET'
                WHEN 'WITHDRAW' THEN 'CASH'
                WHEN 'CREDIT' THEN 'WALLET'
                WHEN 'REFUND' THEN 'WALLET'
                WHEN 'CREDIT_EXPIRY' THEN 'CREDIT_EXPIRY_REVENUE'
            END
        )
) AS mapping(entry_type, account_code)
WHERE wl.transaction_type IN (
    'DEPOSIT',
    'WITHDRAW',
    'CREDIT',
    'REFUND',
    'CREDIT_EXPIRY'
)
AND NOT EXISTS (
    SELECT 1
    FROM wallet_ledger_entries existing
    WHERE existing.transaction_id = wl.id
);


-- ------------------------------------------------------------
-- Migration complete
-- ------------------------------------------------------------