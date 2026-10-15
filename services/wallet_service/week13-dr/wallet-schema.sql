--
-- PostgreSQL database dump
--

\restrict lgbdqU6dFKmZ0fJyBv6QC6eaYwneO9oOep6mJyuB2zMl7Tf5IBVHbWFFQ0AHFnc

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: prevent_wallet_ledger_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.prevent_wallet_ledger_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION
        'Wallet ledger is append-only: % operations are not permitted on %',
        TG_OP,
        TG_TABLE_NAME;
END;
$$;


--
-- Name: update_budget_alert_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_budget_alert_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_currency_rate_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_currency_rate_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_subscription_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_subscription_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: budget_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.budget_alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(100) NOT NULL,
    currency character varying(3) NOT NULL,
    threshold numeric(18,2) NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    last_triggered_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT budget_alerts_currency_length CHECK ((char_length((currency)::text) = 3)),
    CONSTRAINT budget_alerts_threshold_non_negative CHECK ((threshold >= (0)::numeric))
);


--
-- Name: currency_rates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.currency_rates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    base_currency character varying(3) NOT NULL,
    target_currency character varying(3) NOT NULL,
    rate numeric(20,8) NOT NULL,
    effective_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT currency_rates_base_currency_check CHECK ((char_length((base_currency)::text) = 3)),
    CONSTRAINT currency_rates_different_currency_check CHECK (((base_currency)::text <> (target_currency)::text)),
    CONSTRAINT currency_rates_rate_positive_check CHECK ((rate > (0)::numeric)),
    CONSTRAINT currency_rates_target_currency_check CHECK ((char_length((target_currency)::text) = 3))
);


--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.idempotency_keys (
    key character varying(255) NOT NULL,
    user_id character varying(100) NOT NULL,
    endpoint character varying(100) NOT NULL,
    request_hash character varying(64) NOT NULL,
    response_data character varying,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscriptions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    tier character varying(50) NOT NULL,
    status character varying(30) DEFAULT 'ACTIVE'::character varying NOT NULL,
    credits_per_period numeric(20,8) NOT NULL,
    current_period_start timestamp with time zone NOT NULL,
    current_period_end timestamp with time zone NOT NULL,
    cancelled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT subscriptions_credits_positive_check CHECK ((credits_per_period >= (0)::numeric)),
    CONSTRAINT subscriptions_period_check CHECK ((current_period_end > current_period_start)),
    CONSTRAINT subscriptions_status_check CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'CANCELLED'::character varying, 'EXPIRED'::character varying])::text[]))),
    CONSTRAINT subscriptions_tier_check CHECK (((tier)::text = ANY ((ARRAY['FREE'::character varying, 'STARTER'::character varying, 'PROFESSIONAL'::character varying, 'ENTERPRISE'::character varying])::text[])))
);


--
-- Name: wallet_balance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallet_balance (
    user_id character varying(100) NOT NULL,
    currency character varying(3) NOT NULL,
    available_balance numeric(18,2) NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_paused boolean NOT NULL,
    pause_reason character varying(255),
    paused_at timestamp with time zone
);


--
-- Name: wallet_credits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallet_credits (
    id uuid NOT NULL,
    user_id character varying(100) NOT NULL,
    currency character varying(3) NOT NULL,
    amount numeric(18,2) NOT NULL,
    remaining_amount numeric(18,2) NOT NULL,
    reference_id character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    expired_at timestamp with time zone
);


--
-- Name: wallet_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallet_ledger (
    id uuid NOT NULL,
    user_id character varying(100) NOT NULL,
    transaction_type character varying(20) NOT NULL,
    currency character varying(3) NOT NULL,
    amount numeric(18,2) NOT NULL,
    reference_id character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    module_source character varying(20)
);


--
-- Name: wallet_ledger_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallet_ledger_entries (
    id uuid NOT NULL,
    transaction_id uuid NOT NULL,
    user_id character varying(100) NOT NULL,
    transaction_type character varying(20) NOT NULL,
    currency character varying(3) NOT NULL,
    entry_type character varying(6) NOT NULL,
    account_code character varying(50) NOT NULL,
    amount numeric(18,2) NOT NULL,
    reference_id character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    module_source character varying(20),
    CONSTRAINT ck_wallet_ledger_entry_amount_positive CHECK ((amount > (0)::numeric)),
    CONSTRAINT ck_wallet_ledger_entry_type CHECK (((entry_type)::text = ANY ((ARRAY['DEBIT'::character varying, 'CREDIT'::character varying])::text[])))
);


