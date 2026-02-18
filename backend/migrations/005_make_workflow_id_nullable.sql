-- Migration: Update chat_sessions to make workflow_id nullable
-- This supports the new trigger node system where sessions aren't tied to a single workflow
-- Migration: 005_make_workflow_id_nullable.sql

BEGIN;

-- Make workflow_id nullable in chat_sessions table
ALTER TABLE chat_sessions 
ALTER COLUMN workflow_id DROP NOT NULL;

-- Add comment
COMMENT ON COLUMN chat_sessions.workflow_id IS 'Previously required, now nullable as sessions can span multiple workflows via trigger nodes';

COMMIT;
