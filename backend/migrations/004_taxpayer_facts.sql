CREATE TABLE IF NOT EXISTS taxpayer_facts (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    assessment_year VARCHAR NOT NULL,
    fact_key VARCHAR NOT NULL,
    value JSONB NOT NULL,
    normalized_value JSONB NOT NULL,
    source_type VARCHAR NOT NULL,
    document_id VARCHAR REFERENCES user_documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    section VARCHAR,
    source_text TEXT,
    confidence VARCHAR NOT NULL DEFAULT 'LOW',
    status VARCHAR NOT NULL DEFAULT 'NEEDS_CONFIRMATION',
    mapping_status VARCHAR NOT NULL DEFAULT 'MAPPED',
    group_id VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_taxpayer_facts_user_id ON taxpayer_facts(user_id);
CREATE INDEX IF NOT EXISTS ix_taxpayer_facts_assessment_year ON taxpayer_facts(assessment_year);
CREATE INDEX IF NOT EXISTS ix_taxpayer_facts_owner_year_key
    ON taxpayer_facts(user_id, assessment_year, fact_key);
CREATE INDEX IF NOT EXISTS ix_taxpayer_facts_document ON taxpayer_facts(document_id);

CREATE TABLE IF NOT EXISTS taxpayer_fact_evidence (
    id VARCHAR PRIMARY KEY,
    fact_id VARCHAR NOT NULL REFERENCES taxpayer_facts(id) ON DELETE CASCADE,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    source_type VARCHAR NOT NULL,
    document_id VARCHAR REFERENCES user_documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    section VARCHAR,
    source_text TEXT,
    confidence VARCHAR NOT NULL DEFAULT 'LOW',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_taxpayer_fact_evidence_fact ON taxpayer_fact_evidence(fact_id);
CREATE INDEX IF NOT EXISTS ix_taxpayer_fact_evidence_owner ON taxpayer_fact_evidence(user_id);