--
-- Name: week11_pitr_test; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.week11_pitr_test (
    id integer NOT NULL,
    marker text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: week11_pitr_test_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.week11_pitr_test_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: week11_pitr_test_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.week11_pitr_test_id_seq OWNED BY public.week11_pitr_test.id;


--
-- Name: week11_pitr_test id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week11_pitr_test ALTER COLUMN id SET DEFAULT nextval('public.week11_pitr_test_id_seq'::regclass);


--
-- Name: budget_alerts budget_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.budget_alerts
    ADD CONSTRAINT budget_alerts_pkey PRIMARY KEY (id);


--
-- Name: budget_alerts budget_alerts_unique_wallet; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.budget_alerts
    ADD CONSTRAINT budget_alerts_unique_wallet UNIQUE (user_id, currency);


--
-- Name: currency_rates currency_rates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency_rates
    ADD CONSTRAINT currency_rates_pkey PRIMARY KEY (id);


--
-- Name: currency_rates currency_rates_unique_effective_rate; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency_rates
    ADD CONSTRAINT currency_rates_unique_effective_rate UNIQUE (base_currency, target_currency, effective_at);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: wallet_ledger_entries uq_wallet_ledger_entry_transaction_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_ledger_entries
    ADD CONSTRAINT uq_wallet_ledger_entry_transaction_type UNIQUE (transaction_id, entry_type);


--
-- Name: wallet_balance wallet_balance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_balance
    ADD CONSTRAINT wallet_balance_pkey PRIMARY KEY (user_id, currency);


--
-- Name: wallet_credits wallet_credits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_credits
    ADD CONSTRAINT wallet_credits_pkey PRIMARY KEY (id);


--
-- Name: wallet_ledger_entries wallet_ledger_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_ledger_entries
    ADD CONSTRAINT wallet_ledger_entries_pkey PRIMARY KEY (id);


--
-- Name: wallet_ledger wallet_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_ledger
    ADD CONSTRAINT wallet_ledger_pkey PRIMARY KEY (id);


--
-- Name: week11_pitr_test week11_pitr_test_marker_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week11_pitr_test
    ADD CONSTRAINT week11_pitr_test_marker_key UNIQUE (marker);


--
-- Name: week11_pitr_test week11_pitr_test_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week11_pitr_test
    ADD CONSTRAINT week11_pitr_test_pkey PRIMARY KEY (id);


--
-- Name: idx_budget_alerts_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_budget_alerts_enabled ON public.budget_alerts USING btree (is_enabled);


--
-- Name: idx_budget_alerts_user_currency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_budget_alerts_user_currency ON public.budget_alerts USING btree (user_id, currency);


--
-- Name: idx_currency_rates_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_currency_rates_lookup ON public.currency_rates USING btree (base_currency, target_currency, effective_at DESC);


--
-- Name: idx_subscriptions_period_end; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_period_end ON public.subscriptions USING btree (current_period_end);


--
-- Name: idx_subscriptions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_status ON public.subscriptions USING btree (status);


--
-- Name: idx_subscriptions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_user_id ON public.subscriptions USING btree (user_id);


--
-- Name: idx_wallet_ledger_entries_user_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallet_ledger_entries_user_created_at ON public.wallet_ledger_entries USING btree (user_id, created_at DESC);


--
-- Name: idx_wallet_ledger_entries_user_entry_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallet_ledger_entries_user_entry_type ON public.wallet_ledger_entries USING btree (user_id, entry_type);


--
-- Name: idx_wallet_ledger_entries_user_module_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallet_ledger_entries_user_module_source ON public.wallet_ledger_entries USING btree (user_id, module_source);


--
-- Name: idx_wallet_ledger_user_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallet_ledger_user_created_at ON public.wallet_ledger USING btree (user_id, created_at DESC);


--
-- Name: idx_wallet_ledger_user_module_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallet_ledger_user_module_source ON public.wallet_ledger USING btree (user_id, module_source);


--
-- Name: idx_wallet_ledger_user_transaction_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallet_ledger_user_transaction_type ON public.wallet_ledger USING btree (user_id, transaction_type);


--
-- Name: ix_wallet_credits_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wallet_credits_expires_at ON public.wallet_credits USING btree (expires_at);


--
-- Name: ix_wallet_credits_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wallet_credits_user_id ON public.wallet_credits USING btree (user_id);


--
-- Name: uq_subscriptions_active_user; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_subscriptions_active_user ON public.subscriptions USING btree (user_id) WHERE ((status)::text = 'ACTIVE'::text);


--
-- Name: budget_alerts trg_budget_alerts_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_budget_alerts_updated_at BEFORE UPDATE ON public.budget_alerts FOR EACH ROW EXECUTE FUNCTION public.update_budget_alert_updated_at();


--
-- Name: currency_rates trg_currency_rates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_currency_rates_updated_at BEFORE UPDATE ON public.currency_rates FOR EACH ROW EXECUTE FUNCTION public.update_currency_rate_updated_at();


--
-- Name: subscriptions trg_subscriptions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION public.update_subscription_updated_at();


--
-- Name: wallet_ledger wallet_ledger_append_only_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER wallet_ledger_append_only_trigger BEFORE DELETE OR UPDATE ON public.wallet_ledger FOR EACH ROW EXECUTE FUNCTION public.prevent_wallet_ledger_mutation();


--
-- Name: wallet_ledger_entries wallet_ledger_entries_append_only_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER wallet_ledger_entries_append_only_trigger BEFORE DELETE OR UPDATE ON public.wallet_ledger_entries FOR EACH ROW EXECUTE FUNCTION public.prevent_wallet_ledger_mutation();


--
-- Name: wallet_ledger_entries wallet_ledger_entries_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_ledger_entries
    ADD CONSTRAINT wallet_ledger_entries_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.wallet_ledger(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict lgbdqU6dFKmZ0fJyBv6QC6eaYwneO9oOep6mJyuB2zMl7Tf5IBVHbWFFQ0AHFnc

