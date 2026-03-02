CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    affected_assets TEXT[] NOT NULL,
    summary TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    event_score DOUBLE PRECISION NOT NULL CHECK (event_score BETWEEN 0 AND 1),
    raw_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT create_hypertable('alerts', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts (ts DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_type_ts ON alerts (type, ts DESC);

CREATE TABLE IF NOT EXISTS alert_audit (
    id BIGSERIAL PRIMARY KEY,
    alert_id UUID NOT NULL REFERENCES alerts(alert_id),
    trace_id TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alert_audit_alert_id ON alert_audit(alert_id);
