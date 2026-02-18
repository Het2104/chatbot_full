-- Migration 007: Add position columns to nodes table
-- This enables visual workflow editor to save node positions

-- Add position_x column (horizontal position in pixels)
ALTER TABLE nodes 
ADD COLUMN position_x INTEGER;

-- Add position_y column (vertical position in pixels)
ALTER TABLE nodes 
ADD COLUMN position_y INTEGER;

-- Add comment explaining the columns
COMMENT ON COLUMN nodes.position_x IS 'Horizontal position of node in workflow editor (pixels)';
COMMENT ON COLUMN nodes.position_y IS 'Vertical position of node in workflow editor (pixels)';

-- Note: Columns are nullable to handle existing nodes
-- Frontend will assign default positions for nodes without saved positions
