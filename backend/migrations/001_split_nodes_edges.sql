BEGIN;

-- 1) Add new columns to nodes
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS node_type VARCHAR;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS text VARCHAR;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS source_input_id INTEGER;

-- 2) Backfill existing rows as input nodes
UPDATE nodes
SET node_type = 'input',
    text = input_text
WHERE node_type IS NULL;

-- 3) Create edges table
CREATE TABLE IF NOT EXISTS edges (
    id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    from_node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    to_node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_edge_from_node UNIQUE (from_node_id),
    CONSTRAINT uq_edge_to_node UNIQUE (to_node_id)
);

-- 4) Create output nodes and map them to inputs
INSERT INTO nodes (workflow_id, node_type, text, created_at, source_input_id)
SELECT workflow_id, 'output', output_text, created_at, id
FROM nodes
WHERE node_type = 'input'
  AND output_text IS NOT NULL;

-- 5) Create edges from inputs to outputs
INSERT INTO edges (workflow_id, from_node_id, to_node_id)
SELECT i.workflow_id, i.id, o.id
FROM nodes i
JOIN nodes o ON o.source_input_id = i.id
WHERE i.node_type = 'input'
  AND o.node_type = 'output'
ON CONFLICT DO NOTHING;

-- 6) Drop legacy columns + constraints
ALTER TABLE nodes DROP COLUMN IF EXISTS input_text;
ALTER TABLE nodes DROP COLUMN IF EXISTS output_text;
ALTER TABLE nodes DROP COLUMN IF EXISTS source_input_id;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_workflow_input'
    ) THEN
        ALTER TABLE nodes DROP CONSTRAINT uq_workflow_input;
    END IF;
END $$;

-- 7) Enforce not null on new columns
ALTER TABLE nodes ALTER COLUMN node_type SET NOT NULL;
ALTER TABLE nodes ALTER COLUMN text SET NOT NULL;

COMMIT;
