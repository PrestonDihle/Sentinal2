-- ============================================================
-- SENTINEL2 — SQLite Database Schema
-- ============================================================

-- ============================================================
-- CONFIGURATION & MANAGEMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS pirs (
    pir_id TEXT PRIMARY KEY,
    pir_title TEXT NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    is_ai_defined INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS collection_plan (
    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    query_type TEXT DEFAULT 'gdelt_doc',
    pir_id TEXT,
    sir_id TEXT,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'active',
    source TEXT DEFAULT 'cma',
    created_at TEXT DEFAULT (datetime('now')),
    last_run TEXT,
    last_yield INTEGER DEFAULT 0,
    low_yield_days INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    total_results INTEGER DEFAULT 0,
    retired_at TEXT,
    FOREIGN KEY (pir_id) REFERENCES pirs(pir_id)
);

CREATE TABLE IF NOT EXISTS cma_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    action TEXT,
    query_id INTEGER,
    details TEXT,
    FOREIGN KEY (query_id) REFERENCES collection_plan(query_id)
);

CREATE TABLE IF NOT EXISTS email_recipients (
    recipient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT,
    report_types TEXT DEFAULT 'daily',
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_dispatch_log (
    dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_id INTEGER,
    report_type TEXT,
    report_date TEXT,
    sent_at TEXT,
    status TEXT,
    error_message TEXT,
    FOREIGN KEY (recipient_id) REFERENCES email_recipients(recipient_id)
);

-- ============================================================
-- RAW & PROCESSED COLLECTION (R&P Layer)
-- ============================================================

CREATE TABLE IF NOT EXISTS raw_collection (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER,
    collection_date TEXT NOT NULL,
    source_url TEXT,
    source_name TEXT,
    title TEXT,
    snippet TEXT,
    full_text TEXT,
    raw_json TEXT,
    gdelt_themes TEXT,
    gdelt_tone REAL,
    gdelt_entities TEXT,
    gdelt_locations TEXT,
    pir_id TEXT,
    sir_id TEXT,
    is_duplicate INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (query_id) REFERENCES collection_plan(query_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_url_date ON raw_collection(source_url, collection_date);
CREATE INDEX IF NOT EXISTS idx_raw_date ON raw_collection(collection_date);
CREATE INDEX IF NOT EXISTS idx_raw_pir ON raw_collection(pir_id);

CREATE TABLE IF NOT EXISTS processed_collection (
    processed_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    source_urls TEXT,
    source_url TEXT,
    pir_id TEXT,
    indicator_id TEXT,
    sir_id TEXT,
    country TEXT,
    group_tag TEXT,
    topic TEXT,
    nai TEXT,
    significance TEXT DEFAULT 'MED',
    confidence TEXT DEFAULT 'Moderate',
    is_duplicate_merge INTEGER DEFAULT 0,
    merged_count INTEGER DEFAULT 1,
    source_item_ids TEXT,
    processed_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_proc_date ON processed_collection(run_date);
CREATE INDEX IF NOT EXISTS idx_proc_pir ON processed_collection(pir_id);
CREATE INDEX IF NOT EXISTS idx_proc_sig ON processed_collection(significance);

-- ============================================================
-- RUNNING ESTIMATES & SUMMARIES
-- ============================================================

CREATE TABLE IF NOT EXISTS running_estimate (
    estimate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT UNIQUE NOT NULL,
    event_summary TEXT,
    pir_mapping TEXT,
    trajectory TEXT,
    delta_notes TEXT,
    state_of_play TEXT,
    cumulative_patterns TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trajectory_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT,
    pir_id TEXT,
    old_trajectory TEXT,
    new_trajectory TEXT,
    reason TEXT,
    trigger_summary TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tc_date ON trajectory_changes(run_date);

CREATE TABLE IF NOT EXISTS weekly_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT,
    week_end TEXT,
    week_number INTEGER,
    summary_text TEXT,
    pir1_trajectory TEXT,
    pir2_trajectory TEXT,
    pir3_trajectory TEXT,
    pir4_trajectory TEXT,
    black_swan_watchlist TEXT,
    big_question_assessment TEXT,
    pdf_path TEXT,
    drive_file_id TEXT,
    drive_view_link TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS monthly_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    month_start TEXT,
    month_end TEXT,
    month_number INTEGER,
    summary_text TEXT,
    pir1_trajectory_arc TEXT,
    pir2_trajectory_arc TEXT,
    pir3_trajectory_arc TEXT,
    pir4_trajectory_arc TEXT,
    black_swan_ledger TEXT,
    big_question_assessment TEXT,
    collection_program_review TEXT,
    pdf_path TEXT,
    drive_file_id TEXT,
    drive_view_link TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- ANALYSIS & ESTIMATION (A&E Layer)
-- ============================================================

CREATE TABLE IF NOT EXISTS ae_assessments (
    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    group_id INTEGER,
    analysis_group INTEGER,
    pir_id TEXT,
    expert_role TEXT,
    branch TEXT,
    assessment_json TEXT,
    assessment TEXT,
    synthesis_text TEXT,
    trajectory TEXT,
    confidence_level TEXT,
    confidence TEXT,
    key_entities TEXT,
    recommended_collection TEXT,
    flags TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ae_date ON ae_assessments(run_date);
CREATE INDEX IF NOT EXISTS idx_ae_group ON ae_assessments(group_id);
CREATE INDEX IF NOT EXISTS idx_ae_pir ON ae_assessments(pir_id);

CREATE TABLE IF NOT EXISTS cross_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_assessment_id INTEGER,
    target_assessment_id INTEGER,
    relationship_type TEXT DEFAULT 'informs',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_assessment_id) REFERENCES ae_assessments(assessment_id),
    FOREIGN KEY (target_assessment_id) REFERENCES ae_assessments(assessment_id)
);

-- ============================================================
-- BLACK SWAN ALERTS
-- ============================================================

CREATE TABLE IF NOT EXISTS black_swan_alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT,
    issued_at TEXT,
    alert_type TEXT,
    event_id TEXT,
    event_name TEXT,
    trigger_type TEXT,
    alert_text TEXT,
    report_text TEXT,
    probability_band TEXT,
    impact_tier TEXT,
    is_new_event INTEGER DEFAULT 0,
    recommended_actions TEXT,
    collection_recommendations TEXT,
    watchlist_json TEXT,
    pdf_path TEXT,
    drive_file_id TEXT,
    drive_view_link TEXT,
    email_dispatch_status TEXT,
    email_dispatch_timestamp TEXT,
    recipients_notified TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_bsa_date ON black_swan_alerts(run_date);

-- ============================================================
-- METRICS SYSTEM
-- ============================================================

CREATE TABLE IF NOT EXISTS metrics (
    metric_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    domain TEXT,
    source TEXT,
    tier INTEGER DEFAULT 1,
    collection_fn TEXT,
    baseline_window INTEGER DEFAULT 90,
    alert_threshold REAL DEFAULT 2.00,
    direction TEXT DEFAULT 'both',
    enabled INTEGER DEFAULT 1,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER NOT NULL,
    run_date TEXT NOT NULL,
    raw_value REAL,
    raw_json TEXT,
    z_score REAL,
    anomaly_flag INTEGER DEFAULT 0,
    rolling_mean REAL,
    rolling_std REAL,
    trend_7d TEXT DEFAULT 'INSUFFICIENT',
    data_quality TEXT DEFAULT 'ok',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(metric_id, run_date),
    FOREIGN KEY (metric_id) REFERENCES metrics(metric_id)
);

CREATE INDEX IF NOT EXISTS idx_dv_date ON daily_values(run_date);
CREATE INDEX IF NOT EXISTS idx_dv_anomaly ON daily_values(anomaly_flag);

CREATE TABLE IF NOT EXISTS composite_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT UNIQUE NOT NULL,
    total_collected INTEGER,
    anomalous_count INTEGER,
    anomalous_metrics TEXT,
    alert_level TEXT DEFAULT 'NORMAL',
    convergence_note TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cs_date ON composite_scores(run_date);

CREATE TABLE IF NOT EXISTS metrics_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER NOT NULL,
    run_date TEXT NOT NULL,
    api_endpoint TEXT,
    http_status INTEGER,
    response_body TEXT,
    response_size INTEGER,
    latency_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(metric_id, run_date),
    FOREIGN KEY (metric_id) REFERENCES metrics(metric_id)
);

CREATE INDEX IF NOT EXISTS idx_mraw_date ON metrics_raw(run_date);

CREATE TABLE IF NOT EXISTS correlation_matrix (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT,
    metric_id_a INTEGER,
    metric_id_b INTEGER,
    window_days INTEGER DEFAULT 30,
    correlation REAL,
    lag_days INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(run_date, metric_id_a, metric_id_b, lag_days),
    FOREIGN KEY (metric_id_a) REFERENCES metrics(metric_id),
    FOREIGN KEY (metric_id_b) REFERENCES metrics(metric_id)
);

-- ============================================================
-- DELIVERY & REPORTING
-- ============================================================

CREATE TABLE IF NOT EXISTS delivery_log (
    delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT,
    report_type TEXT,
    pdf_path TEXT,
    pdf_size_kb INTEGER,
    drive_file_id TEXT,
    drive_view_link TEXT,
    drive_upload_status TEXT,
    drive_upload_timestamp TEXT,
    email_message_id TEXT,
    email_recipients TEXT,
    email_send_status TEXT,
    email_send_timestamp TEXT,
    retry_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_del_date ON delivery_log(run_date);

CREATE TABLE IF NOT EXISTS report_archive (
    archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT UNIQUE,
    cycle_number INTEGER,
    total_items INTEGER,
    high_count INTEGER,
    med_count INTEGER,
    alert_level TEXT,
    anomalous_metric_count INTEGER,
    trajectory TEXT,
    html_length INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_arch_date ON report_archive(run_date);

-- ============================================================
-- ENTITIES & SEARCH
-- ============================================================

CREATE TABLE IF NOT EXISTS entities (
    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    aliases TEXT,
    country_affiliation TEXT,
    description TEXT,
    first_seen TEXT,
    last_seen TEXT,
    mention_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ent_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_ent_country ON entities(country_affiliation);

CREATE TABLE IF NOT EXISTS entity_mentions (
    mention_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    source_table TEXT,
    source_id INTEGER,
    run_date TEXT,
    context_snippet TEXT,
    sentiment TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_em_entity ON entity_mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_em_date ON entity_mentions(run_date);

-- ============================================================
-- CONFIDENCE CALIBRATION
-- ============================================================

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT,
    source_type TEXT,
    source_id INTEGER,
    pir_id TEXT,
    analysis_group INTEGER,
    prediction_text TEXT,
    confidence_level TEXT,
    predicted_outcome TEXT,
    time_horizon_days INTEGER DEFAULT 7,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pred_date ON predictions(run_date);
CREATE INDEX IF NOT EXISTS idx_pred_conf ON predictions(confidence_level);

CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    evaluation_date TEXT,
    actual_outcome TEXT,
    outcome_matches INTEGER,
    evaluator_notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
);

-- ============================================================
-- PIPELINE STATE
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    results TEXT,
    completed_at TEXT DEFAULT (datetime('now')),
    UNIQUE(run_date, step_name)
);

CREATE INDEX IF NOT EXISTS idx_cp_date ON pipeline_checkpoints(run_date);

CREATE TABLE IF NOT EXISTS agent_group_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    analysis_group INTEGER NOT NULL,
    agent_role TEXT NOT NULL,
    assigned_by TEXT DEFAULT 'default',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(run_date, analysis_group, agent_role)
);

CREATE INDEX IF NOT EXISTS idx_aga_date ON agent_group_assignments(run_date);
