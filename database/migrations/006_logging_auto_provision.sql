-- ==============================================================================
-- Migration 006: Comprehensive Logging & Auto-Provisioned Channels
-- NOVEXA Enterprise Architecture
-- ==============================================================================

CREATE INDEX IF NOT EXISTS idx_logging_config_cat ON logging_config(category_id);
