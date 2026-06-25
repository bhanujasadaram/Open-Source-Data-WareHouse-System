-- ============================================================
--  ClickHouse Data Warehouse Schema
--  Database: demand_dw
--  Purpose:  Analytical tables and deduplication views
-- ============================================================

CREATE DATABASE IF NOT EXISTS demand_dw;

-- ── Demand-Level Analytics Table ─────────────────────────────
CREATE TABLE IF NOT EXISTS demand_dw.demand_delays
(
    demand_id           UInt32,
    demand_number       String,
    initialization_date Date,
    end_date            Date,
    t_total_days        Int32,
    t_user_days         Int32,
    t_committee_days    Int32,
    delay_flag          UInt8
)
ENGINE = ReplacingMergeTree()
ORDER BY demand_id;

-- ── Member-Level Accountability Table ────────────────────────
CREATE TABLE IF NOT EXISTS demand_dw.member_delays
(
    demand_id            UInt32,
    demand_number        String,
    member_id            UInt32,
    member_name          String,
    role                 String,
    t_member_days        Int32,
    passive_flag         UInt8,
    accountability_rank  UInt8,
    boundary_intervals   String
)
ENGINE = ReplacingMergeTree()
ORDER BY (demand_id, member_id);

-- ── Deduplication Views (always use these in Superset) ───────
CREATE OR REPLACE VIEW demand_dw.demand_delays_view AS
    SELECT * FROM demand_dw.demand_delays FINAL;

CREATE OR REPLACE VIEW demand_dw.member_delays_view AS
    SELECT * FROM demand_dw.member_delays FINAL;
