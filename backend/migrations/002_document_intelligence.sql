-- Optional user document metadata. Binary storage and processing are separate adapters.
CREATE TABLE IF NOT EXISTS user_documents (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    document_type VARCHAR NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_key VARCHAR,
    assessment_year VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'pending',
    page_count INTEGER,
    processing_result JSONB,
    metadata_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_user_documents_user_id ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS ix_user_documents_assessment_year ON user_documents(assessment_year);