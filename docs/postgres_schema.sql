-- ============================================================
-- EDA-Genius PostgreSQL Schema
-- Phase 0 - Experiment Tracking Database
-- Compatible with PostgreSQL 14+
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Table: designs
-- One row per unique RTL design (by name)
-- ============================================================
CREATE TABLE IF NOT EXISTS designs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL UNIQUE,
    rtl_top_module  VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description     TEXT
);

CREATE INDEX IF NOT EXISTS idx_designs_name ON designs (name);

-- ============================================================
-- Table: experiment_runs
-- One row per EDA pipeline execution
-- ============================================================
CREATE TABLE IF NOT EXISTS experiment_runs (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id                      VARCHAR(128) NOT NULL UNIQUE,  -- human-readable e.g. run_alu_02f69331
    design_id                   UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    status                      VARCHAR(32)  NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED','ABORTED','RECOVERED')),
    target_pdk                  VARCHAR(64)  NOT NULL,
    clock_period_ns             NUMERIC(10,4),
    rtl_hash                    CHAR(64),         -- SHA-256 of all RTL sources
    config_hash                 CHAR(64),         -- SHA-256 of run config dict
    tool_versions               JSONB,            -- {"yosys": "0.9", "openroad": "2.0"}
    run_config                  JSONB,            -- top_module, params, constraints
    workdir_path                TEXT,
    started_at                  TIMESTAMPTZ,
    completed_at                TIMESTAMPTZ,
    total_wall_time_s           NUMERIC(12,3),
    failure_stage               VARCHAR(32),
    error_summary               TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_design_id  ON experiment_runs (design_id);
CREATE INDEX IF NOT EXISTS idx_runs_status     ON experiment_runs (status);
CREATE INDEX IF NOT EXISTS idx_runs_pdk        ON experiment_runs (target_pdk);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON experiment_runs (started_at DESC);

-- ============================================================
-- Table: run_stages
-- One row per tool-stage within an experiment run
-- ============================================================
CREATE TABLE IF NOT EXISTS run_stages (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id                  UUID NOT NULL REFERENCES experiment_runs(id) ON DELETE CASCADE,
    stage_name              VARCHAR(32) NOT NULL,  -- SYNTHESIS, FLOORPLAN, PLACEMENT, CTS, ROUTING, SIGNOFF
    stage_order             SMALLINT NOT NULL,
    tool_name               VARCHAR(64),
    status                  VARCHAR(32),
    exit_code               SMALLINT,
    runtime_s               NUMERIC(12,3),
    raw_log_path            TEXT,
    output_artifact_path    TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stages_run_id    ON run_stages (run_id);
CREATE INDEX IF NOT EXISTS idx_stages_name      ON run_stages (stage_name);

-- ============================================================
-- Table: run_metrics
-- One row per atomic metric extracted from tool outputs
-- ============================================================
CREATE TABLE IF NOT EXISTS run_metrics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES experiment_runs(id) ON DELETE CASCADE,
    metric_category VARCHAR(32)  NOT NULL,  -- TIMING, AREA, POWER, CELL_COUNT, CONGESTION, ROUTING
    metric_name     VARCHAR(128) NOT NULL,
    float_value     DOUBLE PRECISION,
    string_value    TEXT,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_run_id   ON run_metrics (run_id);
CREATE INDEX IF NOT EXISTS idx_metrics_category ON run_metrics (metric_category);
CREATE INDEX IF NOT EXISTS idx_metrics_name     ON run_metrics (metric_name);

-- ============================================================
-- Table: cell_statistics
-- Per-cell-type counts from Yosys synthesis output
-- ============================================================
CREATE TABLE IF NOT EXISTS cell_statistics (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id      UUID NOT NULL REFERENCES experiment_runs(id) ON DELETE CASCADE,
    cell_type   VARCHAR(128) NOT NULL,
    cell_count  INTEGER NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cellstats_run_id ON cell_statistics (run_id);

-- ============================================================
-- View: experiment_summary
-- Flattened PPA summary joining runs + key metrics
-- ============================================================
CREATE OR REPLACE VIEW experiment_summary AS
SELECT
    er.run_id,
    d.name                                              AS design_name,
    er.target_pdk,
    er.clock_period_ns,
    er.status,
    er.total_wall_time_s,
    MAX(CASE WHEN rm.metric_name = 'synthesis_runtime_s'        THEN rm.float_value END) AS synthesis_runtime_s,
    MAX(CASE WHEN rm.metric_name = 'physical_design_runtime_s'  THEN rm.float_value END) AS pd_runtime_s,
    MAX(CASE WHEN rm.metric_name = 'total_cells'                THEN rm.float_value END) AS total_cells,
    MAX(CASE WHEN rm.metric_name = 'chip_area_um2'              THEN rm.float_value END) AS chip_area_um2,
    MAX(CASE WHEN rm.metric_name = 'wns'                        THEN rm.float_value END) AS wns_ns,
    MAX(CASE WHEN rm.metric_name = 'tns'                        THEN rm.float_value END) AS tns_ns,
    MAX(CASE WHEN rm.metric_name = 'total_power_w'              THEN rm.float_value END) AS total_power_w,
    MAX(CASE WHEN rm.metric_name = 'total_wirelength_um'        THEN rm.float_value END) AS total_wirelength_um,
    er.failure_stage,
    er.started_at
FROM experiment_runs er
JOIN designs d ON d.id = er.design_id
LEFT JOIN run_metrics rm ON rm.run_id = er.id
GROUP BY er.id, d.name, er.target_pdk, er.clock_period_ns,
         er.status, er.total_wall_time_s, er.failure_stage, er.started_at;

-- ============================================================
-- Function: ingest_experiment_payload(jsonb)
-- Idempotent upsert for a full experiment payload dict
-- (matches RecordAdapter.to_postgres_payload() structure)
-- ============================================================
CREATE OR REPLACE FUNCTION ingest_experiment_payload(payload JSONB)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    _design_id  UUID;
    _run_id     UUID;
    stage       JSONB;
    metric      JSONB;
    cellstat    JSONB;
BEGIN
    -- Upsert design
    INSERT INTO designs (id, name, rtl_top_module)
    VALUES (
        (payload->'design'->>'id')::UUID,
        payload->'design'->>'name',
        payload->'design'->>'rtl_top_module'
    )
    ON CONFLICT (name) DO UPDATE SET
        rtl_top_module = EXCLUDED.rtl_top_module;
    _design_id := (payload->'design'->>'id')::UUID;

    -- Upsert run
    INSERT INTO experiment_runs (
        id, run_id, design_id, status, target_pdk, clock_period_ns,
        rtl_hash, config_hash, tool_versions, run_config, workdir_path,
        started_at, completed_at, total_wall_time_s
    )
    VALUES (
        (payload->'run'->>'id')::UUID,
        payload->'run'->>'run_id',
        _design_id,
        payload->'run'->>'status',
        payload->'run'->>'target_pdk',
        (payload->'run'->>'clock_period_ns')::NUMERIC,
        payload->'run'->'run_config'->>'rtl_hash',
        payload->'run'->'run_config'->>'config_hash',
        payload->'run'->'tool_versions',
        payload->'run'->'run_config',
        payload->'run'->>'workdir_path',
        (payload->'run'->>'started_at')::TIMESTAMPTZ,
        (payload->'run'->>'completed_at')::TIMESTAMPTZ,
        (payload->'run'->>'total_wall_time_s')::NUMERIC
    )
    ON CONFLICT (run_id) DO UPDATE SET
        status          = EXCLUDED.status,
        completed_at    = EXCLUDED.completed_at,
        total_wall_time_s = EXCLUDED.total_wall_time_s;
    _run_id := (payload->'run'->>'id')::UUID;

    -- Insert stages (delete old first for idempotency)
    DELETE FROM run_stages WHERE run_id = _run_id;
    FOR stage IN SELECT * FROM jsonb_array_elements(payload->'stages') LOOP
        INSERT INTO run_stages (id, run_id, stage_name, stage_order, tool_name, status,
                                exit_code, runtime_s, raw_log_path, output_artifact_path)
        VALUES (
            uuid_generate_v4(),
            _run_id,
            stage->>'stage_name',
            (stage->>'stage_order')::SMALLINT,
            stage->>'tool_name',
            stage->>'status',
            (stage->>'exit_code')::SMALLINT,
            (stage->>'runtime_s')::NUMERIC,
            stage->>'raw_log_path',
            stage->>'output_artifact_path'
        );
    END LOOP;

    -- Insert metrics (delete old first for idempotency)
    DELETE FROM run_metrics WHERE run_id = _run_id;
    FOR metric IN SELECT * FROM jsonb_array_elements(payload->'metrics') LOOP
        INSERT INTO run_metrics (id, run_id, metric_category, metric_name, float_value, string_value)
        VALUES (
            uuid_generate_v4(),
            _run_id,
            metric->>'metric_category',
            metric->>'metric_name',
            (metric->>'float_value')::DOUBLE PRECISION,
            metric->>'string_value'
        );
    END LOOP;
END;
$$;
