-- Migration: Remove old edge constraints and add new one
-- This allows multiple edges from/to the same node (branching workflows)
-- Migration: 006_update_edge_constraints.sql

BEGIN;

-- Drop old constraints that prevented branching
ALTER TABLE edges DROP CONSTRAINT IF EXISTS uq_edge_from_node;
ALTER TABLE edges DROP CONSTRAINT IF EXISTS uq_edge_to_node;

-- Add new constraint that prevents duplicate edges between same two nodes
ALTER TABLE edges ADD CONSTRAINT uq_edge_from_to UNIQUE (from_node_id, to_node_id);

-- Add comment
COMMENT ON CONSTRAINT uq_edge_from_to ON edges IS 'Prevents duplicate edges between the same two nodes';

COMMIT;
